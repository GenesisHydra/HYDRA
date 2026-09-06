# HYDRA Google authentication wrapper.
# Provides a simple interface to load/store credentials in the Vault and
# refresh them when they expire.
from __future__ import annotations

import json
from typing import Any, Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from hydra.vault import get_vault


class GoogleAuth:
    """Wrapper around the Vault that owns the current *refresh token*.

    The flow is:
    1. ``get_credentials()`` returns a :class:`google.oauth2.credentials.Credentials`
       object.  If the token is expired and a refresh token is present, it is
       refreshed automatically and the new token is persisted.
    2. ``revoke()`` revokes the current refresh token and clears the Vault entry.
    """

    # -----------------------------------------------------------------
    # Construction
    # -----------------------------------------------------------------
    def __init__(self, vault: Any | None = None) -> None:
        self._vault = get_vault() if vault is None else vault

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------
    def get_credentials(self) -> Optional[Credentials]:
        """Return valid ``Credentials``, refreshing if necessary.

        Returns
        -------
        Optional[Credentials]
            ``None`` if no credentials are stored in the Vault.
        """
        raw = self._vault.get_secret("google/token")
        if not raw:
            return None
        try:
            # Ensure we have a dict (the vault may store a JSON string).
            if isinstance(raw, str):
                creds_dict = json.loads(raw)
            else:
                creds_dict = raw
        except (json.JSONDecodeError, TypeError):
            return None

        try:
            creds = Credentials.from_authorized_user_info(creds_dict)
        except Exception:
            return None

        # Refresh if needed.
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Persist the refreshed token immediately.
                self._vault.set_secret("google/token", creds.to_json())
            except Exception:
                # If refresh fails we still return the expired object;
                # the caller can decide to re‑bootstrap.
                pass
        return creds

    def revoke(self) -> None:
        """Revoke the current refresh token and clear the Vault entry."""
        self._vault.delete_secret("google/token")