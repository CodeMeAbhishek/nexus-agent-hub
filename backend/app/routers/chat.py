"""
Chat / query endpoint — Phase 2 runs LangGraph agent (Planner + Notion tools).
"""
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.agent.graph import run_agent
from app.auth.routes import get_current_user
from app.db.chat_history import fetch_chat_history
from app.db.supabase import get_service_client
from app.utils.response import standard_response

router = APIRouter()


class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


@router.post("/chat")
async def chat(request: ChatRequest, user: dict | None = Depends(get_current_user)):
    """
    Run the ReAct agent on the user query. Agent uses Notion MCP tools when available.
    User context is used to load private connection credentials.
    """
    q = (request.query or "").strip()
    user_id = user["id"] if user else None

    chat_history = await fetch_chat_history(
        session_id=request.session_id or "",
        user_id=user_id,
    )

    # 2. Run Agent
    response_text = await run_agent(q, user_id=user_id, chat_history=chat_history)
    
    # 3. Save History in background thread to avoid blocking
    if request.session_id and user_id:
        try:
            def _save_history():
                client = get_service_client()
                if not client:
                    return
                # Save User Message
                client.table("chat_messages").insert({
                    "session_id": request.session_id,
                    "role": "user",
                    "content": q
                }).execute()
                # Save AI Response
                client.table("chat_messages").insert({
                    "session_id": request.session_id,
                    "role": "assistant",
                    "content": response_text
                }).execute()
                # Update Session Timestamp
                client.table("chat_sessions").update({
                    "updated_at": "now()"
                }).eq("id", request.session_id).execute()
            await asyncio.to_thread(_save_history)
        except Exception as e:
            print(f"Failed to save history: {e}")

    return standard_response(data={"response": response_text})
