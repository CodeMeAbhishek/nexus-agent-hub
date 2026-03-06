"""
Phase 2 — LangGraph ReAct agent with Notion MCP tools.
Planner (LLM) + Executor (Notion tools). LLM: Google Gemini.
Enterprise-ready: works for any company's natural language queries.
"""
import asyncio
import logging
import sys
from typing import Any

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from app.core.limbs import get_all_limb_keywords, get_keyword_routes
from app.db.supabase import get_connection_credentials
from app.mcp.calendar import get_calendar_tools
from app.mcp.drive import get_drive_tools
from app.mcp.gmail import get_gmail_tools
from app.mcp.github import get_github_tool_list
from app.mcp.mongodb import get_mongodb_tools
from app.mcp.notion import get_notion_tool_list
from app.mcp.slack import async_get_slack_tool_list as get_slack_tool_list

from .prompts import SYSTEM_PROMPT, ROUTER_PROMPT
from .llm import get_llm
from .tools import (
    build_notion_tool,
    build_slack_tool,
    build_github_tool,
    build_write_tools
)

# Configure logging for debugging
logger = logging.getLogger(__name__)

# ── Graph factory ────────────────────────────────────────────────────────────
# Wraps create_react_agent with clean error handling.
# NOTE: We cannot cache compiled graphs across requests because tools
# contain user-specific tokens and differ per request.

def _get_or_build_graph(route: str, tools: list, llm) -> Any:
    """
    Build a compiled LangGraph agent for the given route.
    Tools change per-request (user-specific tokens), so we always rebuild.
    """
    logger.info(f"Building agent graph for route={route} with {len(tools)} tool(s)")
    return create_react_agent(llm, tools=tools, prompt=SYSTEM_PROMPT)



# Short user replies that usually mean "continue with what you just offered"
_SHORT_AFFIRMATIVES = frozenset({
    "yes", "yeah", "yep", "sure", "ok", "okay", "please", "do it", "get it",
    "continue", "go ahead", "confirm", "confirmed", "yup", "absolutely",
    "send it", "send it again", "resend", "try again",
})


def _build_agent_messages(chat_history: list, query: str) -> list:
    """
    Build the message list for the agent. When the user sends a short affirmative
    (e.g. "yes") after an assistant message, append a nudge so the agent actually
    calls the relevant tool instead of replying with text-only confirmation.
    Chat history from DB has no tool_calls/tool_results, so the model may otherwise
    assume the action was already done and just reply "I've sent it" without calling.
    """
    q = query.strip()
    if not q:
        return list(chat_history)
    last_content = q
    q_lower = q.lower()
    nudge = "\n\n(Perform the requested action now by calling the appropriate tool in this turn.)"

    # Nudge when user confirms after assistant (e.g. "yes", "do it")
    if chat_history:
        last = chat_history[-1]
        is_ai = type(last).__name__ == "AIMessage"
        is_affirmative = q_lower in _SHORT_AFFIRMATIVES or (
            len(q_lower) <= 25 and any(w in q_lower for w in ("send", "do it", "yes", "please", "sure"))
        )
        if is_ai and is_affirmative:
            last_content = q + nudge
            logger.info("Nudging agent to use tool after user confirmation")
            return list(chat_history) + [HumanMessage(content=last_content)]

    # Nudge when user explicitly asks to add/create a calendar event (so agent actually calls the tool)
    if any(phrase in q_lower for phrase in (
        "add", "create", "schedule", "put "
    )) and any(word in q_lower for word in ("calendar", "meeting", "event", "google calendar")):
        last_content = q + nudge
        logger.info("Nudging agent to use tool for calendar/create request")
    return list(chat_history) + [HumanMessage(content=last_content)]


# Patterns that indicate the content is internal reasoning/code, not a user-facing reply
_INTERNAL_PATTERNS = (
    "tool_name=",
    "arguments=",
    "call_notion",
    "call_slack",
    "print(",
    "api-post-search",
    "first, i will",
    "i need to search",
    "i will search",
    "i will call",
)


def _is_user_facing_content(text: str) -> bool:
    """True if the text looks like a final user-facing reply, not internal plan/code."""
    if not text or len(text.strip()) < 10:
        return False
    lower = text.lower()
    for p in _INTERNAL_PATTERNS:
        if p in lower:
            return False
    return True


def _extract_text_from_ai_message(m) -> str | None:
    """Get plain text from an AIMessage, or None if empty."""
    if not m.content:
        return None
    if isinstance(m.content, str):
        return m.content
    if isinstance(m.content, list):
        parts = []
        for block in m.content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts) if parts else None
    return str(m.content)


