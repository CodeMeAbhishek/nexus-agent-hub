"""
Slack MCP limb — Persistent subprocess approach for low latency.
Keeps a single MCP server process alive per-token and reuses it across calls.
Falls back to one-shot subprocess if the persistent process dies.
Requires: SLACK_BOT_TOKEN in env (xoxb-*** from Slack App settings).
Requires: Node.js/npx on PATH.
"""
import json
import logging
import os
import subprocess
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

SLACK_LIMB_ID = "slack"
SLACK_LIMB_NAME = "Slack"
_CACHE_TTL_SEC = 30
_cached: dict | None = None
_cached_at: float = 0

# Thread pool for running sync subprocess in async context
_executor = ThreadPoolExecutor(max_workers=4)

# ── Persistent process pool ──────────────────────────────────────────────────
_process_pool: dict[str, subprocess.Popen] = {}
_process_lock = threading.Lock()
_msg_id_counter = 100
_msg_id_lock = threading.Lock()


def _next_msg_id() -> int:
    global _msg_id_counter
    with _msg_id_lock:
        _msg_id_counter += 1
        return _msg_id_counter


def _build_cmd():
    if sys.platform == "win32":
        return ["cmd.exe", "/c", "npx", "-y", "@modelcontextprotocol/server-slack"]
    return ["npx", "-y", "@modelcontextprotocol/server-slack"]


def _start_process(token: str, team_id: str | None = None) -> subprocess.Popen:
    env = os.environ.copy()
    # Subprocess env values must be strings (Windows enforces this)
    if token is not None:
        env["SLACK_BOT_TOKEN"] = str(token)
    if team_id is not None and team_id != "":
        env["SLACK_TEAM_ID"] = str(team_id)
    env["PYTHONUNBUFFERED"] = "1"
    env["NODE_NO_WARNINGS"] = "1"

    proc = subprocess.Popen(
        _build_cmd(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        bufsize=1,
    )

    init_req = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "nexus-agent", "version": "1.0.0"}
        }
    }) + "\n"
    init_notif = json.dumps({
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }) + "\n"

    proc.stdin.write(init_req)
    proc.stdin.write(init_notif)
    proc.stdin.flush()

    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        line = proc.stdout.readline()
        if not line:
            break
        try:
            msg = json.loads(line)
            if msg.get("id") == 1:
                break
        except json.JSONDecodeError:
            continue

    logger.info("[MCP] Persistent Slack process started (pid=%s)", proc.pid)
    return proc


def _get_process(token: str, team_id: str | None = None) -> subprocess.Popen:
    pool_key = f"{token}:{team_id or ''}"
    with _process_lock:
        proc = _process_pool.get(pool_key)
        if proc is None or proc.poll() is not None:
            if proc is not None:
                logger.warning("[MCP] Slack process died, restarting...")
                try: proc.kill()
                except Exception: pass
            proc = _start_process(token, team_id)
            _process_pool[pool_key] = proc
        return proc


def _call_slack_persistent(method: str, params: dict | None, token: str, team_id: str | None = None, timeout: int = 30) -> dict | str:
    msg_id = _next_msg_id()
    request = json.dumps({
        "jsonrpc": "2.0",
        "id": msg_id,
        "method": method,
        "params": params or {}
    }) + "\n"

    pool_key = f"{token}:{team_id or ''}"
    
    try:
        proc = _get_process(token, team_id)
        proc.stdin.write(request)
        proc.stdin.flush()

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            line = proc.stdout.readline()
            if not line:
                raise RuntimeError("Slack MCP process closed stdout unexpectedly")
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                if msg.get("id") == msg_id:
                    if "error" in msg:
                        err = msg["error"]
                        return f"MCP error: {err.get('message', str(err)) if isinstance(err, dict) else err}"
                    return msg.get("result", msg)
            except json.JSONDecodeError:
                continue

        return f"MCP persistent call timed out after {timeout}s"

    except Exception as e:
        logger.warning("[MCP] Persistent call failed (%s), falling back to one-shot: %s", method, e)
        with _process_lock:
            _process_pool.pop(pool_key, None)
        return _call_slack_mcp_sync(method, params, token=token, team_id=team_id, timeout=60)


# ── Graceful cleanup on shutdown ──────────────────────────────────────────────
import atexit

