"""
Google Drive MCP limb - Native Python implementation using google-api-python-client.
Mirrors the Gmail/Calendar integration pattern.
"""
import logging
import io
from typing import List, Optional, Dict, Any

from langchain_core.tools import tool
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.db.supabase import get_connection_credentials

logger = logging.getLogger(__name__)

DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


async def _get_drive_service(user_id: str, token_data: Optional[Dict[str, Any]] = None):
    """
    Get authenticated Google Drive service.
    If token_data is provided, use it. Otherwise, fetch from Supabase.
    """
    try:
        if not token_data:
            creds_json = await get_connection_credentials(user_id, "googledrive")
            if not creds_json:
                return None
            token_data = creds_json

        creds = Credentials.from_authorized_user_info(token_data, DRIVE_SCOPES)

        if not creds.valid:
            if creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
            else:
                return None

        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        logger.error(f"Failed to create Drive service: {e}")
        return None


def get_drive_tools(user_id: str) -> List[Any]:
    """Return list of Google Drive tools, bound to the specific user_id."""

    @tool
    async def list_drive_files(max_results: int = 10) -> str:
        """
        List recent files from Google Drive.
        Args:
            max_results: Maximum number of files to return (default 10)
        """
        service = await _get_drive_service(user_id)
        if not service:
            return "Google Drive is not connected. Please connect it in Settings."

        try:
            results = service.files().list(
                pageSize=max_results,
                fields="files(id, name, mimeType, modifiedTime, owners, webViewLink)",
                orderBy="modifiedTime desc"
            ).execute()

            files = results.get('files', [])

            if not files:
                return "No files found in Google Drive."

            output = []
            for f in files:
                mime = f.get('mimeType', '')
                icon = _get_file_icon(mime)
                name = f.get('name', 'Untitled')
                modified = f.get('modifiedTime', 'Unknown')[:10]
                link = f.get('webViewLink', '')

                entry = f"{icon} **{name}**\n   Modified: {modified} | Type: {_friendly_mime(mime)}"
                if link:
                    entry += f"\n   🔗 {link}"
                output.append(entry)

            return f"Found {len(files)} file(s):\n\n" + "\n---\n".join(output)
        except Exception as e:
            logger.error(f"Error listing Drive files: {e}")
            return f"Error listing Drive files: {str(e)}"

    @tool
    async def search_drive_files(query: str, max_results: int = 10) -> str:
        """
        Search for files in Google Drive by name or content.
        Args:
            query: Search keyword (e.g., 'budget report', 'meeting notes')
            max_results: Maximum number of results (default 10)
        """
        service = await _get_drive_service(user_id)
        if not service:
            return "Google Drive is not connected. Please connect it in Settings."

        try:
            # Use Drive's fullText search
            drive_query = f"fullText contains '{query}' and trashed = false"

            results = service.files().list(
                q=drive_query,
                pageSize=max_results,
                fields="files(id, name, mimeType, modifiedTime, webViewLink)",
                orderBy="modifiedTime desc"
            ).execute()

            files = results.get('files', [])

            if not files:
                return f"No files found matching '{query}'."

            output = []
            for f in files:
                icon = _get_file_icon(f.get('mimeType', ''))
                name = f.get('name', 'Untitled')
                modified = f.get('modifiedTime', 'Unknown')[:10]
                file_id = f.get('id', '')
                output.append(f"{icon} **{name}** (ID: {file_id})\n   Modified: {modified}")

            return f"Found {len(files)} file(s) matching '{query}':\n\n" + "\n---\n".join(output)
        except Exception as e:
            logger.error(f"Error searching Drive files: {e}")
            return f"Error searching Drive files: {str(e)}"

    @tool
    async def read_drive_file(file_id: str) -> str:
        """
        Read the content of a Google Drive file by its ID.
        Supports Google Docs, Sheets (as CSV), and plain text files.
        Args:
            file_id: The file ID from Google Drive (get this from search_drive_files or list_drive_files)
        """
        service = await _get_drive_service(user_id)
        if not service:
            return "Google Drive is not connected. Please connect it in Settings."

        try:
            # Get file metadata first
            file_meta = service.files().get(
                fileId=file_id,
                fields="name, mimeType"
            ).execute()

            mime = file_meta.get('mimeType', '')
            name = file_meta.get('name', 'Untitled')

            # Google Docs → export as plain text
            if mime == 'application/vnd.google-apps.document':
                content = service.files().export(
                    fileId=file_id,
                    mimeType='text/plain'
                ).execute()
                text = content.decode('utf-8') if isinstance(content, bytes) else str(content)
                return f"📄 **{name}** (Google Doc)\n\n{text[:3000]}"

            # Google Sheets → export as CSV
            elif mime == 'application/vnd.google-apps.spreadsheet':
                content = service.files().export(
                    fileId=file_id,
                    mimeType='text/csv'
                ).execute()
                text = content.decode('utf-8') if isinstance(content, bytes) else str(content)
                return f"📊 **{name}** (Google Sheet)\n\n{text[:3000]}"

            # Google Slides → export as plain text
            elif mime == 'application/vnd.google-apps.presentation':
                content = service.files().export(
                    fileId=file_id,
                    mimeType='text/plain'
                ).execute()
                text = content.decode('utf-8') if isinstance(content, bytes) else str(content)
                return f"📽️ **{name}** (Google Slides)\n\n{text[:3000]}"

            # Plain text / CSV / JSON / code files → download directly
            elif mime.startswith('text/') or mime in ['application/json', 'application/xml']:
                from googleapiclient.http import MediaIoBaseDownload
                request = service.files().get_media(fileId=file_id)
                buffer = io.BytesIO()
                downloader = MediaIoBaseDownload(buffer, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
                text = buffer.getvalue().decode('utf-8', errors='replace')
                return f"📄 **{name}**\n\n{text[:3000]}"

            else:
                return f"📎 **{name}** — File type '{_friendly_mime(mime)}' cannot be read as text. Use the Google Drive link to view it."

        except Exception as e:
            logger.error(f"Error reading Drive file: {e}")
            return f"Error reading Drive file: {str(e)}"

    return [list_drive_files, search_drive_files, read_drive_file]


def _get_file_icon(mime: str) -> str:
    """Return an emoji icon based on MIME type."""
    if 'document' in mime or 'text' in mime:
        return '📄'
    elif 'spreadsheet' in mime or 'csv' in mime:
        return '📊'
    elif 'presentation' in mime:
        return '📽️'
    elif 'image' in mime:
        return '🖼️'
    elif 'pdf' in mime:
        return '📕'
    elif 'folder' in mime:
        return '📁'
    elif 'video' in mime:
        return '🎬'
    elif 'audio' in mime:
        return '🎵'
    return '📎'


def _friendly_mime(mime: str) -> str:
    """Convert MIME type to a friendly name."""
    mapping = {
        'application/vnd.google-apps.document': 'Google Doc',
        'application/vnd.google-apps.spreadsheet': 'Google Sheet',
        'application/vnd.google-apps.presentation': 'Google Slides',
        'application/vnd.google-apps.folder': 'Folder',
        'application/pdf': 'PDF',
        'text/plain': 'Text',
        'text/csv': 'CSV',
        'application/json': 'JSON',
        'image/png': 'PNG Image',
        'image/jpeg': 'JPEG Image',
    }
    return mapping.get(mime, mime.split('/')[-1])
