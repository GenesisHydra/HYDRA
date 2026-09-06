"""
HYDRA Mail Module
Handles Gmail API integration for sending and receiving emails.
"""

import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import HYDRA Vault
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from hydra.vault import get_vault

# If modifying these scopes, delete the google/token secret from the vault.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_gmail_service():
    """Authenticate and return Gmail service object.
    Assumes that a valid refresh token is stored in the vault under 'google/token'.
    If not present, raises an error instructing the user to run bootstrap.
    """
    vault = get_vault()
    token_json = vault.get_secret('google/token')
    if not token_json:
        raise RuntimeError(
            "Gmail token not found in vault. Please run the bootstrap script:\n"
            "  python -m src.hydra.mail.bootstrap_gmail\n"
            "to authorize and store the refresh token."
        )
    try:
        creds = Credentials.from_authorized_user_info(token_json, SCOPES)
    except Exception as e:
        raise RuntimeError(f"Failed to load credentials from vault: {e}")
    
    # If expired but refresh token exists, refresh
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save refreshed token back to vault
            vault.set_secret('google/token', creds.to_json())
        except Exception as e:
            raise RuntimeError(f"Failed to refresh token: {e}")
    
    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except HttpError as error:
        print(f'An error occurred while building Gmail service: {error}')
        return None

def send_message(to, subject, body, cc=None, bcc=None):
    """Send an email message.
    
    Args:
        to: Recipient email address (string or list)
        subject: Email subject
        body: Email body (plain text)
        cc: CC recipients (optional)
        bcc: BCC recipients (optional)
    
    Returns:
        Sent message object or None if error
    """
    service = get_gmail_service()
    if not service:
        return None
    
    try:
        message = MIMEMultipart()
        message['to'] = ', '.join(to) if isinstance(to, list) else to
        message['subject'] = subject
        if cc:
            message['cc'] = ', '.join(cc) if isinstance(cc, list) else cc
        if bcc:
            message['bcc'] = ', '.join(bcc) if isinstance(bcc, list) else bcc
        
        message.attach(MIMEText(body, 'plain'))
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {'raw': raw_message}
        
        sent_message = service.users().messages().send(
            userId='me', body=body).execute()
        return sent_message
    except HttpError as error:
        print(f'An error occurred while sending message: {error}')
        return None

def list_messages(max_results=10, query=''):
    """List messages from the user's mailbox.
    
    Args:
        max_results: Maximum number of messages to return
        query: Search query (same format as Gmail search)
    
    Returns:
        List of message dictionaries
    """
    service = get_gmail_service()
    if not service:
        return []
    
    try:
        results = service.users().messages().list(
            userId='me', maxResults=max_results, q=query).execute()
        messages = results.get('messages', [])
        return messages
    except HttpError as error:
        print(f'An error occurred while listing messages: {error}')
        return []

def get_message(message_id):
    """Get a specific message by ID.
    
    Args:
        message_id: ID of the message to retrieve
    
    Returns:
        Message dictionary or None if error
    """
    service = get_gmail_service()
    if not service:
        return None
    
    try:
        message = service.users().messages().get(
            userId='me', id=message_id, format='full').execute()
        return message
    except HttpError as error:
        print(f'An error occurred while getting message: {error}')
        return None

def create_label(label_name):
    """Create a new label in the user's mailbox.
    
    Args:
        label_name: Name of the label to create
    
    Returns:
        Created label object or None if error
    """
    service = get_gmail_service()
    if not service:
        return None
    
    try:
        label_object = {
            'name': label_name,
            'labelListVisibility': 'labelShow',
            'messageListVisibility': 'show'
        }
        label = service.users().labels().create(
            userId='me', body=label_object).execute()
        return label
    except HttpError as error:
        print(f'An error occurred while creating label: {error}')
        return None

