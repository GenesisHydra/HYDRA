# -------------------------------------------------------------------------
# Google Capability Registry – maps semantic capabilities to OAuth scopes.
# -------------------------------------------------------------------------
from __future__ import annotations

from typing import Dict, FrozenSet, Set

# -----------------------------------------------------------------
# 1️⃣  Capabilities for each service (semantic names, NOT OAuth scopes).
# -----------------------------------------------------------------
# - YouTube
YT_CAPABILITIES: FrozenSet[str] = frozenset({
    "upload_video",
    "update_metadata",
    "thumbnails",
    "playlists",
    "analytics",
    "comments",
})

# - Gmail
GM_CAPABILITIES: FrozenSet[str] = frozenset({
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

# - Drive
DRIVE_CAPABILITIES: FrozenSet[str] = frozenset({
    "upload",
    "download",
    "share",
    "search",
    "folders",
})

# - Calendar
CA_CAPABILITIES: FrozenSet[str] = frozenset({
    "read_events",
    "create_events",
    "update_events",
    "reminders",
})

# - Sheets
SH_CAPABILITIES: FrozenSet[str] = frozenset({
    "read",
    "write",
    "formatting",
})

# - Docs
DC_CAPABILITIES: FrozenSet[str] = frozenset({
    "read",
    "write",
    "comments",
})

# -----------------------------------------------------------------
# 2️⃣  Central dictionary: service name → frozenset of capabilities.
# -----------------------------------------------------------------
SERVICE_CAPABILITIES: Dict[str, FrozenSet[str]] = {
    "youtube":    YT_CAPABILITIES,
    "gmail":      GM_CAPABILITIES,
    "drive":      DRIVE_CAPABILITIES,
    "calendar":   CA_CAPABILITIES,
    "sheets":     SH_CAPABILITIES,
    "docs":       DC_CAPABILITIES,
}

# -----------------------------------------------------------------
# 3️⃣  Inverse mapping: scope → set of capabilities that this scope
#     contributes.  Filled lazily when the module is first imported.
# -----------------------------------------------------------------
_scope_map: Dict[str, Set[str]] = {}

# -----------------------------------------------------------------
# 4️⃣  Helper: given a set of *activated* capabilities, return the minimal
#    OAuth scopes needed.  The actual mapping from capability → scope is
#    encoded in ``_scope_map`` (populated at import time).
# -----------------------------------------------------------------
def scopes_for_capabilities(activated: FrozenSet[str]) -> Set[str]:
    """Return the minimal OAuth scopes that cover the given capabilities.

    Parameters
    ----------
    activated : FrozenSet[str]
        Capability names that the user has consented to.

    Returns
    -------
    Set[str]
        OAuth scope URLs that must be present in the token.
    """
    scopes: Set[str] = set()
    for svc, caps in SERVICE_CAPABILITIES.items():
        if caps & activated:                     # at least one of these caps is active
            # add every scope that belongs to this service.
            # The service‑specific mapping lives in ``_scope_map[svc]``.
            scopes.update(_scope_map.get(svc, set()))
    return scopes


# -----------------------------------------------------------------
# 5️⃣  Populate ``_scope_map`` at import time.
#    We enumerate the official Google scopes for each service and record
#    which of the *capabilities* defined above they satisfy.
# -----------------------------------------------------------------
# --- YouTube scopes (official) ---
_YT_OFFICIAL: list[str] = [
    "https://www.googleapis.com/auth/youtube.readonly",          # covers read_events‑like, analytics
    "https://www.googleapis.com/auth/youtube.upload",            # upload_video, thumbnails, playlists
    "https://www.googleapis.com/auth/youtube.force-ssl",        # subset of upload
    "https://www.googleapis.com/auth/youtube.comments.readonly", # comments
]
for s in _YT_OFFICIAL:
    _scope_map.setdefault("youtube", set()).add(s)
# Map each YouTube capability to at least one of the official scopes (simple
# one‑to‑one for illustration – in a real deployment you would have a more
# exhaustive table).
_caps_to_yt: dict[str, str] = {
    "upload_video":   "https://www.googleapis.com/auth/youtube.upload",
    "update_metadata": "https://www.googleapis.com/auth/youtube.upload",
    "thumbnails":     "https://www.googleapis.com/auth/youtube.upload",
    "playlists":      "https://www.googleapis.com/auth/youtube.upload",
    "analytics":      "https://www.googleapis.com/auth/youtube.readonly",
    "comments":       "https://www.googleapis.com/auth/youtube.comments.readonly",
}
for cap, sc in _caps_to_yt.items():
    _scope_map["youtube"].add(sc)   # ensure the scope is present

# --- Gmail scopes (official) ---
_GM_OFFICIAL: list[str] = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.insert",   # attachments
]
for s in _GM_OFFICIAL:
    _scope_map.setdefault("gmail", set()).add(s)
_caps_to_gm: dict[str, str] = {
    "read_mail":       "https://www.googleapis.com/auth/gmail.readonly",
    "send_mail":       "https://www.googleapis.com/auth/gmail.send",
    "search":          "https://www.googleapis.com/auth/gmail.readonly",
    "archive":         "https://www.googleapis.com/auth/gmail.modify",
    "add_labels":      "https://www.googleapis.com/auth/gmail.labels",
    "remove_labels":   "https://www.googleapis.com/auth/gmail.labels",
    "mark_as_read":    "https://www.googleapis.com/auth/gmail.modify",
    "mark_as_unread":  "https://www.googleapis.com/auth/gmail.modify",
    "list_attachments":"https://www.googleapis.com/auth/gmail.readonly",
    "download_attachment":"https://www.googleapis.com/auth/gmail.readonly",
    "get_thread":      "https://www.googleapis.com/auth/gmail.readonly",
    "list_messages":   "https://www.googleapis.com/auth/gmail.readonly",
}
for cap, sc in _caps_to_gm.items():
    _scope_map["gmail"].add(sc)

# --- Drive scopes (official) ---
_DR_OFFICIAL: list[str] = [
    "https://www.googleapis.com/auth/drive.file",          # upload, download, share, folders
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive",
]
for s in _DR_OFFICIAL:
    _scope_map.setdefault("drive", set()).add(s)
_caps_to_drive: dict[str, str] = {
    "upload":   "https://www.googleapis.com/auth/drive.file",
    "download": "https://www.googleapis.com/auth/drive.file",
    "share":    "https://www.googleapis.com/auth/drive.file",
    "search":   "https://www.googleapis.com/auth/drive.file",
    "folders":  "https://www.googleapis.com/auth/drive.file",
}
for cap, sc in _caps_to_drive.items():
    _scope_map["drive"].add(sc)

# --- Calendar scopes (official) ---
_CA_OFFICIAL: list[str] = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.settings.readonly",
]
for s in _CA_OFFICIAL:
    _scope_map.setdefault("calendar", set()).add(s)
