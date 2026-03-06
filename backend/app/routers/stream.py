"""
SSE (Server-Sent Events) streaming endpoint for real-time agent reasoning traces.
Streams agent "thoughts", tool calls, and results to the frontend ReasoningTrace panel.
"""
import asyncio
import json
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from datetime import datetime

from app.agent.graph import run_agent_streaming
from app.auth.routes import get_current_user
from app.db.supabase import get_service_client

router = APIRouter()


class StreamRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


async def event_generator(query: str, user_id: str | None = None, session_id: str | None = None) -> AsyncGenerator[str, None]:
    """
    Generate SSE events from the agent's execution.
    
    SSE format:
    data: {"type": "info", "message": "..."}
    
    """
    accumulated_response = ""
    
    try:
        # Fetch chat history if session_id is provided
        chat_history = []
        if session_id and user_id:
            client = get_service_client()
            if client:
                try:
                    # Fetch last 10 messages for context
                    response = (
                        client.table("chat_messages")
                        .select("*")
                        .eq("session_id", session_id)
                        .order("created_at", desc=True)
                        .limit(10)
                        .execute()
                    )
                    db_messages = response.data[::-1] if response.data else []
                    
                    from langchain_core.messages import HumanMessage, AIMessage
                    for msg in db_messages:
                        if msg["role"] == "user":
                            chat_history.append(HumanMessage(content=msg["content"]))
                        elif msg["role"] == "assistant" or msg["role"] == "agent":
                            chat_history.append(AIMessage(content=msg["content"]))
                except Exception as e:
                    print(f"Failed to fetch history for stream: {e}")

        async for event in run_agent_streaming(query, user_id=user_id, chat_history=chat_history):
            # Capture response for saving
            if event.get("type") == "response":
                accumulated_response = event.get("message", "")

            # Format as SSE
            data = json.dumps(event)
            yield f"data: {data}\n\n"
            
    except Exception as e:
        error_event = json.dumps({
            "type": "error",
            "message": f"Agent error: {str(e)}"
        })
        yield f"data: {error_event}\n\n"
    finally:
        # Save Assistant Response if session_id exists
        # Use asyncio.to_thread to avoid blocking the event loop
        if session_id and user_id and accumulated_response:
            try:
                def _save_response():
                    client = get_service_client()
                    if client:
                        client.table("chat_messages").insert({
                            "session_id": session_id,
                            "role": "assistant",
                            "content": accumulated_response,
                            "created_at": datetime.utcnow().isoformat()
                        }).execute()
                        client.table("chat_sessions").update({
                            "updated_at": datetime.utcnow().isoformat()
                        }).eq("id", session_id).execute()
                await asyncio.to_thread(_save_response)
            except Exception as e:
                print(f"Failed to save assistant response: {e}")

        # Send completion event
        done_event = json.dumps({
            "type": "done",
            "message": "Agent execution complete"
        })
        yield f"data: {done_event}\n\n"


@router.post("/chat/stream")
async def stream_chat(request: StreamRequest, user: dict | None = Depends(get_current_user)):
    """
    SSE streaming endpoint for agent execution.
    
    Returns a stream of events:
    - type: "info" - General status updates
    - type: "action" - Tool calls being executed
    - type: "result" - Tool results
    - type: "response" - Final agent response
    - type: "done" - Execution complete
    - type: "error" - Error occurred
    """
    q = (request.query or "").strip()
    if not q:
        return StreamingResponse(
            iter([f'data: {json.dumps({"type": "error", "message": "Empty query"})}\n\n']),
            media_type="text/event-stream"
        )
    
    user_id = user["id"] if user else None
    
    # Save User Message in background thread to avoid blocking
    if request.session_id and user_id:
        try:
            def _save_user_msg():
                client = get_service_client()
                if client:
                    client.table("chat_messages").insert({
                        "session_id": request.session_id,
                        "role": "user",
                        "content": q,
                        "created_at": datetime.utcnow().isoformat()
                    }).execute()
            await asyncio.to_thread(_save_user_msg)
        except Exception as e:
            import logging
            logging.getLogger("app.routers.stream").error(f"Failed to save user message: {e}")

    return StreamingResponse(
        event_generator(q, user_id=user_id, session_id=request.session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
