"""
Gmail MCP limb - Native Python implementation using google-api-python-client.
"""
import base64
import logging
from typing import List, Optional, Dict, Any
from email.mime.text import MIMEText

from langchain_core.tools import tool
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.db.supabase import get_connection_credentials

logger = logging.getLogger(__name__)

GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

async def _get_gmail_service(user_id: str, token_data: Optional[Dict[str, Any]] = None):
    """
    Get authenticated Gmail service. 
    If token_data is provided (e.g. during auth flow), use it.
    Otherwise, fetch from Supabase using user_id.
    """
    try:
        if not token_data:
            creds_json = await get_connection_credentials(user_id, "gmail")
            if not creds_json:
                return None
            token_data = creds_json

        # Reconstruct Credentials object from stored JSON
        # Expecting token_data to contain: token, refresh_token, token_uri, client_id, client_secret, scopes
        creds = Credentials.from_authorized_user_info(token_data, GMAIL_SCOPES)
        
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
            else:
                return None

        return build('gmail', 'v1', credentials=creds)
    except Exception as e:
        logger.error(f"Failed to create Gmail service: {e}")
        return None

def get_gmail_tools(user_id: str) -> List[Any]:
    """Return list of Gmail tools, bound to the specific user_id."""
    
    @tool
    async def read_recent_emails(limit: int = 5) -> str:
        """
        Read recent emails from your Gmail inbox.
        Args:
            limit: Number of emails to retrieve (default 5)
        """
        service = await _get_gmail_service(user_id)
        if not service:
            return "Gmail is not connected. Please connect Gmail in Settings."

        try:
            results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=limit).execute()
            messages = results.get('messages', [])

            if not messages:
                return "No recent emails found."

            output = []
            for msg in messages:
                txt = service.users().messages().get(userId='me', id=msg['id']).execute()
                payload = txt.get('payload', {})
                headers = payload.get('headers', [])
                
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), '(Unknown)')
                snippet = txt.get('snippet', '')
                
                # Try to get body snippet more robustly if needed
                
                output.append(f"From: {sender}\nSubject: {subject}\nSnippet: {snippet}\n---")

            return "\n".join(output)
        except Exception as e:
            logger.error(f"Error reading emails: {e}")
            return f"Error reading emails: {str(e)}"

    @tool
    async def send_email(to: str, subject: str, body: str) -> str:
        """
        Send an email via Gmail.
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
        """
        service = await _get_gmail_service(user_id)
        if not service:
            return "Gmail is not connected. Please connect Gmail in Settings."

        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            body_payload = {'raw': raw}

            sent_message = service.users().messages().send(userId='me', body=body_payload).execute()
            return f"Email sent successfully! Message ID: {sent_message['id']}"
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return f"Error sending email: {str(e)}"

    @tool
    async def search_emails(query: str, limit: int = 5) -> str:
        """
        Search emails in Gmail.
        Args:
            query: Search query (e.g. "from:boss", "subject:meeting")
            limit: Max results
        """
        service = await _get_gmail_service(user_id)
        if not service:
            return "Gmail is not connected. Please connect Gmail in Settings."

        try:
            results = service.users().messages().list(userId='me', q=query, maxResults=limit).execute()
            messages = results.get('messages', [])

            if not messages:
                return f"No emails found matching query: {query}"

            output = []
            for msg in messages:
                txt = service.users().messages().get(userId='me', id=msg['id']).execute()
                payload = txt.get('payload', {})
                headers = payload.get('headers', [])
                
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), '(Unknown)')
                snippet = txt.get('snippet', '')
                
                output.append(f"From: {sender}\nSubject: {subject}\nSnippet: {snippet}\n---")

            return "\n".join(output)
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return f"Error searching emails: {str(e)}"

    return [read_recent_emails, send_email, search_emails]
