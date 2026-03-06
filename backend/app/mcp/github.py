"""
GitHub MCP limb — SYNCHRONOUS subprocess approach for Windows compatibility.
Uses subprocess.Popen + JSON-RPC protocol directly to bypass async MCP SDK issues.
Requires: GITHUB_PERSONAL_ACCESS_TOKEN (stored in Supabase).
Requires: Node.js/npx on PATH.
"""
import json
import logging
import os
import subprocess
import sys
import time
import requests
from concurrent.futures import ThreadPoolExecutor

from app.db.supabase import get_connection_credentials

logger = logging.getLogger(__name__)

GITHUB_LIMB_ID = "github"
GITHUB_LIMB_NAME = "GitHub"
_CACHE_TTL_SEC = 30
_cached: dict | None = None
_cached_at: float = 0

# Thread pool for running sync subprocess in async context
_executor = ThreadPoolExecutor(max_workers=2)


async def _get_github_token(user_id: str | None = None) -> str | None:
    """
    Get GitHub PAT from Supabase for the given user.
    If no user_id, returns None (strict mode).
    """
    if not user_id:
        return None
    
    creds = await get_connection_credentials(user_id, GITHUB_LIMB_ID)
    if not creds:
        return None
        
    return creds.get("token")


def _disconnected_limb() -> dict:
    return {
        "id": GITHUB_LIMB_ID,
        "name": GITHUB_LIMB_NAME,
        "status": "disconnected",
        "tools_count": 0,
    }


def _call_github_mcp_sync(method: str, params: dict | None = None, token: str | None = None, timeout: int = 60) -> dict | str:
    """
    Call GitHub MCP server synchronously via subprocess.
    Uses communicate() for reliability on Windows.
    """
    if not token:
        return "GitHub not configured (active connection required)."
    
    env = os.environ.copy()
    env["GITHUB_PERSONAL_ACCESS_TOKEN"] = token
    env["PYTHONUNBUFFERED"] = "1"
    env["NODE_NO_WARNINGS"] = "1"
    
    # Build command for Windows vs Unix
    if sys.platform == "win32":
        cmd = ["cmd.exe", "/c", "npx", "-y", "@modelcontextprotocol/server-github"]
    else:
        cmd = ["npx", "-y", "@modelcontextprotocol/server-github"]
    
    # Build the full request sequence as input
    init_request = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "nexus-agent", "version": "1.0.0"}
        }
    })
    
    main_request = json.dumps({
        "jsonrpc": "2.0",
        "id": 2,
        "method": method,
        "params": params or {}
    })
    
    # Combine requests (one per line)
    full_input = init_request + "\n" + main_request + "\n"
    
    logger.debug(f"[MCP DEBUG] Starting GitHub subprocess for method: {method}")
    
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        
        stdout, stderr = proc.communicate(input=full_input.encode(), timeout=timeout)
        
        stdout_str = stdout.decode("utf-8", errors="replace")
        stderr_str = stderr.decode("utf-8", errors="replace")
        
        logger.debug(f"[MCP DEBUG] stdout length: {len(stdout_str)}, stderr length: {len(stderr_str)}")
        
        # Parse JSON-RPC responses (look for the second response with id=2)
        lines = [l.strip() for l in stdout_str.split("\n") if l.strip()]
        logger.debug(f"[MCP DEBUG] Got {len(lines)} response lines")
        
        for line in lines:
            try:
                resp = json.loads(line)
                if resp.get("id") == 2:
                    logger.debug(f"[MCP DEBUG] Found response for id=2")
                    if "error" in resp:
                        return f"Error: {resp['error'].get('message', resp['error'])}"
                    return resp.get("result", {})
            except json.JSONDecodeError:
                continue
        
        # No valid response found
        if stderr_str:
            return f"MCP Error: {stderr_str[:200]}"
        return "No valid MCP response received."
        
    except subprocess.TimeoutExpired:
        proc.kill()
        return f"GitHub MCP timeout ({timeout}s)"
    except Exception as e:
        logger.error(f"[MCP ERROR] {e}")
        return f"GitHub MCP error: {str(e)}"


async def get_github_limb_status(user_id: str | None = None) -> dict:
    """Get GitHub limb status."""
    global _cached, _cached_at
    
    # We can cache based on user_id if needed, but for now simple global cache 
    # might be issue if multiple users. But this is local dev for now.
    # Actually, status depends on user's token. 
    # Check if we have a token first.
    
    token = await _get_github_token(user_id)
    if not token:
        return _disconnected_limb()
    
    # If we have token, we can try to connect. 
    # Use cache to avoid spawning process every poll (10s)
    now = time.monotonic()
    if _cached is not None and (now - _cached_at) < _CACHE_TTL_SEC:
        return _cached

    import asyncio
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        _executor, 
        lambda: _call_github_mcp_sync("tools/list", token=token)
    )
    
    if isinstance(result, str):  # Error message
        logger.warning(f"GitHub MCP failed: {result}")
        return _disconnected_limb()
    
    tools = result.get("tools", [])
    limb = {
        "id": GITHUB_LIMB_ID,
        "name": GITHUB_LIMB_NAME,
        "status": "active",
        "tools_count": len(tools),
    }
    
    _cached = limb
    _cached_at = time.monotonic()
    
    return limb


async def call_github_tool(tool_name: str, arguments: dict, user_id: str | None = None) -> str:
    """Call a specific GitHub MCP tool."""
    token = await _get_github_token(user_id)
    if not token:
        return "GitHub not configured. Please add your Personal Access Token in Settings."

    import asyncio
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        _executor, 
        lambda: _call_github_mcp_sync("tools/call", {
            "name": tool_name,
            "arguments": arguments
        }, token=token)
    )
    
    if isinstance(result, str):
        return result
    
    # Extract text content from result
    content = result.get("content", [])
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(item.get("text", ""))
        if texts:
            return "\n".join(texts)
    
    return json.dumps(result, indent=2)


async def get_github_tool_list(user_id: str | None = None) -> list[dict]:
    """Get list of GitHub MCP tools for agent prompt."""
    token = await _get_github_token(user_id)
    if not token:
        return []

    import asyncio
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        _executor, 
        lambda: _call_github_mcp_sync("tools/list", token=token)
    )
    
    if isinstance(result, str):
        return []
    
    return result.get("tools", [])


async def get_github_user(user_id: str | None = None) -> str:
    """
    Get the authenticated GitHub username.
    Useful for 'list my repos' queries since MCP search_repositories requires a username.
    """
    token = await _get_github_token(user_id)
    if not token:
        return "GitHub not connected"

    try:
        response = requests.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json"
            },
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("login", "unknown")
        else:
            return f"Error fetching user: {response.status_code}"
    except Exception as e:
        return f"Error fetching user: {str(e)}"
