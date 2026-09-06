"""
HYDRA Browser - Infraestructura de automatización web unificada.

Un servicio de infraestructura común para todos los agentes de HYDRA que necesitan
interactuar con aplicaciones web: TradingView, Gmail, YouTube, LinkedIn, X, GitHub, etc.

IMPORTANTE: HYDRA Browser NO contiene integraciones con servicios externos.
Todos los conectores viven en paquetes separados:
    src/hydra/tradingview/
    src/hydra/google/
    src/hydra/youtube/
    src/hydra/linkedin/
    src/hydra/x/
    src/hydra/github/
    src/hydra/fundednext/
    src/hydra/gomining/
    ...

Arquitectura:
    HYDRA Browser (Infraestructura)
        ├── Browser Pool (contextos Chromium persistentes)
        ├── Session Manager (perfiles cifrados por servicio)
        ├── Page Objects (patrón Page Object Model)
        ├── Vision (OCR + análisis visual)
        ├── Recorder (grabación de video opcional)
        ├── Artifact Store (persistencia de evidencias)
        ├── Validation Engine (ciclo compile-fix genérico)
        └── MCP Interface (acceso exclusivo para agentes)

Módulos internos (solo fallback genérico):
    └── Generic (fallback universal para cualquier web)

Conectores externos (paquetes independientes):
    ├── TradingView → src/hydra/tradingview/
    ├── Google → src/hydra/google/
    ├── YouTube → src/hydra/youtube/
    ├── LinkedIn → src/hydra/linkedin/
    ├── X → src/hydra/x/
    ├── GitHub → src/hydra/github/
    ├── FundedNext → src/hydra/fundednext/
    ├── GoMining → src/hydra/gomining/
    └── ...
"""

from hydra.browser.core.browser_pool import BrowserPool, BrowserContextConfig
from hydra.browser.core.session_manager import SessionManager, EncryptedProfile
from hydra.browser.core.page_objects import BasePageObject, Selector, WaitConfig
from hydra.browser.core.actions import BrowserActions, ActionResult
from hydra.browser.mcp.interface import HydraBrowserMCP, MCPRequest, MCPResponse
from hydra.browser.validation.engine import ValidationEngine, CompilationError, CompilationResult, ValidationStatus
from hydra.browser.artifacts.store import ArtifactStore, Artifact, SessionArtifacts
from hydra.browser.vision import VisionAnalyzer, OCRBackend, TesseractOCR, EasyOCRBackend, create_vision_analyzer
from hydra.browser.recorder import VideoRecorder, RecordingConfig, RecordingMetadata
from hydra.browser.manager import BrowserManager, BrowserManagerConfig, create_browser_manager

__version__ = "1.0.0"

__all__ = [
    # Core
    "BrowserPool",
    "BrowserContextConfig",
    "SessionManager",
    "EncryptedProfile",
    "BasePageObject",
    "Selector",
    "WaitConfig",
    "BrowserActions",
    "ActionResult",
    # MCP
    "HydraBrowserMCP",
    "MCPRequest",
    "MCPResponse",
    # Validation
    "ValidationEngine",
    "CompilationError",
    "CompilationResult",
    "ValidationStatus",
    # Artifacts
    "ArtifactStore",
    "Artifact",
    "SessionArtifacts",
    # Vision
    "VisionAnalyzer",
    "OCRBackend",
    "TesseractOCR",
    "EasyOCRBackend",
    "create_vision_analyzer",
    # Recorder
    "VideoRecorder",
    "RecordingConfig",
    "RecordingMetadata",
    # Manager (punto de entrada principal para conectores)
    "BrowserManager",
    "BrowserManagerConfig",
    "create_browser_manager",
]