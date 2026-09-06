# -------------------------------------------------------------------------
# ScopeManager – central registry of OAuth scopes for Google services.
# -------------------------------------------------------------------------
from __future__ import annotations

from typing import Dict, FrozenSet, Set, Tuple

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from hydra.google.capabilities import (
    SERVICE_CAPABILITIES,
    scopes_for_capabilities,
    get_service_capabilities,
)
from hydra.google.modules.base import GoogleModule
from hydra.google.modules.gmail_module import GmailModule
from hydra.google.modules.youtube_module import YouTubeModule
from hydra.google.modules.drive_module import DriveModule
from hydra.google.modules.calendar_module import CalendarModule
from hydra.google.modules.sheets_module import SheetsModule
from hydra.google.modules.docs_module import DocsModule
from hydra.vault import get_vault


class ScopeManager:
    """Responsible for building the set of OAuth scopes required by the
    currently registered ``GoogleModule``\ s and for checking whether the
    token stored in the Vault satisfies those requirements.

    The public API is deliberately small – most of the work is done inside
    the helper methods that translate *capabilities* (semantic names) into
    OAuth scopes.
    """

    # -----------------------------------------------------------------
    # 1️⃣  Registered modules – each module declares its capabilities.
    # -----------------------------------------------------------------
    _modules: Dict[str, GoogleModule] = {
        "youtube":  YouTubeModule(),
        "gmail":    GmailModule(),
        "drive":    DriveModule(),
        "calendar": CalendarModule(),
        "sheets":   SheetsModule(),
        "docs":     DocsModule(),
    }

    # -----------------------------------------------------------------
    # 2️⃣  Helper: required scopes for *all* modules.
    # -----------------------------------------------------------------
    @staticmethod
    def _required_scopes_for_modules() -> Dict[str, Set[str]]:
        """Return ``{module_name: set_of_oauth_scopes_needed}``.

        The scopes are derived from each module's ``capabilities`` property
        (via the global ``GoogleCapabilityRegistry``).
        """
        result: Dict[str, Set[str]] = {}
        for name, mod in ScopeManager._modules.items():
            # Gather *all* capabilities (obligatory + opcionales + future).
            all_caps = mod.capabilities | mod.optional_capabilities | mod.future_capabilities
            result[name] = scopes_for_capabilities(all_caps)
        return result

    # -----------------------------------------------------------------
    # 3️⃣  Detect missing scopes.
    # -----------------------------------------------------------------
    @staticmethod
    def missing_scopes() -> Tuple[Set[str], Dict[str, Set[str]]]:
        """Return ``(missing_global, per_module)``.

        *missing_global* – set of scopes that are required by *any* module but
        not present in the current token.

        *per_module* – ``{module_name: set_of_missing_scopes_for_that_module}``.
        """
        # Load the token once.
        from hydra.google.auth import GoogleAuth
        auth = GoogleAuth()
        token_scopes: Set[str] = set()
        creds = auth.get_credentials()
        if creds and creds.scopes:
            token_scopes = set(creds.scopes)

        required_per_mod = ScopeManager._required_scopes_for_modules()
        missing_global: Set[str] = set()
        per_module: Dict[str, Set[str]] = {}

        for mod, needed in required_per_mod.items():
            have = token_scopes.intersection(needed)
            mod_missing = needed - have
            if mod_missing:
                per_module[mod] = mod_missing
                missing_global.update(mod_missing)

        return missing_global, per_module

    # -----------------------------------------------------------------
    # 4️⃣  Validation – are all scopes present?
    # -----------------------------------------------------------------
    @staticmethod
    def validate() -> Tuple[bool, str]:
        """Return ``(ok, message)``.

        *ok* is ``True`` iff every module's mandatory scopes are present in
        the token.
        """
        missing, _ = ScopeManager.missing_scopes()
        if not missing:
            return True, "✓ All scopes available."
        # Build a human‑readable list.
        missing_list = sorted(missing)
        msg = f"⚠ Missing scopes: {', '.join(missing_list)}"
        return False, msg

    # -----------------------------------------------------------------
    # 5️⃣  Re‑authorisation (one‑shot).
    # -----------------------------------------------------------------
    @staticmethod
    def request_reauthorisation() -> bool:
        """Run the one‑time bootstrap flow (InstalledAppFlow with PKCE, loopback redirect).

        In production this would launch the browser on the operator's PC and
        wait for the OAuth redirect.  Here we raise an informative error so
        the operator knows which command to run.
        """
        raise RuntimeError(
            "Bootstrap not implemented in this environment. "
            "Run: python -m hydra.mail.bootstrap_gmail  (on the operator's PC)"
        )

    # -----------------------------------------------------------------
    # 6️⃣  Expose the capabilities summary to outer layers (e.g. ARGOS).
    # -----------------------------------------------------------------
    @staticmethod
    def capabilities_summary() -> Dict[str, FrozenSet[str]]:
        """Return ``{service_name: frozenset_of_capabilities}`` for all modules.

        This is the surface that external components (e.g. ARGOS) use to
        discover what HYDRA is able to do without touching raw OAuth scopes.
        """
        summary: Dict[str, FrozenSet[str]] = {}
        for name, mod in ScopeManager._modules.items():
            summary[name] = mod.capabilities
        return summary