def add_label_to_message(message_id, label_id):
    """Add a label to a specific message.
    
    Args:
        message_id: ID of the message
        label_id: ID of the label to add
    
    Returns:
        Modified message object or None if error
    """
    service = get_gmail_service()
    if not service:
        return None
    
    try:
        message = service.users().messages().modify(
            userId='me', id=message_id,
            body={'addLabelIds': [label_id]}).execute()
        return message
    except HttpError as error:
        print(f'An error occurred while adding label: {error}')
        return None

def search_messages(query, max_results=10):
    """Search for messages matching a query.
    
    Args:
        query: Search query (same format as Gmail search)
        max_results: Maximum number of results to return
    
    Returns:
        List of message dictionaries
    """
    return list_messages(max_results=max_results, query=query)

def get_message_plain_text(message):
    """Extract plain text body from a message object.
    
    Args:
        message: Message object as returned by get_message()
    
    Returns:
        Plain text body as string, or empty string if not found
    """
    if not message:
        return ''
    
    payload = message.get('payload', {})
    parts = payload.get('parts', [])
    
    if not parts:
        # Simple message without parts
        body = payload.get('body', {}).get('data', '')
        if body:
            return base64.urlsafe_b64decode(body).decode('utf-8')
        return ''
    
    # Look for text/plain part
    for part in parts:
        mime_type = part.get('mimeType')
        if mime_type == 'text/plain':
            data = part.get('body', {}).get('data', '')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8')
        # If nested parts, recurse (simplified: only one level)
        elif 'parts' in part:
            for subpart in part['parts']:
                if subpart.get('mimeType') == 'text/plain':
                    data = subpart.get('body', {}).get('data', '')
                    if data:
                        return base64.urlsafe_b64decode(data).decode('utf-8')
    
    return ''

# Example usage and test function
def test_gmail_integration():
    """Run a series of tests to verify Gmail integration works."""
    print("=== HYDRA Mail Integration Test ===")
    
    # Test 1: Authenticate and get service
    print("\n1. Authenticating with Gmail API...")
    try:
        service = get_gmail_service()
        if service:
            print("   ✓ Authentication successful")
        else:
            print("   ✗ Authentication failed")
            return False
    except RuntimeError as e:
        print(f"   ✗ {e}")
        return False
    
    # Test 2: List recent messages
    print("\n2. Listing recent messages...")
    messages = list_messages(max_results=5)
    print(f"   ✓ Found {len(messages)} recent messages")
    
    # Test 3: Create a test label
    print("\n3. Creating test label 'HYDRA_Test'...")
    label = create_label('HYDRA_Test')
    if label:
        label_id = label.get('id')
        print(f"   ✓ Label created with ID: {label_id}")
    else:
        print("   ✗ Failed to create label")
        # Continue anyway
    
    # Test 4: Send a test email to ourselves
    print("\n4. Sending test email...")
    test_subject = "HYDRA Mail Test - " + str(os.getpid())
    test_body = f"This is a test email sent at {os.popen('date').read().strip()}\n\nHYDRA Mail integration is working!"
    sent = send_message(to='contact.genesishydra@gmail.com', 
                       subject=test_subject, 
                       body=test_body)
    if sent:
        sent_id = sent.get('id')
        print(f"   ✓ Test email sent. Message ID: {sent_id}")
        
        # Test 5: Search for the sent email
        print("\n5. Searching for sent email...")
        search_query = f'subject:"{test_subject}"'
        found_messages = search_messages(search_query, max_results=1)
        if found_messages:
            print(f"   ✓ Found {len(found_messages)} matching message(s)")
            # Test 6: Retrieve the message
            msg_id = found_messages[0]['id']
            message = get_message(msg_id)
            if message:
                body_text = get_message_plain_text(message)
                if test_body in body_text:
                    print("   ✓ Message content verified")
                else:
                    print("   ⚠ Message content mismatch")
            else:
                print("   ✗ Failed to retrieve message")
        else:
            print("   ✗ Test email not found in search")
    else:
        print("   ✗ Failed to send test email")
    
    print("\n=== Test Complete ===")
    return True

if __name__ == '__main__':
    test_gmail_integration()
