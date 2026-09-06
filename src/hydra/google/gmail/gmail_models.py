from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class Attachment:
    """Minimal representation of a Gmail attachment."""
    attachment_id: str
    size: int
    filename: Optional[str] = None
    mime_type: Optional[str] = None

    def download(self, service) -> bytes:
        """Download the attachment using the given Gmail service object."""
        import io
        response = service.users().messages().attachments().get(
            userId='me', messageId=self.message_id, id=self.attachment_id).execute()
        return response.get('data', b'').encode() if isinstance(response.get('data'), str) else response.get('data', b'')

@dataclass
class Message:
    """Minimal representation of a Gmail message."""
    id: str
    thread_id: str
    labels: List[str] = field(default_factory=list)
    subject: Optional[str] = None
    body: Optional[str] = None
    snippet: Optional[str] = None
    raw: Optional[str] = None
    attachments: List[Attachment] = field(default_factory=list)

    def get_body_plain(self, service) -> str:
        """Return the plain‑text body of the message."""
        from email import message_from_string
        msg = message_from_string(self.raw) if self.raw else None
        if msg:
            payload = msg.get_payload(decode=True)
            if payload:
                return payload.decode('utf-8')
        return ''

@dataclass
class Thread:
    """Minimal representation of a Gmail conversation thread."""
    id: str
    messages: List[Message] = field(default_factory=list)
    subject: Optional[str] = None

    @property
    def latest_message(self) -> Optional[Message]:
        return self.messages[-1] if self.messages else None


@dataclass
class ListMessagesResponse:
    """Response from listing messages."""
    messages: List[Message] = field(default_factory=list)
    next_page_token: Optional[str] = None
    result_size_estimate: int = 0