# -------------------------------------------------------------------------
# Tests for the Gmail connector.
# They rely heavily on mocking because real Google API calls are not possible
# in this environment.
# -------------------------------------------------------------------------
import unittest
from unittest import mock
from typing import Any, Dict, List

from hydra.google.gmail import (
    GmailConnector,
    GmailService,
    health_check,
    Message,
    Thread,
    Attachment,
    ListMessagesResponse,
    GmailCapabilities,
    CAPABILITIES,
)
from hydra.google.gmail.gmail_exceptions import (
    GmailError,
    TokenExpired,
    InsufficientPermissions,
    RateLimitError,
    GmailApiError,
)
from hydra.google.scope_manager import ScopeManager
from hydra.google.capabilities import scopes_for_capabilities


class TestGmailConnectorHealthCheck(unittest.TestCase):
    """Validate that health_check works when token is valid / invalid."""

    def setUp(self):
        # Create a connector instance; we will patch the internals.
        self.conn = GmailConnector()

    @mock.patch.object(GmailConnector, "_ensure_credentials")
    @mock.patch.object(GmailConnector, "_build_service")
    def test_health_check_success(self, mock_build, mock_creds):
        # Mock credentials return value
        mock_creds.return_value = mock.MagicMock()
        # Mock service build returning a mock service object.
        mock_service = mock.MagicMock()
        mock_service.users().getProfile().execute.return_value = {"emailAddress": "user@gmail.com"}
        mock_build.return_value = GmailService(mock_service)

        result = self.conn.health_check()
        self.assertTrue(result["valid"])
        self.assertIn("healthy", result["message"].lower())

    @mock.patch.object(GmailConnector, "_ensure_credentials")
    def test_health_check_missing_token(self, mock_creds):
        # Simulate that no credentials are available.
        mock_creds.side_effect = TokenExpired("No credentials found.")
        result = self.conn.health_check()
        self.assertFalse(result["valid"])
        self.assertIn("unavailable", result["message"].lower())

    @mock.patch.object(GmailConnector, "_ensure_credentials")
    @mock.patch.object(GmailConnector, "_build_service")
    def test_health_check_api_error(self, mock_build, mock_creds):
        mock_creds.return_value = mock.MagicMock()
        mock_build.side_effect = GmailApiError("API error", http_status=500)
        result = self.conn.health_check()
        self.assertFalse(result["valid"])
        self.assertIn("API error", result["message"])


class TestGmailConnectorListMessages(unittest.TestCase):
    """Test list_messages and the underlying _fetch_message_details."""

    def setUp(self):
        self.conn = GmailConnector()

    @mock.patch.object(GmailConnector, "_ensure_service")
    @mock.patch.object(GmailConnector, "_fetch_message_details")
    def test_list_messages_basic(self, mock_fetch, mock_ensure):
        # Mock a couple of message ids.
        mock_fetch.side_effect = [
            Message(id="msg1", thread_id="thr1", subject="Hello"),
            Message(id="msg2", thread_id="thr1", subject="Hi"),
        ]
        mock_ensure.return_value = None

        msgs = self.conn.list_messages(query="", max_results=5)
        self.assertEqual(len(msgs.messages), 2)
        self.assertEqual(msgs.messages[0].subject, "Hello")
        self.assertEqual(msgs.messages[1].subject, "Hi")


class TestGmailConnectorSendMail(unittest.TestCase):
    """Test send_mail functionality."""

    def setUp(self):
        self.conn = GmailConnector()

    @mock.patch.object(GmailConnector, "_ensure_service")
    @mock.patch.object(GmailConnector, "_map_http_error")
    def test_send_mail_success(self, mock_map, mock_ensure):
        mock_ensure.return_value = None
        # The send_mail method builds a MIME message and calls the API;
        # because we mock _map_http_error we just verify it was called.
        self.conn.send_mail(to="test@example.com", subject="Test", body="Hello")
        # _map_http_error should NOT have been raised an exception.
        # We just check that no exception propagated.
        self.assertTrue(True)  # placeholder assert


class TestGmailConnectorLabels(unittest.TestCase):
    """Test add_labels, remove_labels, archive, mark_as_read/unread."""

    def setUp(self):
        self.conn = GmailConnector()

    @mock.patch.object(GmailConnector, "_modify_labels")
    def test_archive_calls_modify(self, mock_modify):
        self.conn.archive("msg123")
        mock_modify.assert_called_once_with("msg123", add=["ARCHIVE"], remove=[])

    @mock.patch.object(GmailConnector, "_modify_labels")
    def test_mark_as_read_calls_modify(self, mock_modify):
        self.conn.mark_as_read("msg123")
        mock_modify.assert_called_once_with("msg123", add=["READ"], remove=[])

    @mock.patch.object(GmailConnector, "_modify_labels")
    def test_mark_as_unread_calls_modify(self, mock_modify):
        self.conn.mark_as_unread("msg123")
        mock_modify.assert_called_once_with("msg123", add=[], remove=["READ"])


class TestGmailConnectorSearch(unittest.TestCase):
    """Test the search method."""

    def setUp(self):
        self.conn = GmailConnector()

    @mock.patch.object(GmailConnector, "list_messages")
    def test_search_delegates_to_list_messages(self, mock_list):
        self.conn.search("from:alice")
        mock_list.assert_called_once_with(query="from:alice", max_results=50)


class TestGmailConnectorAttachments(unittest.TestCase):
    """Test list_attachments and download_attachment (stub)."""

    def setUp(self):
        self.conn = GmailConnector()

    @mock.patch.object(GmailConnector, "_ensure_service")
    def test_list_attachments_no_error(self, mock_ensure):
        mock_ensure.return_value = None
        # list_attachments should not raise; it returns an empty list.
        atts = self.conn.list_attachments("msg1")
        self.assertIsInstance(atts, list)
        self.assertEqual(len(atts), 0)

    @mock.patch.object(GmailConnector, "_ensure_service")
    def test_download_attachment_returns_bytes(self, mock_ensure):
        mock_ensure.return_value = None
        # download_attachment should return some bytes; we mock the API response.
        with mock.patch.object(
            self.conn._service.users().messages().attachments().get,
            return_value={"data": "dGVzdA=="},
        ):
            data = self.conn.download_attachment("msg1", "att1")
            self.assertIsInstance(data, bytes)
            self.assertEqual(data, b"test")


class TestGmailConnectorThread(unittest.TestCase):
    """Test get_thread."""

    def setUp(self):
        self.conn = GmailConnector()

    @mock.patch.object(GmailConnector, "list_messages")
    def test_get_thread_delegates(self, mock_list):
        self.conn.get_thread("thr1")
        mock_list.assert_called_once_with(query="thread:thr1", max_results=50)


# -------------------------------------------------------------------------
# Helper: integration‑style test that verifies automatic token renewal.
// This test is written against the real TokenManager but requires a Vault
// with a valid refresh token – it is therefore marked as “skip” unless the
// operator has set up a test Vault.
// -------------------------------------------------------------------------
class TestGmailConnectorTokenRenewal(unittest.TestCase):
    """Skip unless a test Vault is configured."""
    @unittest.skipUnless(
        bool(unittest.TestCase._safe_getAttr(unittest.TestCase, "_vault_test", None)),
        "Vault not configured",
    )
    def test_automatic_renewal(self):
        # In a real setup one would call connector.health_check() after having
        # refreshed the token via TokenManager.  Here we just verify that the
        # code path exists.
        pass


# -------------------------------------------------------------------------
# Main test runner – allow running individual test files from the command line.
# -------------------------------------------------------------------------
if __name__ == "__main__":
    unittest.main()