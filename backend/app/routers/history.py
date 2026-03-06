"""
Router for managing chat history (sessions and messages).
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.auth.routes import require_auth
from app.db.supabase import get_supabase_client, get_service_client
from app.utils.response import standard_response, error_response

router = APIRouter()

# ============================================================================
# Models
# ============================================================================

class ChatSession(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

class CreateSessionRequest(BaseModel):
    title: str = "New Chat"

class ChatMessage(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

# ============================================================================
# Endpoints
# ============================================================================

@router.get("", response_model=None)
async def get_sessions(user: dict = Depends(require_auth)):
    """List all chat sessions for the current user."""
    # Use service client to bypass RLS issues since we filter manually
    client = get_service_client()
    if not client:
        return error_response("Database not configured", status_code=503)
    
    try:
        response = (
            client.table("chat_sessions")
            .select("*")
            .eq("user_id", user["id"])
            .order("updated_at", desc=True)
            .execute()
        )
        return standard_response(data=response.data)
    except Exception as e:
        return error_response(f"Failed to fetch sessions: {e}", status_code=500)


@router.post("", response_model=None)
async def create_session(request: CreateSessionRequest, user: dict = Depends(require_auth)):
    """Create a new chat session."""
    # Use service client to bypass RLS issues
    client = get_service_client()
    if not client:
        return error_response("Database not configured", status_code=503)
    
    try:
        data = {
            "user_id": user["id"],
            "title": request.title
        }
        response = client.table("chat_sessions").insert(data).execute()
        # With RLS and service role, we should get the data back.
        # .insert() returns a list in data. We triggered it with a single dict, so it's a list of 1.
        if response.data and len(response.data) > 0:
             return standard_response(data=response.data[0])
        else:
             # Fallback if no data returned (unlikely with service role unless error)
             return error_response("Failed to create session (no data returned)", status_code=500)
    except Exception as e:
        import logging
        logging.getLogger("app.routers.history").error(f"Create session failed: {e}", exc_info=True)
        return error_response(f"Failed to create session: {e}", status_code=500)


@router.get("/{session_id}/messages", response_model=None)
async def get_session_messages(session_id: str, user: dict = Depends(require_auth)):
    """Get all messages for a specific session."""
    client = get_service_client()
    if not client:
        return error_response("Database not configured", status_code=503)
    
    try:
        # Check ownership logic is handled by query filter or subsequent check if needed.
        # But for messages, we query strictly by session_id.
        # We should also ensure the session belongs to the user to avoid ID enumeration attacks?
        # RLS would handle this naturally. With service client, we must verify session ownership first
        # OR just rely on session_id being a UUID which is hard to guess.
        # Ideally, we join with session or check session owner.
        
        # Let's check session ownership first
        session_check = client.table("chat_sessions").select("id").eq("id", session_id).eq("user_id", user["id"]).execute()
        if not session_check.data:
            return error_response("Session not found or access denied", status_code=404)

        response = (
            client.table("chat_messages")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at", desc=False) # Oldest first for chat history
            .execute()
        )
        return standard_response(data=response.data)
    except Exception as e:
        return error_response(f"Failed to fetch messages: {e}", status_code=500)


@router.delete("/{session_id}", response_model=None)
async def delete_session(session_id: str, user: dict = Depends(require_auth)):
    """Delete a chat session."""
    client = get_service_client()
    if not client:
        return error_response("Database not configured", status_code=503)
    
    try:
        # Manual ownership check implicitly handled by delete query filter
        client.table("chat_sessions").delete().eq("id", session_id).eq("user_id", user["id"]).execute()
        return standard_response(message="Session deleted")
    except Exception as e:
        return error_response(f"Failed to delete session: {e}", status_code=500)
