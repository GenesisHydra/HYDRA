from typing import FrozenSet, Set
from hydra.google.capabilities import scopes_for_capabilities
from hydra.google.scope_manager import ScopeManager

# --------------------------------------------------------------
# Capabilities for Gmail (semantic names)
# --------------------------------------------------------------
CAPABILITIES: FrozenSet[str] = frozenset({
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

# --------------------------------------------------------------
# Mapping from capabilities to OAuth scopes (via ScopeManager)
# --------------------------------------------------------------
# The ScopeManager uses the registry to translate, but we provide a
# direct helper for Gmail because the mapping is stable.
# --------------------------------------------------------------
def capabilities_to_scopes(activated: Set[str] | None = None) -> Set[str]:
    """
    Return the minimal OAuth scopes needed for the activated Gmail capabilities.
    If *activated* is None, returns scopes for all CAPABILITIES.
    """
    if activated is None:
        activated = set(CAPABILITIES)
    # Use the global ScopeManager to resolve scopes.
    # ScopeManager.scopes_for_capabilities expects a frozenset of capabilities
    # from the global registry; we delegate to it for consistency.
    from hydra.google.scope_manager import ScopeManager as SM
    return SM.scopes_for_capabilities(frozenset(activated))


# -----------------------------------------------------------------
# Helper: check whether a given set of OAuth scopes covers the capabilities
# -----------------------------------------------------------------
def scopes_cover_capabilities(scopes: Set[str], capabilities: FrozenSet[str] | None = None) -> bool:
    """True if the supplied OAuth scopes cover the (optional) capabilities set."""
    if capabilities is None:
        capabilities = CAPABILITIES
    needed = scopes_for_capabilities(capabilities)  # scopes required by registry
    return needed.issubset(scopes)


# -----------------------------------------------------------------
# Exported class that holds the static capability information
# -----------------------------------------------------------------
class GmailCapabilities:
    """Static container for Gmail semantic capabilities."""

    @property
    def all(self) -> FrozenSet[str]:
        return CAPABILITIES

    def __contains__(self, item: str) -> bool:
        return item in CAPABILITIES

    def __iter__(self):
        return iter(CAPABILITIES)

    def __len__(self) -> int:
        return len(CAPABILITIES)

    def __repr__(self) -> str:
        return f"GmailCapabilities({CAPABILITIES!r})"