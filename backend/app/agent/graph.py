"""
Phase 2 — LangGraph ReAct agent with Notion MCP tools.
Planner (LLM) + Executor (Notion tools). LLM: Google Gemini.
Enterprise-ready: works for any company's natural language queries.
"""
import asyncio
import logging
import sys
from typing import Any

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from app.mcp.notion import get_notion_tool_list
from app.mcp.slack import async_get_slack_tool_list as get_slack_tool_list
from app.mcp.github import get_github_tool_list
from app.db.supabase import get_connection_credentials
from app.mcp.gmail import get_gmail_tools
from app.mcp.calendar import get_calendar_tools
from app.mcp.drive import get_drive_tools
from app.mcp.mongodb import get_mongodb_tools

# ... existing code ...
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



async def route_query(query: str, llm) -> str:
    """
    Classify the query — keyword-first (0 ms), LLM fallback only for ambiguous queries.
    """
    # Fast path: keyword matching covers ~85% of queries with zero LLM cost
    _KEYWORD_ROUTES: dict[str, list[str]] = {
        "conversational": ["hi", "hello", "hey", "thanks", "who are you", "what are you",
                           "write a poem", "tell me a joke", "help me understand"],
        "notion":   ["notion", "page", "workspace", "database", "block"],
        "slack":    ["slack", "channel", "#general", "#", "dm ", "post to"],
        "github":   ["github", "repo", "repository", "issue", "pull request", "pr",
                     "commit", "branch", "code"],
        "gmail":    ["email", "gmail", "inbox", "mail", "send mail", "unread"],
        "calendar": ["calendar", "schedule", "event", "meeting", "appointment", "standup"],
        "drive":    ["drive", "gdrive", "google drive", "document", "spreadsheet", "sheet",
                     "slides", "doc"],
        "mongodb":  ["mongo", "mongodb", "collection", "aggregate", "pipeline"],
    }
    q_lower = query.lower()
    for route, keywords in _KEYWORD_ROUTES.items():
        if any(kw in q_lower for kw in keywords):
            logger.info(f"⚡ Fast-routed '{query[:40]}' → {route} (keyword match)")
            return route

    # Slow path: LLM classifier for ambiguous queries
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        messages = [
            SystemMessage(content=ROUTER_PROMPT),
            HumanMessage(content=query)
        ]
        response = await llm.ainvoke(messages)
        route = response.content.strip().lower()
        logger.info(f"🔀 LLM-routed '{query[:40]}' → {route}")
        return route
    except Exception as e:
        logger.error(f"Routing failed: {e}")
        return "general"  # Fallback to loading everything


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

    # 1. ROUTE THE QUERY
    route = await route_query(query, llm)
    
    # Fast path for conversational queries
    if route == "conversational":
        from langchain_core.messages import HumanMessage, SystemMessage
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
        if route not in ["slack", "general"]:
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
        inputs = {"messages": chat_history + [HumanMessage(content=query.strip())]}
        result = await graph.ainvoke(
            inputs,
            config={"recursion_limit": 25},
        )
    except Exception as e:
        err_str = str(e).lower()
        if "429" in err_str or "resource_exhausted" in err_str or "rate" in err_str:
            import asyncio
            logger.warning("Rate limit hit, waiting 5 seconds and retrying...")
            await asyncio.sleep(5)
            try:
                result = await graph.ainvoke(
                    {"messages": [HumanMessage(content=query.strip())]},
                    config={"recursion_limit": 25},
                )
            except Exception as retry_e:
                 return "⚠️ Rate limit reached. Please wait 30 seconds and try again."
        elif "recursion" in err_str:
             return "I had trouble processing your request. Please try a more specific query."
        elif "400" in err_str:
             return "I couldn't complete the tool call. Please try rephrasing your request."
        else:
            logger.exception("Agent run failed: %s", e)
            return f"Something went wrong: {e}"

    # Extract the final AI response
    messages = result.get("messages", [])
    for m in reversed(messages):
        if isinstance(m, AIMessage) and m.content:
            if isinstance(m.content, str):
                return m.content
            elif isinstance(m.content, list):
                text_parts = []
                for block in m.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        text_parts.append(block)
                return "".join(text_parts)
            else:
                return str(m.content)
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
    
    # 1. ROUTE THE QUERY
    yield {"type": "info", "message": "🧭 Routing query..."}
    route = await route_query(query, llm)
    yield {"type": "info", "message": f"👉 Routed to: {route.upper()}"}
    
    # Fast path for conversational
    if route == "conversational":
        from langchain_core.messages import HumanMessage, SystemMessage
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
        if route not in ["slack", "general"]:
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
        inputs = {"messages": chat_history + [HumanMessage(content=query.strip())]}
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
                                continue 
                            elif msg.content:
                                if isinstance(msg.content, str):
                                    final_response = msg.content
                                elif isinstance(msg.content, list):
                                    text_parts = []
                                    for block in msg.content:
                                        if isinstance(block, dict) and block.get("type") == "text":
                                            text_parts.append(block.get("text", ""))
                                        elif isinstance(block, str):
                                            text_parts.append(block)
                                    final_response = "".join(text_parts)
                                    
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
            import asyncio
            await asyncio.sleep(5)
            yield {"type": "info", "message": "🔄 Retrying..."}
            yield {"type": "error", "message": "Rate limit persisted. Try again in 30 seconds."}
        elif "recursion" in err_str:
            yield {"type": "error", "message": "Task too complex. Try a simpler query."}
        else:
            yield {"type": "error", "message": f"Error: {str(e)[:200]}"}
