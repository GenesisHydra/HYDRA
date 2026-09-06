"""
HYDRA Browser Connectors — Paquete de conectores.

Proporciona la infraestructura para conectores de servicios externos:
- BaseConnector: Interfaz base con ciclo de vida estándar
- Capabilities: Sistema de capacidades declarativas
- Registry: Registro automático de conectores
- Health: Monitoreo de salud unificado
- Cluster: Interfaces preparadas para cluster distribuido
"""

from hydra.browser.connectors.base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorState,
    HealthStatus,
    ExecutionResult,
    AuthMixin,
)

from hydra.browser.connectors.capabilities import (
    Capability,
    CapabilitySpec,
    ConnectorCapabilities,
    get_capabilities,
    DEFAULT_CONNECTOR_CAPABILITIES,
)

from hydra.browser.connectors.registry import (
    ConnectorRegistry,
    ConnectorRegistration,
    get_connector_registry,
    register_connector,
    get_connector,
    connector,
)

from hydra.browser.connectors.health import (
    HealthMonitor,
    Alert,
    AlertLevel,
    ConnectorMetrics,
    SystemHealth,
    get_health_monitor,
    log_alert_handler,
    slack_alert_handler,
)

from hydra.browser.connectors.cluster import (
    NodeRole,
    NodeStatus,
    NodeInfo,
    TaskRequest,
    TaskResult,
    IClusterCoordinator,
    IClusterWorker,
    ITaskQueue,
    LocalClusterCoordinator,
    ClusterMode,
    ClusterConfig,
    create_cluster_coordinator,
    create_cluster_worker,
)

__all__ = [
    # Base
    "BaseConnector",
    "ConnectorConfig",
    "ConnectorState",
    "HealthStatus",
    "ExecutionResult",
    "AuthMixin",
    # Capabilities
    "Capability",
    "CapabilitySpec",
    "ConnectorCapabilities",
    "get_capabilities",
    "DEFAULT_CONNECTOR_CAPABILITIES",
    # Registry
    "ConnectorRegistry",
    "ConnectorRegistration",
    "get_connector_registry",
    "register_connector",
    "get_connector",
    "connector",
    # Health
    "HealthMonitor",
    "Alert",
    "AlertLevel",
    "ConnectorMetrics",
    "SystemHealth",
    "get_health_monitor",
    "log_alert_handler",
    "slack_alert_handler",
    # Cluster
    "NodeRole",
    "NodeStatus",
    "NodeInfo",
    "TaskRequest",
    "TaskResult",
    "IClusterCoordinator",
    "IClusterWorker",
    "ITaskQueue",
    "LocalClusterCoordinator",
    "ClusterMode",
    "ClusterConfig",
    "create_cluster_coordinator",
    "create_cluster_worker",
]