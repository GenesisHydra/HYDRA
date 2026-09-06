# Gmail connector package

from .gmail_connector import GmailConnector, GmailService
from .gmail_models import Message, Thread, Attachment, ListMessagesResponse
from .gmail_exceptions import (
    GmailError,
    TokenExpired,
    InsufficientPermissions,
    RateLimitError,
    ConnectionError as GmailConnectionError,
    TimeoutError as GmailTimeoutError,
    GmailApiError,
)
from .gmail_capabilities import GmailCapabilities, CAPABILITIES

__all__ = [
    "GmailConnector",
    "GmailService",
    "health_check",
    "Message",
    "Thread",
    "Attachment",
    "ListMessagesResponse",
    "GmailError",
    "TokenExpired",
    "InsufficientPermissions",
    "RateLimitError",
    "GmailConnectionError",
    "GmailTimeoutError",
    "GmailApiError",
    "GmailCapabilities",
    "CAPABILITIES",
]