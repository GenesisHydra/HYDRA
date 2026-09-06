# -------------------------------------------------------------------------
# Sheets module – semantic capabilities and OAuth scope mapping.
# -------------------------------------------------------------------------
from __future__ import annotations

from typing import FrozenSet
from hydra.google.modules.base import GoogleModule


class SheetsModule(GoogleModule):
    """Semantic capability container for Google Sheets.

    Capabilities are *not* raw OAuth scopes – they are meaningful operation
    names.  The :class:`ScopeManager` translates them into the official
    Google OAuth scopes via the global ``_scope_map`` (populated in
    :mod:`hydra.google.capabilities`).
    """

    @property
    def capabilities(self) -> FrozenSet[str]:
        return frozenset({
            "read",
            "write",
            "formatting",
        })

    @property
    def optional_capabilities(self) -> FrozenSet[str]:
        return frozenset()

    @property
    def future_capabilities(self) -> FrozenSet[str]:
        return frozenset({
            "auto_grid",          # may be added later
            "conditional_formatting",  # may be added later
        })