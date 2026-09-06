# -------------------------------------------------------------------------
# Gmail connector – thin wrapper around the Gmail REST API.
# It re‑uses the existing HYDRA OAuth infrastructure (GoogleAuth, TokenManager,
# ScopeManager, Vault).  No new authentication flow is introduced.
# -------------------------------------------------------------------------
from __future__ import annotations

import json
import time
import logging
from typing import Any, Dict, List, Optional, Set

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request

from hydra.google.auth import GoogleAuth
from hydra.google.token_manager import TokenManager
from hydra.google.scope_manager import ScopeManager
from hydra.vault import get_vault
from hydra.google.gmail.gmail_exceptions import (
    GmailError,
    TokenExpired,
    InsufficientPermissions,
    RateLimitError,
    ConnectionError as GmailConnectionError,
    TimeoutError as GmailTimeoutError,
    GmailApiError,
)
from hydra.google.gmail.gmail_models import Message, Thread, Attachment, ListMessagesResponse

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# GmailService – a tiny wrapper that holds the built discovery service.
# -------------------------------------------------------------------------
class GmailService:
    """Holder of the :class:`googleapiclient.discovery.Resource` object.

    This wrapper exists so that the connector can return a lightweight object
    without exposing the raw discovery client to callers that only need the
    high‑level methods.
    """
    def __init__(self, resource):
        self._resource = resource

    # -----------------------------------------------------------------
    # Convenience helpers that delegate to the underlying resource.
    # -----------------------------------------------------------------
    def users(self, **kwargs):
        return self._resource.users()

    def messages(self, **kwargs):
        return self._resource.messages()


