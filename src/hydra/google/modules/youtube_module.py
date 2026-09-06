# -------------------------------------------------------------------------
# YouTube module – semantic capabilities and OAuth scope mapping.
# -------------------------------------------------------------------------
from __future__ import annotations

from typing import FrozenSet
from hydra.google.modules.base import GoogleModule


class YouTubeModule(GoogleModule):
    """Semantic capability container for YouTube.

    Capabilities are *not* raw OAuth scopes – they are meaningful operation
    names.  The :class:`ScopeManager` translates them into the official
    Google OAuth scopes via the global ``_scope_map`` (populated in
    :mod:`hydra.google.capabilities`).
    """

    @property
    def capabilities(self) -> FrozenSet[str]:
        return frozenset({
            "upload_video",
            "update_metadata",
            "thumbnails",
            "playlists",
            "analytics",
            "comments",
        })

    @property
    def optional_capabilities(self) -> FrozenSet[str]:
        return frozenset()

    @property
    def future_capabilities(self) -> FrozenSet[str]:
        return frozenset({
            "live_stream",          # may be added later
            "community_posts",    # may be added later
        })