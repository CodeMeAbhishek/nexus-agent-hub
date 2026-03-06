"""
Chat / query endpoint — Phase 2 runs LangGraph agent (Planner + Notion tools).
"""
import asyncio
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.agent.graph import run_agent
from app.auth.routes import get_current_user
from typing import Optional
from app.db.supabase import get_supabase_client
from app.utils.response import standard_response, error_response

router = APIRouter()


from langchain_core.messages import HumanMessage, AIMessage

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


@router.post("/chat")
async def chat(request: ChatRequest, user: dict | None = Depends(get_current_user)):
    """
    Run the ReAct agent on the user query. Agent uses Notion MCP tools when available.
    Requires OPENAI_API_KEY (or configured LLM key) in env.
    User context is used to load private connection credentials.
    """
    q = (request.query or "").strip()
    user_id = user["id"] if user else None
    
    # 1. Fetch Chat History if session_id is provided
    chat_history = []
    if request.session_id and user_id:
        try:
            def _fetch_history():
                client = get_supabase_client()
                if not client:
                    return []
                response = (
                    client.table("chat_messages")
                    .select("*")
                    .eq("session_id", request.session_id)
                    .order("created_at", desc=True)
                    .limit(10)
                    .execute()
                )
                return response.data[::-1] if response.data else []
            db_messages = await asyncio.to_thread(_fetch_history)
            for msg in db_messages:
                if msg["role"] == "user":
                    chat_history.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant" or msg["role"] == "agent":
                    chat_history.append(AIMessage(content=msg["content"]))
        except Exception as e:
            print(f"Failed to fetch history: {e}")

    # 2. Run Agent
    response_text = await run_agent(q, user_id=user_id, chat_history=chat_history)
    
    # 3. Save History in background thread to avoid blocking
    if request.session_id and user_id:
        try:
            def _save_history():
                client = get_supabase_client()
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