async def route_query(query: str, llm, chat_history: list | None = None) -> str:
    """
    Route to either 'conversational' (no tools) or 'general' (all tools).
    User can use any query; the agent gets all connected tools and picks what it needs.
    """
    chat_history = chat_history or []
    q_lower = query.strip().lower()

    # Context-aware: short affirmative after assistant follow-up → keep tools (general)
    if q_lower in _SHORT_AFFIRMATIVES and chat_history:
        last = chat_history[-1]
        is_ai = getattr(last, "type", None) == "ai" or last.__class__.__name__ == "AIMessage"
        if is_ai:
            raw = getattr(last, "content", None) or ""
            if isinstance(raw, list):
                text = " ".join(
                    (b.get("text") or "") for b in raw if isinstance(b, dict)
                ).lower()
            else:
                text = str(raw).lower()
            if "would you like" in text or "channel" in text or "?" in text or len(text) > 60:
                logger.info(f"⚡ Context-routed '{query[:40]}' → general (affirmative after assistant)")
                return "general"

    # Dynamic routing: default to general (all tools). Only use conversational for pure chat.
    limb_keywords = get_all_limb_keywords()
    conversational_keywords = get_keyword_routes().get("conversational", [])

    if any(kw in q_lower for kw in limb_keywords):
        logger.info(f"⚡ Routed '{query[:40]}' → general (tool intent detected)")
        return "general"
    if any(kw in q_lower for kw in conversational_keywords):
        logger.info(f"⚡ Routed '{query[:40]}' → conversational (pure chat)")
        return "conversational"
    # Unknown or ambiguous query → give agent all tools so it can choose
    logger.info(f"⚡ Routed '{query[:40]}' → general (default, all tools)")
    return "general"


async def run_agent(query: str, user_id: str | None = None, chat_history: list = []) -> str:
    """
    Run the ReAct agent on the user query.
    """
    if not query or not query.strip():
        return "Please enter a query."

    try:
        llm = get_llm()
    except ValueError as e:
        return f"Agent not configured: {e}"

    # 1. ROUTE THE QUERY (pass chat_history so "Yes" after assistant follow-up stays tool-aware)
    route = await route_query(query, llm, chat_history=chat_history)
    
    # Fast path for conversational queries
    if route == "conversational":
        # Simple chat interaction without tools
        messages = [
            SystemMessage(content="You are a helpful AI assistant. Answer the user's question directly."),
            HumanMessage(content=query)
        ]
        response = await llm.ainvoke(messages)
        return response.content

    tools = []
    
    # Load credentials in parallel (not sequentially)
    notion_token = None
    slack_token = None
    slack_team_id = None

    if user_id:
        notion_creds, slack_creds = await asyncio.gather(
            get_connection_credentials(user_id, "notion"),
            get_connection_credentials(user_id, "slack"),
            return_exceptions=True
        )
        if isinstance(notion_creds, dict):
            notion_token = notion_creds.get("token")
        if isinstance(slack_creds, dict):
            slack_token = slack_creds.get("token")
            slack_team_id = slack_creds.get("team_id")

    tools = []
    
    # 2. DYNAMIC TOOL LOADING — parallel gather for all applicable tools
    async def _load_notion():
        if route not in ["notion", "general"]:
            return []
        tool_list = await get_notion_tool_list(token=notion_token)
        result = []
        if tool_list:   
            result.append(build_notion_tool(tool_list, token=notion_token))
        result.extend(build_write_tools(token=notion_token))    
        return result

    async def _load_slack():
        if route not in ["slack", "general"] or not slack_token:
            return []
        slack_tool_list = await get_slack_tool_list(token=slack_token, team_id=slack_team_id)
        if slack_tool_list:
            return [build_slack_tool(slack_tool_list, token=slack_token, team_id=slack_team_id)]
        return []

    async def _load_github():
        if route not in ["github", "general"] or not user_id:
            return []
        github_tool_list = await get_github_tool_list(user_id=user_id)
        if github_tool_list:
            return [build_github_tool(github_tool_list, user_id=user_id)]
        return []

    async def _load_gmail():
        if route not in ["gmail", "general"] or not user_id:
            return []
        try:
            gmail_tools = get_gmail_tools(user_id)
            return gmail_tools if gmail_tools else []
        except Exception as e:
            logger.error(f"Failed to load Gmail tools: {e}")
            return []

    async def _load_calendar():
        if route not in ["calendar", "general"] or not user_id:
            return []
        try:
            calendar_tools = get_calendar_tools(user_id)
            return calendar_tools if calendar_tools else []
        except Exception as e:
            logger.error(f"Failed to load Calendar tools: {e}")
            return []

    async def _load_drive():
        if route not in ["drive", "general"] or not user_id:
            return []
        try:
            drive_tools = get_drive_tools(user_id)
            return drive_tools if drive_tools else []
        except Exception as e:
            logger.error(f"Failed to load Drive tools: {e}")
            return []

    async def _load_mongodb():
        if route not in ["mongodb", "general"] or not user_id:
            return []
        try:
            mongo_tools = get_mongodb_tools(user_id)
            return mongo_tools if mongo_tools else []
        except Exception as e:
            logger.error(f"Failed to load MongoDB tools: {e}")
            return []

    tool_groups = await asyncio.gather(
        _load_notion(), _load_slack(), _load_github(),
        _load_gmail(), _load_calendar(), _load_drive(), _load_mongodb(),
        return_exceptions=True
    )
    for group in tool_groups:
        if isinstance(group, list):
            tools.extend(group)

    try:
        graph = _get_or_build_graph(route, tools, llm)
    except Exception as e:
        logger.exception("Failed to create agent: %s", e)
        return f"Agent setup failed: {e}"

    try:
        inputs = {"messages": _build_agent_messages(chat_history, query)}
        result = await graph.ainvoke(
            inputs,
            config={"recursion_limit": 25},
        )
    except Exception as e:
        err_str = str(e).lower()
        if "429" in err_str or "resource_exhausted" in err_str or "rate" in err_str:
            logger.warning("Rate limit hit, waiting 5 seconds and retrying...")
            await asyncio.sleep(5)
            try:
                result = await graph.ainvoke(inputs, config={"recursion_limit": 25})
            except Exception as retry_e:
                 return "⚠️ Rate limit reached. Please wait 30 seconds and try again."
        elif "recursion" in err_str:
             return "I had trouble processing your request. Please try a more specific query."
        elif "400" in err_str:
             return "I couldn't complete the tool call. Please try rephrasing your request."
        else:
            logger.exception("Agent run failed: %s", e)
            return f"Something went wrong: {e}"

    # Extract the final AI response — prefer last user-facing content (skip internal plan/code)
    messages = result.get("messages", [])
    for m in reversed(messages):
        if isinstance(m, AIMessage):
            text = _extract_text_from_ai_message(m)
            if text and _is_user_facing_content(text):
                return text
    # Fallback: last AI content even if it looks internal (better than nothing)
    for m in reversed(messages):
        if isinstance(m, AIMessage):
            text = _extract_text_from_ai_message(m)
            if text:
                return text
    return "No response from agent."


