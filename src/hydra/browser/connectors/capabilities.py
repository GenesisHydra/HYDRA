"""
Connector Capabilities — Sistema de capacidades declarativas para conectores.

Cada conector declara qué operaciones soporta. BrowserManager consulta
estas capacidades sin conocer la implementación.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class Capability(str, Enum):
    """Capacidades estándar disponibles."""
    # Autenticación
    LOGIN = "login"
    LOGOUT = "logout"
    HEALTH_CHECK = "health_check"
    
    # Navegación genérica
    NAVIGATE = "navigate"
    SCREENSHOT = "screenshot"
    EXTRACT_TEXT = "extract_text"
    EXTRACT_TABLE = "extract_table"
    UPLOAD_FILE = "upload_file"
    DOWNLOAD_FILE = "download_file"
    FILL_FORM = "fill_form"
    CLICK = "click"
    WAIT_FOR = "wait_for"
    
    # TradingView específicas
    COMPILE_PINE = "compile_pine"
    CHART_NAVIGATION = "chart_navigation"
    PINE_EDITOR = "pine_editor"
    
    # YouTube específicas
    UPLOAD_VIDEO = "upload_video"
    MANAGE_THUMBNAILS = "manage_thumbnails"
    MANAGE_PLAYLISTS = "manage_playlists"
    ANALYTICS = "analytics"
    
    # LinkedIn específicas
    PUBLISH_POST = "publish_post"
    UPLOAD_IMAGE = "upload_image"
    SEND_MESSAGE = "send_message"
    NETWORKING = "networking"
    
    # GitHub específicas
    CREATE_ISSUE = "create_issue"
    CREATE_PR = "create_pr"
    MANAGE_ACTIONS = "manage_actions"
    REPO_OPS = "repo_ops"
    
    # X/Twitter específicas
    POST_TWEET = "post_tweet"
    SEND_DM = "send_dm"
    SCHEDULE = "schedule"
    
    # Google específicas
    GMAIL_READ = "gmail_read"
    GMAIL_SEND = "gmail_send"
    DRIVE_UPLOAD = "drive_upload"
    CALENDAR_MANAGE = "calendar_manage"
    SHEETS_ACCESS = "sheets_access"
    
    # FundedNext / GoMining
    DASHBOARD = "dashboard"
    TRADING_OPS = "trading_ops"
    MINING_OPS = "mining_ops"
    
    # Genérico
    EXECUTE_CUSTOM = "execute_custom"
    BROWSER_ACTIONS = "browser_actions"


@dataclass
class CapabilitySpec:
    """Especificación detallada de una capacidad."""
    name: Capability
    description: str
    required_params: List[str] = field(default_factory=list)
    optional_params: List[str] = field(default_factory=list)
    returns: str = "Any"
    async_op: bool = True
    rate_limit: Optional[Dict[str, int]] = None  # {"requests": 10, "window_seconds": 60}
    requires_auth: bool = True


# Registro de capacidades conocidas (extensible)
CAPABILITY_REGISTRY: Dict[Capability, CapabilitySpec] = {
    Capability.LOGIN: CapabilitySpec(
        name=Capability.LOGIN,
        description="Autenticación en el servicio",
        required_params=["credentials"],
        optional_params=["totp", "remember_me"],
        returns="bool",
        async_op=True,
    ),
    Capability.LOGOUT: CapabilitySpec(
        name=Capability.LOGOUT,
        description="Cerrar sesión",
        required_params=[],
        returns="bool",
    ),
    Capability.HEALTH_CHECK: CapabilitySpec(
        name=Capability.HEALTH_CHECK,
        description="Verificar disponibilidad del servicio",
        required_params=[],
        returns="HealthStatus",
        requires_auth=False,
    ),
    Capability.COMPILE_PINE: CapabilitySpec(
        name=Capability.COMPILE_PINE,
        description="Compilar script Pine en TradingView",
        required_params=["script", "script_name"],
        optional_params=["symbol", "timeout"],
        returns="CompilationResult",
        rate_limit={"requests": 5, "window_seconds": 60},
    ),
    Capability.UPLOAD_VIDEO: CapabilitySpec(
        name=Capability.UPLOAD_VIDEO,
        description="Subir video a YouTube",
        required_params=["video_path", "title", "description"],
        optional_params=["tags", "privacy", "thumbnail"],
        returns="VideoMetadata",
        rate_limit={"requests": 2, "window_seconds": 3600},
    ),
    Capability.PUBLISH_POST: CapabilitySpec(
        name=Capability.PUBLISH_POST,
        description="Publicar post en LinkedIn/X",
        required_params=["content"],
        optional_params=["media", "visibility"],
        returns="PostResult",
        rate_limit={"requests": 10, "window_seconds": 3600},
    ),
    Capability.CREATE_ISSUE: CapabilitySpec(
        name=Capability.CREATE_ISSUE,
        description="Crear issue en GitHub",
        required_params=["repo", "title", "body"],
        optional_params=["labels", "assignees", "milestone"],
        returns="Issue",
    ),
    Capability.NAVIGATE: CapabilitySpec(
        name=Capability.NAVIGATE,
        description="Navegación genérica a URL",
        required_params=["url"],
        optional_params=["wait_until", "timeout"],
        returns="NavigationResult",
        requires_auth=False,
    ),
    Capability.SCREENSHOT: CapabilitySpec(
        name=Capability.SCREENSHOT,
        description="Captura de pantalla",
        required_params=[],
        optional_params=["full_page", "selector", "path"],
        returns="ScreenshotResult",
        requires_auth=False,
    ),
    Capability.EXTRACT_TEXT: CapabilitySpec(
        name=Capability.EXTRACT_TEXT,
        description="Extraer texto de página",
        required_params=["selector"],
        optional_params=[],
        returns="str",
        requires_auth=False,
    ),
    Capability.BROWSER_ACTIONS: CapabilitySpec(
        name=Capability.BROWSER_ACTIONS,
        description="Acceso directo a BrowserActions (fallback genérico)",
        required_params=[],
        optional_params=[],
        returns="BrowserActions",
        requires_auth=False,
    ),
}


@dataclass
class ConnectorCapabilities:
    """Declaración de capacidades de un conector."""
    connector_name: str
    supported: Set[Capability] = field(default_factory=set)
    custom: Dict[str, CapabilitySpec] = field(default_factory=dict)
    
    def has(self, capability: Capability) -> bool:
        return capability in self.supported
    
    def add(self, capability: Capability, spec: Optional[CapabilitySpec] = None) -> None:
        self.supported.add(capability)
        if spec:
            self.custom[capability.value] = spec
    
    def get_spec(self, capability: Capability) -> Optional[CapabilitySpec]:
        if capability.value in self.custom:
            return self.custom[capability.value]
        return CAPABILITY_REGISTRY.get(capability)
    
    def list_all(self) -> List[Dict[str, Any]]:
        """Lista todas las capacidades con sus specs."""
        result = []
        for cap in self.supported:
            spec = self.get_spec(cap)
            if spec:
                result.append({
                    "name": cap.value,
                    "description": spec.description,
                    "required_params": spec.required_params,
                    "optional_params": spec.optional_params,
                    "returns": spec.returns,
                    "async": spec.async_op,
                    "rate_limit": spec.rate_limit,
                    "requires_auth": spec.requires_auth,
                })
        return result


# Capacidades predefinidas por conector conocido
DEFAULT_CONNECTOR_CAPABILITIES = {
    "tradingview": ConnectorCapabilities(
        connector_name="tradingview",
        supported={
            Capability.LOGIN,
            Capability.LOGOUT,
            Capability.HEALTH_CHECK,
            Capability.COMPILE_PINE,
            Capability.CHART_NAVIGATION,
            Capability.PINE_EDITOR,
            Capability.SCREENSHOT,
            Capability.EXTRACT_TEXT,
            Capability.BROWSER_ACTIONS,
        },
    ),
    "youtube": ConnectorCapabilities(
        connector_name="youtube",
        supported={
            Capability.LOGIN,
            Capability.LOGOUT,
            Capability.HEALTH_CHECK,
            Capability.UPLOAD_VIDEO,
            Capability.MANAGE_THUMBNAILS,
            Capability.MANAGE_PLAYLISTS,
            Capability.ANALYTICS,
            Capability.SCREENSHOT,
            Capability.BROWSER_ACTIONS,
        },
    ),
    "linkedin": ConnectorCapabilities(
        connector_name="linkedin",
        supported={
            Capability.LOGIN,
            Capability.LOGOUT,
            Capability.HEALTH_CHECK,
            Capability.PUBLISH_POST,
            Capability.UPLOAD_IMAGE,
            Capability.SEND_MESSAGE,
            Capability.NETWORKING,
            Capability.SCREENSHOT,
            Capability.BROWSER_ACTIONS,
        },
    ),
    "github": ConnectorCapabilities(
        connector_name="github",
        supported={
            Capability.LOGIN,
            Capability.LOGOUT,
            Capability.HEALTH_CHECK,
            Capability.CREATE_ISSUE,
            Capability.CREATE_PR,
            Capability.MANAGE_ACTIONS,
            Capability.REPO_OPS,
            Capability.SCREENSHOT,
            Capability.BROWSER_ACTIONS,
        },
    ),
    "x": ConnectorCapabilities(
        connector_name="x",
        supported={
            Capability.LOGIN,
            Capability.LOGOUT,
            Capability.HEALTH_CHECK,
            Capability.POST_TWEET,
            Capability.SEND_DM,
            Capability.SCHEDULE,
            Capability.SCREENSHOT,
            Capability.BROWSER_ACTIONS,
        },
    ),
    "google": ConnectorCapabilities(
        connector_name="google",
        supported={
            Capability.LOGIN,
            Capability.LOGOUT,
            Capability.HEALTH_CHECK,
            Capability.GMAIL_READ,
            Capability.GMAIL_SEND,
            Capability.DRIVE_UPLOAD,
            Capability.CALENDAR_MANAGE,
            Capability.SHEETS_ACCESS,
            Capability.BROWSER_ACTIONS,
        },
    ),
    "fundednext": ConnectorCapabilities(
        connector_name="fundednext",
        supported={
            Capability.LOGIN,
            Capability.LOGOUT,
            Capability.HEALTH_CHECK,
            Capability.DASHBOARD,
            Capability.TRADING_OPS,
            Capability.SCREENSHOT,
            Capability.BROWSER_ACTIONS,
        },
    ),
    "gomining": ConnectorCapabilities(
        connector_name="gomining",
        supported={
            Capability.LOGIN,
            Capability.LOGOUT,
            Capability.HEALTH_CHECK,
            Capability.DASHBOARD,
            Capability.MINING_OPS,
            Capability.SCREENSHOT,
            Capability.BROWSER_ACTIONS,
        },
    ),
    "generic": ConnectorCapabilities(
        connector_name="generic",
        supported={
            Capability.NAVIGATE,
            Capability.SCREENSHOT,
            Capability.EXTRACT_TEXT,
            Capability.EXTRACT_TABLE,
            Capability.UPLOAD_FILE,
            Capability.DOWNLOAD_FILE,
            Capability.FILL_FORM,
            Capability.CLICK,
            Capability.WAIT_FOR,
            Capability.BROWSER_ACTIONS,
        },
    ),
}


def get_capabilities(connector_name: str) -> ConnectorCapabilities:
    """Obtiene capacidades predefinidas para un conector."""
    return DEFAULT_CONNECTOR_CAPABILITIES.get(
        connector_name,
        ConnectorCapabilities(connector_name=connector_name),
    )