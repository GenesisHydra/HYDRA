# Base class for all Google service modules.
# Each concrete module (Gmail, YouTube, Drive, ...) must sub‑class this and
# implement the three properties: capabilities, optional_capabilities,
# future_capabilities.
from abc import ABC, abstractmethod
from typing import FrozenSet, Set, List


class GoogleModule(ABC):
    """
    Semantic capability container for a Google service.

    The *ScopeManager* uses ``capabilities`` (and the optional/future sets)
    to compute the OAuth scopes that need to be present in the token.
    """

    @property
    @abstractmethod
    def capabilities(self) -> FrozenSet[str]:
        """Mandatory capabilities for the module to function."""
        ...

    @property
    @abstractmethod
    def optional_capabilities(self) -> FrozenSet[str]:
        """Capabilities that are not strictly required but may be useful."""
        ...

    @property
    @abstractmethod
    def future_capabilities(self) -> FrozenSet[str]:
        """Capabilities that may be needed in future versions of the module."""
        ...