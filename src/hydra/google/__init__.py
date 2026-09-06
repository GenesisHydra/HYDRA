# --
print("__init__.py loaded:", __name__)
# --
# HYDRA Google package – public API surface.
# This file is intentionally kept minimal; all heavy logic lives in the
# sub‑modules (auth, scope_manager, capabilities, token_manager, gmail).

from .auth import GoogleAuth
from .scope_manager import ScopeManager
from .token_manager import TokenManager
from .gmail import GmailConnector, GmailService  # noqa: F401
from .gmail.gmail_connector import health_check  # noqa: F401

# Public API surface – these are re‑exported for convenience.
# They are imported lazily inside the respective modules to avoid circular
# import problems at package initialisation time.
# -------------------------------------------------------------------------

# Capability registry – exposed as a read‑only mapping.
# The actual dictionary lives in ``hydra.google.capabilities``.
SERVICE_CAPABILITIES = None  # placeholder; users should import from ``hydra.google.capabilities`` directly.

# -------------------------------------------------------------------------
# Convenience re‑exports for the most common use‑cases.
# -------------------------------------------------------------------------
from hydra.google.capabilities import (
    scopes_for_capabilities,
    get_service_capabilities,
    list_all_capabilities,
)  # noqa: F401

# -------------------------------------------------------------------------
# Expose the most‑used names at the top level so that `from hydra.google import ...`
# works for the typical starter script.
# -------------------------------------------------------------------------
from hydra.google.auth import GoogleAuth  # noqa: F811
from hydra.google.scope_manager import ScopeManager  # noqa: F811
from hydra.google.token_manager import TokenManager  # noqa: F811

__all__ = [
    "GoogleAuth",
    "ScopeManager",
    "TokenManager",
    "scopes_for_capabilities",
    "get_service_capabilities",
    "list_all_capabilities",
]