# -------------------------------------------------------------------------
# TokenManager – thin wrapper around the HYDRA Vault for refresh tokens.
# -------------------------------------------------------------------------
from __future__ import annotations

import json
from typing import Any, Optional

from google.oauth2.credentials import Credentials

from hydra.vault import get_vault


class TokenManager:
    """Very small wrapper that knows how to read/write the ``google/token`` key
    in the Vault and to expose a ``Credentials`` object to the caller.

    The actual refresh logic is delegated to ``GoogleAuth``; this class only
    persists the JSON representation.
    """

    # -----------------------------------------------------------------
    # Construction
    # -----------------------------------------------------------------
    def __init__(self, vault: Any | None = None) -> None:
        self._vault = get_vault() if vault is None else vault

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------
    def get_token(self) -> Optional[Credentials]:
        """Return a ``Credentials`` instance built from the Vault, or ``None``."""
        raw = self._vault.get_secret("google/token")
        if not raw:
            return None
        try:
            if isinstance(raw, str):
                data = json.loads(raw)
            else:
                data = raw
        except (json.JSONDecodeError, TypeError):
            return None
        try:
            return Credentials.from_authorized_user_info(data)  # type: ignore
        except Exception:
            return None

    def set_token(self, creds: Any) -> bool:
        """Persist *creds* (a ``Credentials`` instance) into the Vault.

        Returns ``True`` on success.
        """
        try:
            self._vault.set_secret("google/token", creds.to_json())
            return True
        except Exception:
            return False

    def refresh_token(self) -> Optional[Credentials]:
        """If the stored token is expired and has a refresh token, refresh it.

        Returns the new ``Credentials`` object, or ``None`` if refresh is not
        possible (e.g. revoked token).
        """
        creds = self.get_token()
        if not creds:
            return None
        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            try:
                creds.refresh(Request())
                return self.set_token(creds) and creds
            except Exception:
                return None
        return creds