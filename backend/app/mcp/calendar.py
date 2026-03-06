"""
Google Calendar MCP limb - Native Python implementation using google-api-python-client.
Mirrors the Gmail integration pattern.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from langchain_core.tools import tool
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.db.supabase import get_connection_credentials

logger = logging.getLogger(__name__)

CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']


async def _get_calendar_service(user_id: str, token_data: Optional[Dict[str, Any]] = None):
    """
    Get authenticated Google Calendar service.
    If token_data is provided, use it. Otherwise, fetch from Supabase.
    """
    try:
        if not token_data:
            creds_json = await get_connection_credentials(user_id, "calendar")
            if not creds_json:
                return None
            token_data = creds_json

        creds = Credentials.from_authorized_user_info(token_data, CALENDAR_SCOPES)

        if not creds.valid:
            if creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
            else:
                return None

        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        logger.error(f"Failed to create Calendar service: {e}")
        return None


def get_calendar_tools(user_id: str) -> List[Any]:
    """Return list of Google Calendar tools, bound to the specific user_id."""

    @tool
    async def list_calendar_events(max_results: int = 10, days_ahead: int = 7) -> str:
        """
        List upcoming calendar events.
        Args:
            max_results: Maximum number of events to return (default 10)
            days_ahead: Number of days ahead to look (default 7)
        """
        service = await _get_calendar_service(user_id)
        if not service:
            return "Google Calendar is not connected. Please connect it in Settings."

        try:
            now = datetime.now(timezone.utc)
            time_min = now.isoformat()
            time_max = (now + timedelta(days=days_ahead)).isoformat()

            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            if not events:
                return f"No upcoming events found in the next {days_ahead} days."

            output = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                summary = event.get('summary', '(No title)')
                location = event.get('location', '')
                description = event.get('description', '')

                entry = f"📅 **{summary}**\n   Start: {start}\n   End: {end}"
                if location:
                    entry += f"\n   📍 Location: {location}"
                if description:
                    entry += f"\n   📝 {description[:100]}"
                entry += "\n---"
                output.append(entry)

            return f"Found {len(events)} upcoming event(s):\n\n" + "\n".join(output)
        except Exception as e:
            logger.error(f"Error listing calendar events: {e}")
            return f"Error listing calendar events: {str(e)}"

    @tool
    async def create_calendar_event(
        summary: str,
        start_time: str,
        end_time: str,
        description: str = "",
        location: str = ""
    ) -> str:
        """
        Create a new Google Calendar event.
        Args:
            summary: Event title/name
            start_time: Start time in ISO format (e.g., '2025-01-15T14:00:00')
            end_time: End time in ISO format (e.g., '2025-01-15T15:00:00')
            description: Optional event description
            location: Optional event location
        """
        service = await _get_calendar_service(user_id)
        if not service:
            return "Google Calendar is not connected. Please connect it in Settings."

        try:
            event_body = {
                'summary': summary,
                'start': {
                    'dateTime': start_time,
                    'timeZone': 'Asia/Kolkata',
                },
                'end': {
                    'dateTime': end_time,
                    'timeZone': 'Asia/Kolkata',
                },
            }
            if description:
                event_body['description'] = description
            if location:
                event_body['location'] = location

            created_event = service.events().insert(
                calendarId='primary',
                body=event_body
            ).execute()

            return (
                f"✅ Event created successfully!\n"
                f"**{summary}**\n"
                f"Start: {start_time}\n"
                f"End: {end_time}\n"
                f"Link: {created_event.get('htmlLink', 'N/A')}"
            )
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return f"Error creating calendar event: {str(e)}"

    @tool
    async def search_calendar_events(query: str, max_results: int = 10) -> str:
        """
        Search for calendar events by keyword.
        Args:
            query: Search keyword (e.g., 'meeting', 'standup', 'lunch')
            max_results: Maximum number of results (default 10)
        """
        service = await _get_calendar_service(user_id)
        if not service:
            return "Google Calendar is not connected. Please connect it in Settings."

        try:
            now = datetime.now(timezone.utc).isoformat()

            events_result = service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime',
                q=query
            ).execute()

            events = events_result.get('items', [])

            if not events:
                return f"No events found matching '{query}'."

            output = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                summary = event.get('summary', '(No title)')
                output.append(f"📅 **{summary}** — {start}")

            return f"Found {len(events)} event(s) matching '{query}':\n\n" + "\n".join(output)
        except Exception as e:
            logger.error(f"Error searching calendar events: {e}")
            return f"Error searching calendar events: {str(e)}"

    return [list_calendar_events, create_calendar_event, search_calendar_events]