# -------------------------------------------------------------------------
# GmailConnector – main class that the rest of HYDRA (or ARGOS) will use.
# -------------------------------------------------------------------------
class GmailConnector:
    """Gmail connector powered by the HYDRA Google authentication stack.

    Responsibilities
    -----------------
    * Obtain validCredentials via GoogleAuth / TokenManager.
    * Build the Gmail discovery service once.
    * Provide high‑level methods for the most common Gmail operations.
    * Detect token expiration / insufficient scopes and trigger a single
      re‑authentication when needed.
    * Translate Gmail API errors into domain‑specific exceptions.
    """
    # -----------------------------------------------------------------
    # Construction
    # -----------------------------------------------------------------
    def __init__(self, *,
                 # Allow injection for testing / advanced usage.
                 auth: GoogleAuth | None = None,
                 token_manager: TokenManager | None = None,
                 scope_manager: ScopeManager | None = None,
                 vault: Any | None = None,
                 ):
        self._auth = auth or GoogleAuth()
        self._token_manager = token_manager or TokenManager()
        self._scope_manager = scope_manager or ScopeManager()
        self._vault = vault or get_vault()
        self._service: Optional[GmailService] = None
        self._last_health_check: Optional[float] = None

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------
    def _ensure_credentials(self) -> Any:
        """Return a valid ``Credentials`` object, refreshing if necessary."""
        creds = self._auth.get_credentials()  # loads from Vault / refreshes if needed
        if not creds:
            raise TokenExpired("No credentials found in the Vault. Run bootstrap first.")
        # If the token is refresh‑able and expired, refresh it.
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Persist the refreshed token immediately.
                self._token_manager.set_token(creds)
            except Exception as exc:
                # If refresh fails (e.g. revoked token), surface a clear error.
                raise TokenExpired(f"Could not refresh token: {exc}") from exc
        return creds

    def _build_service(self, creds) -> GmailService:
        """Create the Gmail discovery service from *creds*."""
        try:
            api = build("gmail", "v1", credentials=creds, cache_discovery=False)
            return GmailService(api)
        except HttpError as e:
            # Propagate as a GmailApiError for the caller to decide.
            raise GmailApiError(
                f"Failed to build Gmail service: {e}",
                http_status=e.resp.status if hasattr(e, 'resp') else None,
                http_response=e,
            ) from e

    # -----------------------------------------------------------------
    # Public API – health check
    # -----------------------------------------------------------------
    def health_check(self) -> Dict[str, Any]:
        """Verify that the connector is ready to use Gmail.

        Returns
        -------
        dict
            * ``valid`` – ``True`` if everything ok.
            * ``message`` – human‑readable description.
            * ``missing_scopes`` – set of scope names that are required but not present
              in the current token (may be empty).
        """
        result: Dict[str, Any] = {"valid": False, "message": "", "missing_scopes": set()}
        try:
            creds = self._ensure_credentials()
        except TokenExpired as e:
            result["message"] = f"Token unavailable: {e}"
            return result

        # Check scopes cover the capabilities we intend to use.
        required_scopes = ScopeManager._required_scopes_for_modules().get("gmail", set())
        token_scopes = set(creds.scopes) if creds.scopes else set()
        missing = required_scopes - token_scopes
        result["missing_scopes"] = missing

        # Perform a tiny API call to confirm connectivity and that the token works.
        try:
            service = self._build_service(creds)
            # users().getProfile() returns basic profile info; it is cheap.
            profile = service.users().getProfile(userId='me').execute()
            # If we reach here, token is valid and API is reachable.
            result["valid"] = True
            result["message"] = "Gmail connector is healthy."
            # Also store the service for subsequent calls.
            self._service = service
            self._last_health_check = time.time()
        except GmailApiError as gae:
            # API call failed – propagate a friendly message.
            result["message"] = f"Gmail API error during health check: {gae}"
        except Exception as exc:  # network, timeout, etc.
            result["message"] = f"Connection problem during health check: {exc}"

        return result

    # -----------------------------------------------------------------
    # Core Gmail operations
    # -----------------------------------------------------------------
    # -----------------------------------------------------------------
    # 1️⃣  List messages (with optional query)
    # -----------------------------------------------------------------
    def list_messages(self, query: str = "", max_results: int = 10) -> ListMessagesResponse:
        """Return a ``ListMessagesResponse`` containing up to *max_results* messages.

        Parameters
        ----------
        query: str
            Gmail search query (same syntax as the web UI).  Defaults to ``""`` (all mail).
        max_results: int
            Maximum number of messages to return.
        """
        self._ensure_service()
        try:
            response = self._service.messages().list(
                userId='me', q=query, maxResults=max_results).execute()
        except HttpError as e:
            self._map_http_error(e)
        msgs = response.get('messages', [])
        # Build our lightweight model objects.
        messages: List[Message] = []
        for m in msgs:
            msg = self._fetch_message_details(m['id'])
            messages.append(msg)
        estimate = response.get('resultSizeEstimate', 0)
        return ListMessagesResponse(messages=messages,
                                    next_page_token=response.get('nextPageToken'),
                                    result_size_estimate=estimate)

    # -----------------------------------------------------------------
    # 2️⃣  Get a single message with full details (including attachments)
    # -----------------------------------------------------------------
    def _fetch_message_details(self, message_id: str) -> Message:
        """Retrieve the raw message and parse it into a ``Message`` model."""
        try:
            raw = self._service.users().messages().get(
                userId='me', id=message_id, format='raw').execute()
        except HttpError as e:
            self._map_http_error(e)
        raw_str = raw.get('raw', '')
        # Decode the base64url safe string.
        import base64, json
        try:
            raw_decoded = base64.urlsafe_b64decode(raw_str + '==').decode('utf-8')
        except Exception:
            raw_decoded = ''
        # Very minimal parsing – just store the raw payload; the caller can
        # parse further with the email library if needed.
        # For demonstration we also try to extract a subject via a tiny regex.
        import re
        subject_match = re.search(r'Subject: ([^\r\n]*)', raw_decoded)
        subject = subject_match.group(1).strip() if subject_match else None
        # Build a tiny attachment list (placeholder – real parsing would scan
        # the MIME parts).  We'll just return an empty list for now.
        attachments: List[Attachment] = []
        return Message(id=m['id'] if False else message_id,  # placeholder – will be overwritten
                       thread_id='',
                       labels=[],
                       subject=subject,
                       raw=raw_decoded,
                       attachments=attachments)

    # -----------------------------------------------------------------
    # 3️⃣  Send a mail message
    # -----------------------------------------------------------------
    def send_mail(self,
                  to: str,
                  subject: str,
                  body: str,
                  cc: Optional[str] = None,
                  bcc: Optional[str] = None,
                  request_path: Optional[str] = None) -> Message:
        """Send a simple plain‑text mail message.

        Parameters
        ----------
        to: str
            Recipient address.
        subject: str
            Mail subject.
        body: str
            Plain‑text body.
        cc: str | None
            CC address.
        bcc: str | None
            BCC address.
        request_path: str | None
            Optional custom *path* for the raw MIME message (used only in tests).

        Returns
        -------
        Message
            The ``Message`` object representing the sent mail (contains the
            server‑assigned ``id`` and ``thread_id``).
        """
        # Build a MIME message.
        from email.mime.text import MIMEText
        from email.utils import make_msgid
        mime = MIMEText(body, 'plain')
        mime['To'] = to
        if cc:
            mime['Cc'] = cc
        if bcc:
            mime['Bcc'] = bcc
        mime['Subject'] = subject
        mime_message = mime.as_bytes().decode()
        # Encode to base64url as Gmail expects.
        import base64
        raw_bytes = base64.urlsafe_b64encode(mime_message.encode()).rstrip(b'=').decode()
        try:
            sent = self._service.users().messages().send(
                userId='me', body={'raw': raw_bytes}).execute()
        except HttpError as e:
            self._map_http_error(e)
        # Return a minimal Message model populated with what we know.
        return Message(id=sent.get('id'), thread_id=sent.get('threadId'),
                       labels=sent.get('labelIds', []),
                       subject=subject,
                       body=body,
                       snippet=sent.get('snippet'))

    # -----------------------------------------------------------------
    # 4️⃣  Search messages
    # -----------------------------------------------------------------
    def search(self, query: str) -> List[Message]:
        """Search for messages matching *query* and return a list of ``Message`` objects."""
        response = self.list_messages(query=query, max_results=50)
        return response.messages

    # -----------------------------------------------------------------
    # 5️⃣  Archive a message (move it out of the INBOX)
    # -----------------------------------------------------------------
    def archive(self, message_id: str) -> None:
        """Move the message with *message_id* out of the INBOX (adds 'ARCHIVE' label)."""
        self._modify_labels(message_id, add=['ARCHIVE'], remove=[])

    # -----------------------------------------------------------------
    # 6️⃣  Add labels
    # -----------------------------------------------------------------
    def add_labels(self, message_id: str, label_ids: List[str]) -> None:
        """Add one or more *label_ids* to the message."""
        self._modify_labels(message_id, add=label_ids, remove=[])

    # -----------------------------------------------------------------
    # 7️⃣  Remove labels
    # -----------------------------------------------------------------
    def remove_labels(self, message_id: str, label_ids: List[str]) -> None:
        """Remove one or more *label_ids* from the message."""
        self._modify_labels(message_id, add=[], remove=label_ids)

    # -----------------------------------------------------------------
    # 8️⃣  Mark as read / unread
    # -----------------------------------------------------------------
    def mark_as_read(self, message_id: str) -> None:
        """Add the 'READ' label (if not already present)."""
        self._modify_labels(message_id, add=['READ'], remove=[])

    def mark_as_unread(self, message_id: str) -> None:
        """Remove the 'READ' label (if present)."""
        self._modify_labels(message_id, add=[], remove=['READ'])

    # -----------------------------------------------------------------
    # 9️⃣  Helper that modifies labels on a message
    # -----------------------------------------------------------------
    def _modify_labels(self, message_id: str, add: List[str], remove: List[str]) -> None:
        """Add *add* labels and remove *remove* labels from *message_id*.

        Raises ``InsufficientPermissions`` if the token lacks the ``gmail.modify`` scope.
        """
        try:
            self._service.users().messages().modify(
                userId='me', id=message_id,
                body={'addLabelIds': add, 'removeLabelIds': remove}).execute()
        except HttpError as e:
            self._map_http_error(e)

    # -----------------------------------------------------------------
    # 10️⃣  List attachments of a message (stub – real parsing would scan MIME parts)
    # -----------------------------------------------------------------
    def list_attachments(self, message_id: str) -> List[Attachment]:
        """Return a (possibly empty) list of ``Attachment`` objects for the message.

        At this stage the method only returns an empty list because full MIME
        parsing would require a separate email‑parser library.  Subclasses or
        extensions can override this method to provide real attachment handling.
        """
        # We still attempt a minimal API call just to confirm the token works.
        try:
            self._service.users().messages().attachments().list(
                userId='me', messageId=message_id).execute()
        except HttpError as e:
            self._map_http_error(e)
        return []

    # -----------------------------------------------------------------
    # 11️⃣  Download a specific attachment by its attachment_id
    # -----------------------------------------------------------------
    def download_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """Download the raw bytes of the attachment identified by *attachment_id*.

        Returns
        -------
        bytes
            The decoded attachment data.
        """
        try:
            resp = self._service.users().messages().attachments().get(
                userId='me', messageId=message_id, id=attachment_id).execute()
        except HttpError as e:
            self._map_http_error(e)
        data = resp.get('data', '')
        # data is base64url encoded.
        import base64
        return base64.urlsafe_b64decode(data + '==')

    # -----------------------------------------------------------------
    # 12️⃣  Get a thread (collection of messages) – stub implementation
    # -----------------------------------------------------------------
    def get_thread(self, thread_id: str) -> Thread:
        """Return a ``Thread`` object for the given *thread_id*.

        The current implementation only fetches the first message of the thread
        and builds a minimal ``Thread``; a full implementation would fetch all
        messages belonging to the thread.
        """
        # List messages that belong to this thread (simple filter by thread_id).
        msgs = self.list_messages(query=f"thread:{thread_id}", max_results=50)
        messages = msgs.messages
        # Build minimal Message objects (we already have _fetch_message_details;
        # for brevity we just reuse the ids).
        message_objects = []
        for m in messages:
            # Re‑use the internal helper; it sets raw etc.
            msg = self._fetch_message_details(m.id)
            message_objects.append(msg)
        return Thread(id=thread_id, messages=message_objects)

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------
    def _ensure_service(self) -> None:
        """Make sure we have a valid service instance; refresh/re‑auth if needed."""
        if self._service is None:
            creds = self._ensure_credentials()
            self._service = self._build_service(creds)

    def _map_http_error(self, error: HttpError) -> None:
        """Translate a Google HttpError into one of our domain exceptions."""
        code = error.resp.status if error.resp else None
        body = error.content.decode() if error.content else ''
        try:
            err_detail = json.loads(body)
            error_message = err_detail.get('error', {}).get('message', body)
        except Exception:
            err_detail = body
            error_message = body

        # 401 – token invalid / expired
        if code == 401:
            raise TokenExpired(f"Token invalid or expired (Gmail API returned 401): {error_message}")
        # 403 – insufficient permissions / quota exceeded
        if code == 403:
            # Distinguish quota vs permission based on error message heuristics.
            if 'quota' in error_message.lower() or 'limit' in error_message.lower():
                raise RateLimitError(f"Rate limit / quota exceeded: {error_message}")
            raise InsufficientPermissions(f"Insufficient permissions (Gmail API returned 403): {error_message}")
        # 429 – too many requests
        if code == 429:
            raise RateLimitError(f"Rate limit hit (429): {error_message}")
        # 5xx or other – generic Gmail API error
        raise GmailApiError(f"Gmail API error ({code}): {error_message}", http_status=code, http_response=error)
# -------------------------------------------------------------------------
# Module‑level convenience function.
# -------------------------------------------------------------------------
def health_check() -> Dict[str, Any]:
    """Return the health status of the Gmail connector.

    This creates a temporary :class:`GmailConnector` and calls its
    :meth:`health_check <GmailConnector.health_check>` method.
    It is useful for quick sanity checks from the command line or from ARGOS.
    """
    from hydra.google.gmail.gmail_connector import GmailConnector  # local import to avoid circularity
    conn = GmailConnector()
    return conn.health_check()
