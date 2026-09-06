"""
HYDRA Browser Manager — Único punto de entrada público para conectores.

Ningún conector accede directamente a:
- browser_pool
- session_manager
- page_objects
- actions
- vision
- recorder
- artifacts
- validation_engine

Toda interacción se realiza mediante BrowserManager.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from playwright.async_api import Page

from hydra.browser.core.browser_pool import BrowserPool, BrowserContextConfig
from hydra.browser.core.session_manager import SessionManager
from hydra.browser.core.actions import BrowserActions
from hydra.browser.artifacts import ArtifactStore, SessionArtifacts
from hydra.browser.vision import VisionAnalyzer, create_vision_analyzer
from hydra.browser.recorder import VideoRecorder, RecordingConfig
from hydra.browser.validation import ValidationEngine
from hydra.browser.connectors import (
    BaseConnector,
    ConnectorConfig,
    ConnectorRegistry,
    get_connector_registry,
    Capability,
    ConnectorCapabilities,
    HealthMonitor,
    get_health_monitor,
)
from hydra.browser.connectors.cluster import (
    ClusterMode,
    ClusterConfig,
    create_cluster_coordinator,
    IClusterCoordinator,
)

logger = logging.getLogger(__name__)


@dataclass
class BrowserManagerConfig:
    """Configuración del BrowserManager."""
    profiles_dir: Path
    artifacts_dir: Path
    recordings_dir: Optional[Path] = None
    vision_cache_dir: Optional[Path] = None
    
    # Browser Pool
    max_contexts: int = 10
    max_idle_minutes: int = 30
    health_check_minutes: int = 5
    default_viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    force_headless: bool = True
    
    # Recording
    record_video: bool = False
    video_keep_on_success: bool = False
    
    # Artifacts
    artifact_max_size_gb: float = 10.0
    
    # Vision
    vision_prefer_easyocr: bool = True
    
    # Validation
    validation_max_iterations: int = 5
    validation_timeout_ms: int = 60000
    
    # Cluster
    cluster_mode: ClusterMode = ClusterMode.LOCAL
    cluster_config: Optional[ClusterConfig] = None
    
    # Health Monitoring
    enable_health_monitor: bool = True
    health_check_interval_seconds: int = 30


class BrowserManager:
    """
    Gestor principal de automatización de navegador para HYDRA.
    
    ES EL ÚNICO PUNTO DE ENTRADA PÚBLICO para conectores externos.
    
    Responsabilidades:
    - Gestión de navegador (pool, contextos, pestañas)
    - Gestión de sesiones (perfiles cifrados por servicio)
    - Acciones de alto nivel (navegación, interacción, capturas)
    - Visión (OCR + DOM)
    - Grabación de video
    - Almacén de artefactos
    - Validación genérica (compile-fix cycle)
    - Registro y gestión de conectores
    - Monitoreo de salud
    - Coordinación de cluster (preparado para futuro)
    
    NO RESPONSABILIDADES:
    - Lógica específica de TradingView, Google, YouTube, etc.
    - Autenticación OAuth (usa src/hydra/google/)
    - Compilación Pine real (usa src/hydra/tradingview/)
    - Subida a YouTube (usa src/hydra/youtube/)
    - etc.
    """
    
    def __init__(self, config: BrowserManagerConfig):
        self.config = config
        self._pool: Optional[BrowserPool] = None
        self._session_manager: Optional[SessionManager] = None
        self._artifact_store: Optional[ArtifactStore] = None
        self._vision_analyzer: Optional[VisionAnalyzer] = None
        self._video_recorder: Optional[VideoRecorder] = None
        self._validation_engine: Optional[ValidationEngine] = None
        self._connector_registry: Optional[ConnectorRegistry] = None
        self._health_monitor: Optional[HealthMonitor] = None
        self._cluster_coordinator: Optional[IClusterCoordinator] = None
        self._started = False
        self._start_time = None
    
    # ===== Lifecycle =====
    
    async def start(self) -> None:
        """Inicializa todos los componentes core."""
        if self._started:
            logger.warning("BrowserManager ya iniciado")
            return
        
        logger.info("Iniciando BrowserManager...")
        
        # Browser Pool
        self._pool = BrowserPool(
            max_contexts=self.config.max_contexts,
            max_idle_time=asyncio.timedelta(minutes=self.config.max_idle_minutes),
            health_check_interval=asyncio.timedelta(minutes=self.config.health_check_minutes),
        )
        await self._pool.start()
        
        # Session Manager
        self._session_manager = SessionManager(self.config.profiles_dir)
        
        # Artifact Store
        self._artifact_store = ArtifactStore(
            self.config.artifacts_dir,
            max_size_gb=self.config.artifact_max_size_gb,
        )
        
        # Vision Analyzer
        self._vision_analyzer = await create_vision_analyzer(
            prefer_easyocr=self.config.vision_prefer_easyocr,
            cache_dir=self.config.vision_cache_dir,
        )
        
        # Video Recorder
        if self.config.record_video and self.config.recordings_dir:
            self._video_recorder = VideoRecorder(RecordingConfig(
                enabled=True,
                video_dir=self.config.recordings_dir,
                keep_on_success=self.config.video_keep_on_success,
            ))
        
        # Validation Engine
        self._validation_engine = ValidationEngine(
            browser_pool=self._pool,
            session_manager=self._session_manager,
            artifact_store=self._artifact_store,
            vision_analyzer=self._vision_analyzer,
            max_iterations=self.config.validation_max_iterations,
            compilation_timeout=self.config.validation_timeout_ms,
            default_module="generic",
        )
        
        # Connector Registry
        self._connector_registry = ConnectorRegistry()
        
        # Health Monitor
        if self.config.enable_health_monitor:
            self._health_monitor = HealthMonitor(
                registry=self._connector_registry,
                check_interval_seconds=self.config.health_check_interval_seconds,
            )
            await self._health_monitor.start()
        
        # Cluster Coordinator
        cluster_config = self.config.cluster_config or ClusterConfig(mode=self.config.cluster_mode)
        self._cluster_coordinator = create_cluster_coordinator(
            cluster_config.mode,
            self,
        )
        await self._cluster_coordinator.start()
        
        self._started = True
        self._start_time = asyncio.get_event_loop().time()
        logger.info("BrowserManager iniciado correctamente")
    
    async def stop(self) -> None:
        """Detiene todos los componentes y limpia recursos."""
        if not self._started:
            return
        
        logger.info("Deteniendo BrowserManager...")
        
        # Guardar todas las sesiones
        if self._session_manager:
            self._session_manager.save_all(force=True)
        
        # Cerrar conectores
        if self._connector_registry:
            await self._connector_registry.close_all()
        
        # Detener health monitor
        if self._health_monitor:
            await self._health_monitor.stop()
        
        # Detener cluster coordinator
        if self._cluster_coordinator:
            await self._cluster_coordinator.stop()
        
        # Detener browser pool
        if self._pool:
            await self._pool.stop()
        
        self._started = False
        logger.info("BrowserManager detenido")
    
    # ===== Connector Management (API Principal) =====
    
    def register_connector(
        self,
        name: str,
        connector_class: type,
        capabilities: ConnectorCapabilities,
        version: str = "1.0.0",
        description: str = "",
        dependencies: List[str] = None,
        config_schema: Dict[str, Any] = None,
        enabled: bool = True,
    ) -> None:
        """Registra un conector en el registry."""
        if not self._connector_registry:
            raise RuntimeError("BrowserManager no iniciado")
        self._connector_registry.register(
            name=name,
            connector_class=connector_class,
            capabilities=capabilities,
            version=version,
            description=description,
            dependencies=dependencies,
            enabled=enabled,
        )
    
    def get_connector(self, name: str) -> Optional[BaseConnector]:
        """Obtiene instancia de conector (la crea si no existe)."""
        if not self._connector_registry:
            raise RuntimeError("BrowserManager no iniciado")
        return self._connector_registry.get_instance(name)
    
    def get_or_create_connector(self, name: str, config: Optional[ConnectorConfig] = None) -> Optional[BaseConnector]:
        """Obtiene o crea instancia de conector."""
        if not self._connector_registry:
            raise RuntimeError("BrowserManager no iniciado")
        
        instance = self._connector_registry.get_instance(name)
        if instance:
            return instance
        
        if config is None:
            config = ConnectorConfig(service_name=name)
        
        return self._connector_registry.create_instance(name, config)
    
    async def initialize_connector(self, name: str, config: Optional[ConnectorConfig] = None) -> bool:
        """Inicializa y conecta un conector."""
        instance = self.get_or_create_connector(name, config)
        if not instance:
            return False
        return await instance.connect(self)
    
    async def shutdown_connector(self, name: str) -> bool:
        """Apaga un conector específico."""
        if not self._connector_registry:
            return False
        instance = self._connector_registry.get_instance(name)
        if instance:
            return await instance.close()
        return False
    
    # ===== Session Management (API Pública) =====
    
    @asynccontextmanager
    async def session(
        self,
        service_name: str,
        context_config: Optional[BrowserContextConfig] = None,
    ):
        """
        Context manager para sesión completa de un servicio.
        
        Uso:
            async with browser.session("tradingview") as actions:
                await actions.goto("https://tradingview.com/chart/")
                # ... conector usa actions directamente
        """
        if not self._started:
            raise RuntimeError("BrowserManager no iniciado. Llama a start() primero.")
        
        if context_config is None:
            context_config = BrowserContextConfig(profile_name=service_name)
        
        async with self._pool.acquire(context_config) as context:
            # Restaurar sesión si existe
            await self._session_manager.sync_to_browser(service_name, context)
            
            page = await self._pool.create_page(context)
            
            try:
                yield BrowserActions(
                    page=page,
                    browser_pool=self._pool,
                    session_manager=self._session_manager,
                    artifact_store=self._artifact_store,
                    vision_analyzer=self._vision_analyzer,
                    module_name=service_name,
                )
            finally:
                # Guardar sesión al salir
                await self._session_manager.sync_from_browser(service_name, context)
                self._session_manager.save_profile(service_name, force=True)
                await self._pool.close_page(context, page)
    
    @asynccontextmanager
    async def artifact_session(self, module: str, session_id: Optional[str] = None):
        """Context manager para sesión de artefactos."""
        if not self._artifact_store:
            raise RuntimeError("BrowserManager no iniciado")
        async with self._artifact_store.session(module, session_id) as session:
            yield session
    
    # ===== Capability Execution (API Unificada) =====
    
    async def execute_capability(
        self,
        connector_name: str,
        capability: Capability,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Ejecuta una capacidad en un conector.
        
        API unificada que todos los agentes/conectores usan.
        Maneja automáticamente: inicialización, ejecución, health check, métricas.
        
        Returns:
            Dict con: success, result, error, duration_ms, artifacts
        """
        if not self._started:
            raise RuntimeError("BrowserManager no iniciado")
        
        # Obtener o crear conector
        instance = self.get_or_create_connector(connector_name)
        if not instance:
            return {
                "success": False,
                "error": f"Conector no disponible: {connector_name}",
                "capability": capability.value,
            }
        
        # Conectar si necesario
        if not instance.is_ready:
            connected = await instance.connect(self)
            if not connected:
                return {
                    "success": False,
                    "error": f"No se pudo conectar conector: {connector_name}",
                    "capability": capability.value,
                }
        
        # Verificar capacidad soportada
        if not instance.supports(capability):
            return {
                "success": False,
                "error": f"Capacidad no soportada por {connector_name}: {capability.value}",
                "capability": capability.value,
            }
        
        # Ejecutar
        exec_result = await instance.execute(capability, params)
        
        # Registrar métricas en health monitor
        if self._health_monitor:
            self._health_monitor.record_execution(
                connector_name=connector_name,
                capability=capability.value,
                duration_ms=exec_result.duration_ms,
                success=exec_result.success,
            )
        
        return {
            "success": exec_result.success,
            "result": exec_result.result,
            "error": exec_result.error,
            "duration_ms": exec_result.duration_ms,
            "artifacts": exec_result.artifacts,
            "metadata": exec_result.metadata,
        }
    
    def list_capabilities(self, connector_name: str) -> List[Dict[str, Any]]:
        """Lista capacidades de un conector."""
        if not self._connector_registry:
            return []
        caps = self._connector_registry.get_capabilities(connector_name)
        if caps:
            return caps.list_all()
        return []
    
    def connector_supports(self, connector_name: str, capability: Capability) -> bool:
        """Verifica si un conector soporta una capacidad."""
        caps = self._connector_registry.get_capabilities(connector_name)
        return caps and caps.has(capability)
    
    # ===== Validation Engine (Acceso Controlado) =====
    
    def register_validation_module(self, name: str, module: Any) -> None:
        """Registra módulo para validación (ej. TradingView)."""
        if not self._validation_engine:
            raise RuntimeError("BrowserManager no iniciado")
        self._validation_engine.register_module(name, module)
    
    async def validate(
        self,
        script: str,
        script_name: str,
        module_name: str,
        context_config: Optional[BrowserContextConfig] = None,
    ):
        """Valida script usando módulo registrado."""
        if not self._validation_engine:
            raise RuntimeError("BrowserManager no iniciado")
        async with self._validation_engine.validate(script, script_name, module_name, context_config) as report:
            yield report
    
    # ===== Cluster Coordination (Preparado para Futuro) =====
    
    async def submit_task(self, task) -> str:
        """Envía tarea al cluster (local o distribuido)."""
        if not self._cluster_coordinator:
            raise RuntimeError("Cluster coordinator no disponible")
        return await self._cluster_coordinator.submit_task(task)
    
    async def get_task_result(self, task_id: str, timeout: float = 300):
        """Obtiene resultado de tarea del cluster."""
        if not self._cluster_coordinator:
            raise RuntimeError("Cluster coordinator no disponible")
        return await self._cluster_coordinator.get_task_result(task_id, timeout)
    
    async def get_cluster_status(self) -> Dict[str, Any]:
        """Estado del cluster."""
        if not self._cluster_coordinator:
            return {"mode": "none", "error": "Cluster coordinator no disponible"}
        return await self._cluster_coordinator.get_cluster_status()
    
    # ===== Health & Monitoring =====
    
    async def health_check_all(self) -> Dict[str, Any]:
        """Health check de todos los conectores."""
        if not self._connector_registry:
            return {}
        return await self._connector_registry.health_check_all()
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Salud global del sistema."""
        if not self._health_monitor:
            return {"error": "Health monitor no habilitado"}
        return self._health_monitor.get_system_health()
    
    def get_connector_stats(self, name: str) -> Optional[Dict[str, Any]]:
        """Estadísticas de un conector."""
        instance = self._connector_registry.get_instance(name) if self._connector_registry else None
        return instance.get_stats() if instance else None
    
    def get_all_connector_stats(self) -> Dict[str, Dict[str, Any]]:
        """Estadísticas de todos los conectores."""
        if not self._connector_registry:
            return {}
        return {
            name: instance.get_stats()
            for name, instance in self._connector_registry.get_all_instances().items()
        }
    
    def get_prometheus_metrics(self) -> str:
        """Métricas en formato Prometheus."""
        if not self._health_monitor:
            return "# Health monitor no habilitado"
        return self._health_monitor.get_prometheus_metrics()
    
    # ===== Browser Actions Directas (para casos genéricos) =====
    
    @asynccontextmanager
    async def generic_session(
        self,
        base_url: str = "",
        context_config: Optional[BrowserContextConfig] = None,
    ):
        """Sesión genérica para cualquier web sin conector específico."""
        if context_config is None:
            context_config = BrowserContextConfig(profile_name="generic")
        
        async with self._pool.acquire(context_config) as context:
            page = await self._pool.create_page(context)
            try:
                yield BrowserActions(
                    page=page,
                    browser_pool=self._pool,
                    session_manager=self._session_manager,
                    artifact_store=self._artifact_store,
                    vision_analyzer=self._vision_analyzer,
                    module_name="generic",
                )
            finally:
                await self._pool.close_page(context, page)
    
    # ===== Properties (Read-only para conectores) =====
    
    @property
    def is_started(self) -> bool:
        return self._started
    
    @property
    def uptime_seconds(self) -> float:
        if not self._start_time:
            return 0.0
        return asyncio.get_event_loop().time() - self._start_time
    
    @property
    def pool_stats(self) -> Dict[str, Any]:
        return self._pool.get_stats() if self._pool else {}
    
    @property
    def artifact_stats(self) -> Dict[str, Any]:
        return self._artifact_store.get_stats() if self._artifact_store else {}
    
    @property
    def session_profiles(self) -> List[str]:
        return self._session_manager.list_profiles() if self._session_manager else []
    
    @property
    def registered_connectors(self) -> List[Dict[str, Any]]:
        if not self._connector_registry:
            return []
        return self._connector_registry.list_all()
    
    # ===== Cleanup =====
    
    async def cleanup(
        self,
        max_age_days: int = 30,
        max_artifacts_gb: float = 10,
        max_recordings_gb: float = 5,
    ) -> Dict[str, int]:
        """Limpieza de recursos antiguos."""
        results = {"artifacts_removed": 0, "recordings_removed": 0}
        
        if self._video_recorder:
            results["recordings_removed"] = self._video_recorder.cleanup_old(
                max_age_days=max_age_days,
                max_total_gb=max_recordings_gb,
            )
        
        return results


# ===== Factory =====

def create_browser_manager(
    profiles_dir: Union[str, Path],
    artifacts_dir: Union[str, Path],
    recordings_dir: Optional[Union[str, Path]] = None,
    vision_cache_dir: Optional[Union[str, Path]] = None,
    **kwargs,
) -> BrowserManager:
    """Factory para crear BrowserManager con configuración por defecto."""
    config = BrowserManagerConfig(
        profiles_dir=Path(profiles_dir),
        artifacts_dir=Path(artifacts_dir),
        recordings_dir=Path(recordings_dir) if recordings_dir else None,
        vision_cache_dir=Path(vision_cache_dir) if vision_cache_dir else None,
        **kwargs,
    )
    return BrowserManager(config)


# ===== Export público =====

__all__ = [
    "BrowserManager",
    "BrowserManagerConfig",
    "create_browser_manager",
]