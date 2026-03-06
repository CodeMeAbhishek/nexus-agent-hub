"""
Shared chat history loading — single place for Supabase chat_messages -> LangChain messages.
Used by chat and stream routers to avoid duplication.
"""
from __future__ import annotations

import asyncio
import logging
from typing import List, Any

from langchain_core.messages import HumanMessage, AIMessage

from app.db.supabase import get_service_client

logger = logging.getLogger(__name__)

DEFAULT_HISTORY_LIMIT = 10


def _fetch_history_sync(session_id: str, limit: int) -> List[dict]:
    """Sync fetch; run in thread from async."""
    client = get_service_client()
    if not client:
        return []
    response = (
        client.table("chat_messages")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return (response.data or [])[::-1]


async def fetch_chat_history(
    session_id: str,
    user_id: str | None = None,
    limit: int = DEFAULT_HISTORY_LIMIT,
) -> List[Any]:
    """
    Load last N messages for a session and return as LangChain message list.
    Returns [] if no session_id, no client, or on error.
    """
    if not session_id:
        return []
    try:
        rows = await asyncio.to_thread(_fetch_history_sync, session_id, limit)
        messages = []
        for msg in rows:
            role = (msg.get("role") or "").lower()
            content = msg.get("content") or ""
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role in ("assistant", "agent"):
                messages.append(AIMessage(content=content))
        return messages
    except Exception as e:
        logger.warning("Failed to fetch chat history for session %s: %s", session_id, e)
        return []