_caps_to_ca: dict[str, str] = {
    "read_events":    "https://www.googleapis.com/auth/calendar.readonly",
    "create_events":  "https://www.googleapis.com/auth/calendar.events",
    "update_events":  "https://www.googleapis.com/auth/calendar.events",
    "reminders":      "https://www.googleapis.com/auth/calendar.settings.readonly",
}
for cap, sc in _caps_to_ca.items():
    _scope_map["calendar"].add(sc)

# --- Sheets scopes (official) ---
_SH_OFFICIAL: list[str] = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]
for s in _SH_OFFICIAL:
    _scope_map.setdefault("sheets", set()).add(s)
_caps_to_sh: dict[str, str] = {
    "read":  "https://www.googleapis.com/auth/spreadsheets.readonly",
    "write": "https://www.googleapis.com/auth/spreadsheets",
    "formatting": "https://www.googleapis.com/auth/spreadsheets",
}
for cap, sc in _caps_to_sh.items():
    _scope_map["sheets"].add(sc)

# --- Docs scopes (official) ---
_DC_OFFICIAL: list[str] = [
    "https://www.googleapis.com/auth/docs.readonly",
    "https://www.googleapis.com/auth/docs",
]
for s in _DC_OFFICIAL:
    _scope_map.setdefault("docs", set()).add(s)
_caps_to_dc: dict[str, str] = {
    "read":   "https://www.googleapis.com/auth/docs.readonly",
    "write":  "https://www.googleapis.com/auth/docs",
    "comments": "https://www.googleapis.com/auth/docs",
}
for cap, sc in _caps_to_dc.items():
    _scope_map["docs"].add(sc)


# -----------------------------------------------------------------
# 6️⃣  Public helpers
# -----------------------------------------------------------------
def get_service_capabilities(service: str) -> FrozenSet[str]:
    """Return the frozenset of capabilities for *service* (or `` frozenset()``)."""
    return SERVICE_CAPABILITIES.get(service, frozenset())


def list_all_capabilities() -> Dict[str, FrozenSet[str]]:
    """Return a copy of the whole ``SERVICE_CAPABILITIES`` dict."""
    return dict(SERVICE_CAPABILITIES)