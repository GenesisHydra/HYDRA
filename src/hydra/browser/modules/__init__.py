"""
Browser Modules - Módulos de fallback para HYDRA Browser.

HYDRA Browser SOLO incluye módulos genéricos de fallback.
Todos los conectores específicos de servicios viven FUERA en paquetes independientes:

    src/hydra/tradingview/     → Automatización TradingView
    src/hydra/google/          → Google (OAuth, Gmail, Drive, Calendar, YouTube)
    src/hydra/youtube/         → YouTube
    src/hydra/linkedin/        → LinkedIn
    src/hydra/x/               → X (Twitter)
    src/hydra/github/          → GitHub
    src/hydra/fundednext/      → FundedNext
    src/hydra/gomining/        → GoMining
    ...

El módulo Generic es un fallback universal para cualquier sitio web sin conector dedicado.
"""

from hydra.browser.modules.generic import GenericModule, GenericAction

# Registro de módulos disponibles DENTRO de HYDRA Browser
MODULES = {
    "generic": GenericModule,
}

# Módulos externos (fuera de HYDRA Browser) - solo referencia
EXTERNAL_MODULES = {
    "tradingview": "src/hydra/tradingview",
    "google": "src/hydra/google",
    "youtube": "src/hydra/youtube",
    "linkedin": "src/hydra/linkedin",
    "x": "src/hydra/x",
    "github": "src/hydra/github",
    "fundednext": "src/hydra/fundednext",
    "gomining": "src/hydra/gomining",
}


def get_module_class(module_name: str):
    """Obtiene clase de módulo interno por nombre."""
    if module_name in MODULES:
        return MODULES[module_name]
    raise ValueError(
        f"Módulo interno '{module_name}' no disponible. "
        f"Módulos internos: {list(MODULES.keys())}. "
        f"Para servicios externos, usa su paquete dedicado en src/hydra/<servicio>/"
    )


def create_module(
    module_name: str,
    browser_pool,
    session_manager,
    artifact_store=None,
    vision_analyzer=None,
    **kwargs,
):
    """Factory para crear instancia de módulo interno."""
    module_class = get_module_class(module_name)
    return module_class(
        browser_pool=browser_pool,
        session_manager=session_manager,
        artifact_store=artifact_store,
        vision_analyzer=vision_analyzer,
        **kwargs,
    )


__all__ = [
    "GenericModule",
    "GenericAction",
    "MODULES",
    "EXTERNAL_MODULES",
    "get_module_class",
    "create_module",
]