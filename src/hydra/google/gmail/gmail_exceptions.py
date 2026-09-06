# Base exception for all Gmail connector errors
class GmailError(Exception):
    """Raised for any Gmail‑connector problem."""
    pass


# -----------------------------------------------------------------
# Token‑related errors
# -----------------------------------------------------------------
class TokenExpired(GmailError):
    """The stored refresh token has expired and could not be refreshed."""


# -----------------------------------------------------------------
# Permissions errors
# -----------------------------------------------------------------
class InsufficientPermissions(GmailError):
    """The token does not contain the scopes required for the operation."""


# -----------------------------------------------------------------
# Rate‑limit / throttling
# -----------------------------------------------------------------
class RateLimitError(GmailError):
    """The Gmail API returned a 429 (Too Many Requests) response."""


# -----------------------------------------------------------------
# Network related errors
# -----------------------------------------------------------------
class ConnectionError(GmailError):
    """No network connectivity or the request could not be resolved."""


class TimeoutError(GmailError):
    """The request timed out before a response was received."""


# -----------------------------------------------------------------
# Generic Gmail API error
# -----------------------------------------------------------------
class GmailApiError(GmailError):
    """An error returned by the Gmail API (wraps HttpError)."""

    def __init__(self, message: str, http_status: int | None = None,
                 http_response: object | None = None):
        super().__init__(message)
        self.http_status = http_status
        self.http_response = http_response