def _cleanup_slack_processes():
    """Kill all persistent Slack MCP processes on server shutdown."""
    with _process_lock:
        for key, proc in list(_process_pool.items()):
            try:
                proc.kill()
                logger.info("[MCP] Killed Slack process pid=%s on shutdown", proc.pid)
            except Exception:
                pass
        _process_pool.clear()

atexit.register(_cleanup_slack_processes)


# ── Legacy one-shot fallback ──────────────────────────────────────────────────


def _get_slack_token() -> str | None:
    # STRICT MODE: No environment variable fallback.
    # Connections must be explicitly provided via user_id -> Supabase.
    return None


def _disconnected_limb() -> dict:
    return {
        "id": SLACK_LIMB_ID,
        "name": SLACK_LIMB_NAME,
        "status": "disconnected",
        "tools_count": 0,
    }


def get_slack_limb_status_cached() -> dict:
    """Return current Slack limb from cache (never blocks)."""
    global _cached, _cached_at
    now = time.monotonic()
    if _cached is not None and (now - _cached_at) < _CACHE_TTL_SEC:
        return _cached
    return _disconnected_limb()


def _call_slack_mcp_sync(method: str, params: dict | None = None, token: str | None = None, team_id: str | None = None, timeout: int = 60) -> dict | str:
    """
    Call Slack MCP server synchronously via subprocess.
    Uses communicate() for reliability on Windows.
    """
    # Use provided token or fallback to env
    api_token = token or _get_slack_token()
    
    if not api_token:
        return "Slack not configured (active connection required)."
    
    env = os.environ.copy()
    env["SLACK_BOT_TOKEN"] = api_token
    if team_id:
        env["SLACK_TEAM_ID"] = team_id
    env["PYTHONUNBUFFERED"] = "1"
    env["NODE_NO_WARNINGS"] = "1"
    
    # Build command for Windows vs Unix
    # Using the Model Context Protocol slack server package
    if sys.platform == "win32":
        cmd = ["cmd.exe", "/c", "npx", "-y", "@modelcontextprotocol/server-slack"]
    else:
        cmd = ["npx", "-y", "@modelcontextprotocol/server-slack"]
    
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
    
    logger.debug(f"[MCP DEBUG] Starting subprocess for method: {method}")
    
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
        return f"Slack MCP timeout ({timeout}s)"
    except Exception as e:
        logger.error(f"[MCP ERROR] {e}")
        return f"Slack MCP error: {str(e)}"


def get_slack_limb_status() -> dict:
    """Get Slack limb status by calling tools/list."""
    global _cached, _cached_at
    
    token = _get_slack_token()
    if not token:
        return _disconnected_limb()
    
    result = _call_slack_persistent("tools/list", None, token=token)
    
    if isinstance(result, str):  # Error message
        logger.warning(f"Slack MCP failed: {result}")
        return _disconnected_limb()
    
    tools = result.get("tools", [])
    limb = {
        "id": SLACK_LIMB_ID,
        "name": SLACK_LIMB_NAME,
        "status": "active",
        "tools_count": len(tools),
    }
    
    _cached = limb
    _cached_at = time.monotonic()
    
    return limb


def get_slack_tool_list(token: str | None = None, team_id: str | None = None) -> list[dict]:
    """Get list of Slack MCP tools for agent prompt."""
    if not token:
        return []
    result = _call_slack_persistent("tools/list", None, token=token, team_id=team_id)
    
    if isinstance(result, str):
        return []
    
    return result.get("tools", [])


def call_slack_tool(tool_name: str, arguments: dict, token: str | None = None, team_id: str | None = None) -> str:
    """Call a specific Slack MCP tool."""
    logger.info("Calling Slack tool: %s with args: %s", tool_name, arguments)
    result = _call_slack_persistent("tools/call", {
        "name": tool_name,
        "arguments": arguments
    }, token=token, team_id=team_id)
    
    if isinstance(result, str):
        logger.warning("Slack tool returned error: %s", result)
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


async def async_get_slack_limb_status() -> dict:
    """Async wrapper for get_slack_limb_status."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, get_slack_limb_status)


async def async_get_slack_tool_list(token: str | None = None, team_id: str | None = None) -> list[dict]:
    """Async wrapper for get_slack_tool_list."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, get_slack_tool_list, token, team_id)


async def async_call_slack_tool(tool_name: str, arguments: dict, token: str | None = None, team_id: str | None = None) -> str:
    """Async wrapper for call_slack_tool."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, call_slack_tool, tool_name, arguments, token, team_id)

