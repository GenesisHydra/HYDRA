# -------------------------------------------------------------------------
# Gmail module – semantic capabilities and OAuth scope mapping.
# -------------------------------------------------------------------------
from __future__ import annotations

from typing import FrozenSet
from hydra.google.modules.base import GoogleModule


class GmailModule(GoogleModule):
    """Semantic capability container for Gmail.

    Capabilities are *not* raw OAuth scopes – they are meaningful operation
    names.  The :class:`ScopeManager` translates them into the official
    Google OAuth scopes via the global ``_scope_map`` (populated in
    :mod:`hydra.google.capabilities`).
    """

    @property
    def capabilities(self) -> FrozenSet[str]:
        return frozenset({
            "read_mail",
            "send_mail",
            "search",
            "archive",
            "add_labels",
            "remove_labels",
            "mark_as_read",
            "mark_as_unread",
            "list_attachments",
            "download_attachment",
            "get_thread",
            "list_messages",
        })

    @property
    def optional_capabilities(self) -> FrozenSet[str]:
        return frozenset()

    @property
    def future_capabilities(self) -> FrozenSet[str]:
        return frozenset({
            "drafts",          # may be added later
            "calendar_integration",  # may be added later
        })