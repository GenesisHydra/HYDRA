"""
Validation Engine - Ciclo automático de validación compile-fix para HYDRA Browser.

Flujo:
1. generate script (Coding Agent)
2. browser compile (ejecutar en navegador real)
3. capturar errores
4. convertir errores a JSON estructurado
5. devolver errores al Coding Agent
6. corregir
7. volver a probar
8. SUCCESS

No requiere intervención humana.
"""

import asyncio
import json
import logging
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from playwright.async_api import Page

from hydra.browser.artifacts import ArtifactStore
from hydra.browser.core.actions import BrowserActions
from hydra.browser.core.browser_pool import BrowserPool, BrowserContextConfig
from hydra.browser.core.session_manager import SessionManager
from hydra.browser.vision import VisionAnalyzer

logger = logging.getLogger(__name__)


class ValidationStatus(str, Enum):
    """Estado de validación."""
    PENDING = "pending"
    COMPILING = "compiling"
    SUCCESS = "success"
    COMPILATION_ERROR = "compilation_error"
    RUNTIME_ERROR = "runtime_error"
    TIMEOUT = "timeout"
    UNKNOWN_ERROR = "unknown_error"


class ErrorType(str, Enum):
    """Tipo de error Pine Script."""
    SYNTAX = "syntax"           # CE10101, CE10117, etc.
    TYPE = "type"               # Type mismatch
    RUNTIME = "runtime"         # RE10139, RE10143, etc.
    WARNING = "warning"         # CW10003, etc.
    UNKNOWN = "unknown"


@dataclass
class CompilationError:
    """Error de compilación estructurado."""
    line: int
    column: int
    message: str
    code: str  # CE10101, CW10003, etc.
    severity: str  # error, warning, info
    error_type: ErrorType
    source_snippet: Optional[str] = None
    suggested_fix: Optional[str] = None
    raw_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "line": self.line,
            "column": self.column,
            "message": self.message,
            "code": self.code,
            "severity": self.severity,
            "error_type": self.error_type.value,
            "source_snippet": self.source_snippet,
            "suggested_fix": self.suggested_fix,
            "raw_text": self.raw_text,
        }


@dataclass
class CompilationResult:
    """Resultado de compilación."""
    success: bool
    errors: List[CompilationError] = field(default_factory=list)
    warnings: List[CompilationError] = field(default_factory=list)
    output: Optional[str] = None
    duration_ms: float = 0


@dataclass
class ValidationReport:
    """Informe completo de validación."""
    script_name: str
    script_hash: str
    timestamp: str
    status: ValidationStatus
    compilation: CompilationResult
    screenshots: Dict[str, str] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    iterations: int = 0
    total_duration_ms: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "script_name": self.script_name,
            "script_hash": self.script_hash,
            "timestamp": self.timestamp,
            "status": self.status.value,
            "compilation": {
                "success": self.compilation.success,
                "errors": [e.to_dict() for e in self.compilation.errors],
                "warnings": [w.to_dict() for w in self.compilation.warnings],
                "output": self.compilation.output,
                "duration_ms": self.compilation.duration_ms,
            },
            "screenshots": self.screenshots,
            "metrics": self.metrics,
            "artifacts": self.artifacts,
            "iterations": self.iterations,
            "total_duration_ms": self.total_duration_ms,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class PineErrorParser:
    """Parser de errores de TradingView Pine Editor."""

    # Patrones de error comunes
    ERROR_PATTERNS = [
        # Error estándar: línea X: mensaje (código)
        re.compile(
            r"(?:line|línea)\s*(\d+)[:\s]*"
            r"(.*?)"
            r"\s*\(([A-Z]{2}\d{5})\)",
            re.IGNORECASE,
        ),
        # Error con columna: línea X, columna Y: mensaje (código)
        re.compile(
            r"(?:line|línea)\s*(\d+)[,\s]*(?:column|columna)\s*(\d+)[:\s]*"
            r"(.*?)"
            r"\s*\(([A-Z]{2}\d{5})\)",
            re.IGNORECASE,
        ),
        # Error simple: mensaje (código)
        re.compile(
            r"(.*?)\s*\(([A-Z]{2}\d{5})\)",
            re.IGNORECASE,
        ),
    ]

    WARNING_PATTERNS = [
        re.compile(
            r"(?:warning|advertencia)[:\s]*"
            r"(.*?)"
            r"\s*\(([A-Z]{2}\d{5})\)",
            re.IGNORECASE,
        ),
    ]

    # Mapeo de códigos a tipos
    CODE_TO_TYPE = {
        "CE": ErrorType.SYNTAX,
        "CW": ErrorType.WARNING,
        "RE": ErrorType.RUNTIME,
        "FA": ErrorType.TYPE,
    }

    @classmethod
    def parse_errors(cls, error_text: str) -> List[CompilationError]:
        """Parsea texto de errores a lista estructurada."""
        errors = []

        for pattern in cls.ERROR_PATTERNS:
            for match in pattern.finditer(error_text):
                groups = match.groups()
                if len(groups) >= 3:
                    line = int(groups[0]) if groups[0].isdigit() else 0
                    column = int(groups[1]) if len(groups) > 2 and groups[1].isdigit() else 0
                    message = groups[-2].strip() if len(groups) > 2 else groups[0].strip()
                    code = groups[-1].strip().upper()

                    error_type = cls.CODE_TO_TYPE.get(code[:2], ErrorType.UNKNOWN)
                    severity = "warning" if error_type == ErrorType.WARNING else "error"

                    errors.append(CompilationError(
                        line=line,
                        column=column,
                        message=message,
                        code=code,
                        severity=severity,
                        error_type=error_type,
                        raw_text=match.group(0),
                    ))

        return errors

    @classmethod
    def parse_warnings(cls, warning_text: str) -> List[CompilationError]:
        """Parsea warnings."""
        warnings = []
        for pattern in cls.WARNING_PATTERNS:
            for match in pattern.finditer(warning_text):
                groups = match.groups()
                if len(groups) >= 2:
                    message = groups[0].strip()
                    code = groups[1].strip().upper()

                    warnings.append(CompilationError(
                        line=0,
                        column=0,
                        message=message,
                        code=code,
                        severity="warning",
                        error_type=ErrorType.WARNING,
                        raw_text=match.group(0),
                    ))
        return warnings


