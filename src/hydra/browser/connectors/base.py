"""
Base Connector Interface — Interfaz común para todos los conectores.

Define el ciclo de vida estándar: connect → login → health_check → execute → close
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from hydra.browser.connectors.capabilities import (
    Capability,
    CapabilitySpec,
    ConnectorCapabilities,
    get_capabilities,
)

logger = logging.getLogger(__name__)


class ConnectorState(str, Enum):
    """Estados del ciclo de vida del conector."""
    UNINITIALIZED = "uninitialized"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    LOGGING_IN = "logging_in"
    AUTHENTICATED = "authenticated"
    READY = "ready"
    EXECUTING = "executing"
    ERROR = "error"
    CLOSING = "closing"
    CLOSED = "closed"


@dataclass
class HealthStatus:
    """Estado de salud del conector."""
    healthy: bool
    state: ConnectorState
    last_check: datetime = field(default_factory=datetime.utcnow)
    response_time_ms: float = 0.0
    last_error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"


@dataclass
class ExecutionResult:
    """Resultado de ejecución de una capacidad."""
    success: bool
    capability: Capability
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    artifacts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectorConfig:
    """Configuración base para conectores."""
    service_name: str
    credentials: Dict[str, Any] = field(default_factory=dict)
    browser_config: Dict[str, Any] = field(default_factory=dict)
    custom_config: Dict[str, Any] = field(default_factory=dict)
    capabilities_override: Optional[List[Capability]] = None


class BaseConnector(ABC):
    """
    Interfaz base para todos los conectores de HYDRA.

    Ciclo de vida obligatorio:
        1. connect()      → Establece conexión con BrowserManager
        2. login()        → Autenticación en el servicio
        3. health_check() → Verificación de disponibilidad
        4. execute()      → Ejecuta capacidades declaradas
        5. close()        → Limpieza y cierre

    Cada conector debe:
    - Declarar sus capacidades via `capabilities` property
    - Implementar todos los métodos abstractos
    - Manejar su propio estado interno
    - Ser thread-safe para uso concurrente
    """

    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.service_name = config.service_name
        self._state = ConnectorState.UNINITIALIZED
        self._browser_manager = None  # Inyectado por BrowserManager
        self._last_health_check: Optional[HealthStatus] = None
        self._execution_count = 0
        self._error_count = 0
        self._start_time = datetime.utcnow()
        self._last_activity = datetime.utcnow()

    @property
    @abstractmethod
    def capabilities(self) -> ConnectorCapabilities:
        """Declaración de capacidades que soporta este conector."""
        pass

    @property
    def state(self) -> ConnectorState:
        return self._state

    @property
    def is_ready(self) -> bool:
        return self._state == ConnectorState.READY

    @property
    def is_authenticated(self) -> bool:
        return self._state in (ConnectorState.AUTHENTICATED, ConnectorState.READY)

    # ===== Ciclo de Vida =====

    async def connect(self, browser_manager) -> bool:
        """
        Conecta el conector al BrowserManager.
        Inyecta la referencia al manager para operaciones de navegador.
        """
        self._set_state(ConnectorState.CONNECTING)
        try:
            self._browser_manager = browser_manager
            # Verificar que el perfil existe o crearlo
            await self._ensure_profile()
            self._set_state(ConnectorState.CONNECTED)
            logger.info(f"[{self.service_name}] Conectado a BrowserManager")
            return True
        except Exception as e:
            self._set_state(ConnectorState.ERROR)
            logger.error(f"[{self.service_name}] Error conectando: {e}")
            return False

    async def _ensure_profile(self) -> None:
        """Asegura que el perfil del navegador existe."""
        if self._browser_manager and self._browser_manager.session_manager:
            profile = self._browser_manager.session_manager.load_profile(self.service_name)
            logger.debug(f"[{self.service_name}] Perfil cargado: {profile.service_name}")

    @abstractmethod
    async def login(self, credentials: Optional[Dict[str, Any]] = None) -> bool:
        """
        Autenticación en el servicio externo.
        Debe manejar 2FA, OAuth, tokens, etc. según el servicio.
        """
        pass

    async def health_check(self) -> HealthStatus:
        """
        Verifica disponibilidad del servicio.
        Implementación por defecto: navega a URL base y verifica respuesta.
        """
        self._set_state(ConnectorState.CONNECTING)
        start = datetime.utcnow()
        
        try:
            healthy = await self._perform_health_check()
            response_time = (datetime.utcnow() - start).total_seconds() * 1000
            
            status = HealthStatus(
                healthy=healthy,
                state=self._state,
                response_time_ms=response_time,
                details={"service": self.service_name},
            )
            
            if healthy:
                self._set_state(ConnectorState.READY if self.is_authenticated else ConnectorState.CONNECTED)
            else:
                self._set_state(ConnectorState.ERROR)
            
            self._last_health_check = status
            return status
            
        except Exception as e:
            response_time = (datetime.utcnow() - start).total_seconds() * 1000
            status = HealthStatus(
                healthy=False,
                state=ConnectorState.ERROR,
                response_time_ms=response_time,
                last_error=str(e),
            )
            self._last_health_check = status
            self._set_state(ConnectorState.ERROR)
            return status

    @abstractmethod
    async def _perform_health_check(self) -> bool:
        """Implementación específica de health check."""
        pass

    async def execute(
        self,
        capability: Capability,
        params: Dict[str, Any],
    ) -> ExecutionResult:
        """
        Ejecuta una capacidad declarada.
        Valida que la capacidad esté soportada y delega a método específico.
        """
        if capability not in self.capabilities.supported:
            return ExecutionResult(
                success=False,
                capability=capability,
                error=f"Capacidad no soportada: {capability.value}",
            )

        self._set_state(ConnectorState.EXECUTING)
        self._execution_count += 1
        self._last_activity = datetime.utcnow()
        start = datetime.utcnow()

        try:
            # Dispatch a método específico
            method_name = f"_execute_{capability.value}"
            method = getattr(self, method_name, None)
            
            if method is None:
                # Fallback genérico via BrowserActions
                result = await self._execute_generic(capability, params)
            else:
                result = await method(params)

            duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
            
            exec_result = ExecutionResult(
                success=True,
                capability=capability,
                result=result,
                duration_ms=duration_ms,
            )
            
            self._set_state(ConnectorState.READY)
            return exec_result

        except Exception as e:
            self._error_count += 1
            duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
            logger.error(f"[{self.service_name}] Error ejecutando {capability.value}: {e}")
            
            self._set_state(ConnectorState.ERROR)
            return ExecutionResult(
                success=False,
                capability=capability,
                error=str(e),
                duration_ms=duration_ms,
            )

    async def _execute_generic(self, capability: Capability, params: Dict[str, Any]) -> Any:
        """Ejecución genérica via BrowserActions (fallback)."""
        if not self._browser_manager:
            raise RuntimeError("BrowserManager no disponible")
        
        async with self._browser_manager.session(self.service_name) as actions:
            # Mapear capacidades genéricas a acciones
            if capability == Capability.NAVIGATE:
                return await actions.goto(params["url"])
            elif capability == Capability.SCREENSHOT:
                return await actions.screenshot(
                    path=params.get("path"),
                    full_page=params.get("full_page", True),
                    selector=params.get("selector"),
                )
            elif capability == Capability.EXTRACT_TEXT:
                return await actions.get_text(params["selector"])
            elif capability == Capability.CLICK:
                return await actions.click(params["selector"])
            elif capability == Capability.FILL_FORM:
                return await actions.fill(params["selector"], params["value"])
            else:
                raise NotImplementedError(f"Capacidad genérica no implementada: {capability.value}")

    async def close(self) -> bool:
        """Cierra el conector y libera recursos."""
        self._set_state(ConnectorState.CLOSING)
        try:
            await self._cleanup()
            self._set_state(ConnectorState.CLOSED)
            logger.info(f"[{self.service_name}] Conector cerrado")
            return True
        except Exception as e:
            logger.error(f"[{self.service_name}] Error cerrando: {e}")
            self._set_state(ConnectorState.ERROR)
            return False

    async def _cleanup(self) -> None:
        """Limpieza específica del conector (override en subclases)."""
        pass

    # ===== Helpers =====

    def _set_state(self, state: ConnectorState) -> None:
        old_state = self._state
        self._state = state
        self._last_activity = datetime.utcnow()
        logger.debug(f"[{self.service_name}] Estado: {old_state.value} → {state.value}")

    def get_stats(self) -> Dict[str, Any]:
        """Estadísticas del conector."""
        return {
            "service_name": self.service_name,
            "state": self._state.value,
            "uptime_seconds": (datetime.utcnow() - self._start_time).total_seconds(),
            "execution_count": self._execution_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(self._execution_count, 1),
            "last_activity": self._last_activity.isoformat(),
            "last_health_check": self._last_health_check.__dict__ if self._last_health_check else None,
            "capabilities": [c.value for c in self.capabilities.supported],
        }

    def supports(self, capability: Capability) -> bool:
        return capability in self.capabilities.supported

    def get_capability_spec(self, capability: Capability) -> Optional[CapabilitySpec]:
        return self.capabilities.get_spec(capability)


# ===== Mixin para capacidades comunes =====

class AuthMixin:
    """Mixin para manejo de autenticación común."""
    
    async def login_with_credentials(self, credentials: Dict[str, Any]) -> bool:
        """Login genérico con credenciales email/password + opcional 2FA."""
        if not self._browser_manager:
            return False
        
        email = credentials.get("email")
        password = credentials.get("password")
        totp_secret = credentials.get("totp_secret")
        
        if not email or not password:
            return False
        
        async with self._browser_manager.session(self.service_name) as actions:
            await actions.goto(self._get_login_url())
            
            # Verificar si ya está logueado
            if await self._is_logged_in(actions):
                return True
            
            # Rellenar formulario
            await self._fill_login_form(actions, email, password)
            await actions.click(self._get_submit_selector())
            
            # 2FA si es necesario
            if totp_secret and await self._needs_2fa(actions):
                import pyotp
                code = pyotp.TOTP(totp_secret).now()
                await self._fill_2fa(actions, code)
                await actions.click(self._get_2fa_submit_selector())
            
            # Verificar login exitoso
            return await self._verify_login(actions)
    
    @abstractmethod
    def _get_login_url(self) -> str:
        pass
    
    @abstractmethod
    async def _is_logged_in(self, actions) -> bool:
        pass
    
    @abstractmethod
    async def _fill_login_form(self, actions, email: str, password: str) -> None:
        pass
    
    @abstractmethod
    def _get_submit_selector(self) -> str:
        pass
    
    @abstractmethod
    async def _needs_2fa(self, actions) -> bool:
        pass
    
    @abstractmethod
    async def _fill_2fa(self, actions, code: str) -> None:
        pass
    
    @abstractmethod
    def _get_2fa_submit_selector(self) -> str:
        pass
    
    @abstractmethod
    async def _verify_login(self, actions) -> bool:
        pass