async def run_agent_streaming(query: str, user_id: str | None = None, chat_history: list = []):
    """
    Streaming version of run_agent that yields events for SSE.
    """
    if not query:
        yield {"type": "error", "message": "No query provided"}
        return
    
    yield {"type": "info", "message": "🧠 Initializing Nexus agent..."}
    
    try:
        llm = get_llm()
    except ValueError as e:
        yield {"type": "error", "message": str(e)}
        return
    
    # 1. ROUTE THE QUERY (pass chat_history so "Yes" after assistant follow-up stays tool-aware)
    yield {"type": "info", "message": "🧭 Routing query..."}
    route = await route_query(query, llm, chat_history=chat_history)
    yield {"type": "info", "message": f"👉 Routed to: {route.upper()}"}
    
    # Fast path for conversational
    if route == "conversational":
        messages = [
            SystemMessage(content="You are a helpful AI assistant. Answer the user's question directly."),
            HumanMessage(content=query)
        ]
        # Yield partials if we want, but for now simple await for consistency
        response = await llm.ainvoke(messages)
        yield {"type": "response", "message": response.content}
        return

    # Load credentials in parallel
    notion_token = None
    slack_token = None
    slack_team_id = None

    if user_id:
        notion_creds, slack_creds = await asyncio.gather(
            get_connection_credentials(user_id, "notion"),
            get_connection_credentials(user_id, "slack"),
            return_exceptions=True
        )
        if isinstance(notion_creds, dict):
            notion_token = notion_creds.get("token")
        if isinstance(slack_creds, dict):
            slack_token = slack_creds.get("token")
            slack_team_id = slack_creds.get("team_id")

    tools = []
    
    # 2. DYNAMIC TOOL LOADING — parallel gather (mirrors run_agent)
    yield {"type": "info", "message": "🔌 Loading tools..."}

    async def _sload_notion():
        if route not in ["notion", "general"]:
            return []
        tool_list = await get_notion_tool_list(token=notion_token)
        result = []
        if tool_list:
            result.append(build_notion_tool(tool_list, token=notion_token))
        result.extend(build_write_tools(token=notion_token))
        return result

    async def _sload_slack():
        if route not in ["slack", "general"] or not slack_token:
            return []
        slack_tool_list = await get_slack_tool_list(token=slack_token, team_id=slack_team_id)
        if slack_tool_list:
            return [build_slack_tool(slack_tool_list, token=slack_token, team_id=slack_team_id)]
        return []

    async def _sload_github():
        if route not in ["github", "general"] or not user_id:
            return []
        github_tool_list = await get_github_tool_list(user_id=user_id)
        if github_tool_list:
            return [build_github_tool(github_tool_list, user_id=user_id)]
        return []

    async def _sload_gmail():
        if route not in ["gmail", "general"] or not user_id:
            return []
        try:
            gmail_tools = get_gmail_tools(user_id)
            return gmail_tools if gmail_tools else []
        except Exception as e:
            logger.error(f"Failed Gmail: {e}")
            return []

    async def _sload_calendar():
        if route not in ["calendar", "general"] or not user_id:
            return []
        try:
            calendar_tools = get_calendar_tools(user_id)
            return calendar_tools if calendar_tools else []
        except Exception as e:
            logger.error(f"Failed Calendar: {e}")
            return []

    async def _sload_drive():
        if route not in ["drive", "general"] or not user_id:
            return []
        try:
            drive_tools = get_drive_tools(user_id)
            return drive_tools if drive_tools else []
        except Exception as e:
            logger.error(f"Failed Drive: {e}")
            return []

    async def _sload_mongodb():
        if route not in ["mongodb", "general"] or not user_id:
            return []
        try:
            mongo_tools = get_mongodb_tools(user_id)
            return mongo_tools if mongo_tools else []
        except Exception as e:
            logger.error(f"Failed MongoDB: {e}")
            return []

    tool_groups = await asyncio.gather(
        _sload_notion(), _sload_slack(), _sload_github(),
        _sload_gmail(), _sload_calendar(), _sload_drive(), _sload_mongodb(),
        return_exceptions=True
    )
    for group in tool_groups:
        if isinstance(group, list):
            tools.extend(group)

    yield {"type": "info", "message": f"🧰 Loaded {len(tools)} tool(s) for {route.upper()}"}
    
    try:
        graph = _get_or_build_graph(route, tools, llm)
    except Exception as e:
        yield {"type": "error", "message": f"Agent setup failed: {e}"}
        return
    
    yield {"type": "info", "message": f"🚀 Processing: \"{query[:50]}{'...' if len(query) > 50 else ''}\""}
    
    final_response = None
    
    try:
        inputs = {"messages": _build_agent_messages(chat_history, query)}
        async for event in graph.astream(
            inputs,
            config={"recursion_limit": 25},
        ):
            # Process different event types
            for key, value in event.items():
                if key == "agent":
                    messages = value.get("messages", [])
                    for msg in messages:
                        if isinstance(msg, AIMessage):
                            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                for tc in msg.tool_calls:
                                    name = (
                                        tc.get("name", "tool")
                                        if isinstance(tc, dict)
                                        else getattr(tc, "name", "tool")
                                    )
                                    yield {"type": "action", "message": f"🔧 Calling: {name}"}
                                continue
                            elif msg.content:
                                text = _extract_text_from_ai_message(msg)
                                if text and _is_user_facing_content(text):
                                    final_response = text
                                    
                elif key == "tools":
                    messages = value.get("messages", [])
                    for msg in messages:
                        if isinstance(msg, ToolMessage):
                            content = str(msg.content)[:200]
                            if len(str(msg.content)) > 200:
                                content += "..."
                            yield {
                                "type": "result",
                                "message": f"✅ Action completed: {content}"
                            }
        
        if final_response:
            yield {
                "type": "response",
                "message": final_response
            }
        else:
            yield {
                "type": "response", 
                "message": "No response from agent."
            }
            
    except Exception as e:
        err_str = str(e).lower()
        if "429" in err_str or "resource_exhausted" in err_str:
            yield {"type": "error", "message": "⚠️ Rate limit hit. Waiting..."}
            await asyncio.sleep(5)
            yield {"type": "info", "message": "🔄 Retrying..."}
            yield {"type": "error", "message": "Rate limit persisted. Try again in 30 seconds."}
        elif "recursion" in err_str:
            yield {"type": "error", "message": "Task too complex. Try a simpler query."}
        else:
            yield {"type": "error", "message": f"Error: {str(e)[:200]}"}