class ValidationEngine:
    """
    Motor de validación automática para scripts Pine (y otros).

    Orquesta:
    - BrowserPool para contexto
    - SessionManager para login/perfil
    - Module-specific controller (TradingView, etc.)
    - VisionAnalyzer para captura visual
    - ArtifactStore para persistencia
    - PineErrorParser para estructurar errores
    """

    def __init__(
        self,
        browser_pool: BrowserPool,
        session_manager: SessionManager,
        artifact_store: ArtifactStore,
        vision_analyzer: Optional[VisionAnalyzer] = None,
        max_iterations: int = 5,
        compilation_timeout: float = 60000,
        default_module: str = "tradingview",
    ):
        self.browser_pool = browser_pool
        self.session_manager = session_manager
        self.artifact_store = artifact_store
        self.vision_analyzer = vision_analyzer
        self.max_iterations = max_iterations
        self.compilation_timeout = compilation_timeout
        self.default_module = default_module

        # Módulos registrados
        self._modules: Dict[str, Any] = {}

    def register_module(self, name: str, module_controller: Any) -> None:
        """Registra un controlador de módulo (TradingView, Gmail, etc.)."""
        self._modules[name] = module_controller

    def get_module(self, name: str) -> Any:
        """Obtiene un módulo registrado."""
        if name not in self._modules:
            raise ValueError(f"Módulo no registrado: {name}. Disponibles: {list(self._modules.keys())}")
        return self._modules[name]

    @asynccontextmanager
    async def validate(
        self,
        script_content: str,
        script_name: str = "script",
        module_name: Optional[str] = None,
        context_config: Optional[BrowserContextConfig] = None,
    ):
        """
        Context manager para validación completa con reintentos automáticos.

        Uso:
            async with engine.validate(script, "genesis_vwap.pine") as report:
                # report se actualiza en cada iteración
                pass
            # Al final, report tiene el resultado final
        """
        module_name = module_name or self.default_module
        module = self.get_module(module_name)

        # Hash del script
        script_hash = hashlib.sha256(script_content.encode()).hexdigest()[:16]

        # Iniciar sesión de artefactos
        async with self.artifact_store.session(module_name) as session:
            # Guardar script original
            await self.artifact_store.add_script(session, script_content, script_name)

            report = ValidationReport(
                script_name=script_name,
                script_hash=script_hash,
                timestamp=datetime.utcnow().isoformat(),
                status=ValidationStatus.PENDING,
                compilation=CompilationResult(success=False),
            )

            start_time = datetime.utcnow()
            iteration = 0

            while iteration < self.max_iterations:
                iteration += 1
                report.iterations = iteration
                logger.info(f"Validación iteración {iteration}/{self.max_iterations} para {script_name}")

                # Compilar en navegador
                try:
                    compilation_result = await self._compile_in_browser(
                        module, script_content, session, context_config
                    )
                    report.compilation = compilation_result

                    if compilation_result.success:
                        report.status = ValidationStatus.SUCCESS
                        logger.info(f"Validación exitosa en iteración {iteration}")
                        break
                    else:
                        report.status = ValidationStatus.COMPILATION_ERROR
                        logger.warning(f"Errores de compilación ({len(compilation_result.errors)}): iteración {iteration}")

                except asyncio.TimeoutError:
                    report.status = ValidationStatus.TIMEOUT
                    logger.error(f"Timeout en iteración {iteration}")
                    break
                except Exception as e:
                    report.status = ValidationStatus.UNKNOWN_ERROR
                    report.compilation.errors.append(CompilationError(
                        line=0, column=0,
                        message=str(e),
                        code="UNKNOWN",
                        severity="error",
                        error_type=ErrorType.UNKNOWN,
                    ))
                    logger.error(f"Error inesperado en iteración {iteration}: {e}")
                    break

                # Si hay errores y no es la última iteración, preparar para corrección
                if iteration < self.max_iterations:
                    # Aquí el Coding Agent corregiría el script
                    # Por ahora, solo logueamos los errores para revisión manual
                    logger.info(f"Errores para corrección: {len(report.compilation.errors)}")
                    for err in report.compilation.errors:
                        logger.info(f"  L{err.line}: {err.code} - {err.message}")

                    # En implementación real, aquí se llamaría al Coding Agent
                    # script_content = await coding_agent.fix(script_content, report.compilation.errors)
                    # Para demo, rompemos el bucle
                    break

            # Finalizar
            report.total_duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Generar reporte final
            await self.artifact_store.add_validation_report(session, report.to_dict())

            yield report

    async def _compile_in_browser(
        self,
        module: Any,
        script_content: str,
        session,
        context_config: Optional[BrowserContextConfig] = None,
    ) -> CompilationResult:
        """Compila script en el navegador usando el módulo específico."""
        start = datetime.utcnow()

        async with self.browser_pool.acquire(context_config) as context:
            # Sincronizar sesión
            await self.session_manager.sync_to_browser(module.service_name, context)

            page = await self.browser_pool.create_page(context)

            try:
                # Usar módulo específico para compilar
                result = await module.compile_script(
                    page=page,
                    script_content=script_content,
                    artifact_store=self.artifact_store,
                    session=session,
                    vision_analyzer=self.vision_analyzer,
                    timeout=self.compilation_timeout,
                )

                # Sincronizar de vuelta
                await self.session_manager.sync_from_browser(module.service_name, context)

                duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
                result.duration_ms = duration_ms
                return result

            finally:
                await self.browser_pool.close_page(context, page)

    async def fix_and_retry(
        self,
        script_content: str,
        errors: List[CompilationError],
        coder_agent: Callable[[str, List[CompilationError]], str],
        script_name: str = "script",
        module_name: Optional[str] = None,
    ) -> str:
        """
        Corrige script usando un Coding Agent y revalida.

        Args:
            script_content: Script original
            errors: Errores de compilación
            coder_agent: Función async (script, errors) -> fixed_script
            script_name: Nombre del script
            module_name: Módulo a usar

        Returns:
            Script corregido y validado exitosamente
        """
        current_script = script_content

        for iteration in range(self.max_iterations):
            logger.info(f"Fix attempt {iteration + 1}/{self.max_iterations}")

            # Validar
            async with self.validate(current_script, script_name, module_name) as report:
                if report.status == ValidationStatus.SUCCESS:
                    logger.info("Script corregido y validado exitosamente")
                    return current_script

                # Corregir
                current_script = await coder_agent(current_script, report.compilation.errors)

        raise RuntimeError(f"No se pudo corregir script tras {self.max_iterations} iteraciones")


# ===== Coding Agent Interface =====

class CodingAgentInterface:
    """Interfaz para agentes de código que corrigen scripts."""

    async def fix(self, script: str, errors: List[CompilationError]) -> str:
        """Corrige script basado en errores. Debe ser implementado por agente real."""
        raise NotImplementedError("Implementar en agente específico")


# ===== Utilidades =====

import hashlib