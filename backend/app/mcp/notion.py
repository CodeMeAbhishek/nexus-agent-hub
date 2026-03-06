"""
Notion MCP limb — Persistent subprocess approach for low latency.
Keeps a single MCP server process alive per-token and reuses it across calls.
Falls back to one-shot subprocess if the persistent process dies.
Requires: NOTION_TOKEN in env (ntn_*** from Notion integration settings).
Requires: Node.js/npx on PATH.
"""
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty

logger = logging.getLogger(__name__)

NOTION_LIMB_ID = "notion"
NOTION_LIMB_NAME = "Notion"
_CACHE_TTL_SEC = 30
_cached: dict | None = None
_cached_at: float = 0

# Thread pool for running sync subprocess in async context
_executor = ThreadPoolExecutor(max_workers=4)

# ── Persistent process pool ──────────────────────────────────────────────────
# One persistent MCP server process per token. Eliminates cold-start cost
# (1-3 s on Windows) for every tool call.
_process_pool: dict[str, subprocess.Popen] = {}
_process_lock = threading.Lock()
_msg_id_counter = 100  # Start above 2 used during init
_msg_id_lock = threading.Lock()


def _next_msg_id() -> int:
    global _msg_id_counter
    with _msg_id_lock:
        _msg_id_counter += 1
        return _msg_id_counter


def _build_cmd():
    if sys.platform == "win32":
        return ["cmd.exe", "/c", "npx", "-y", "@notionhq/notion-mcp-server"]
    return ["npx", "-y", "@notionhq/notion-mcp-server"]


def _start_process(token: str) -> subprocess.Popen:
    """Start a Notion MCP server subprocess and perform the handshake."""
    env = os.environ.copy()
    env["NOTION_TOKEN"] = token
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
        bufsize=1,  # line-buffered
    )

    # Send initialize handshake
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

    # Drain the initialize response (id=1) to keep stdout clean
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        line = proc.stdout.readline()
        if not line:
            break
        try:
            msg = json.loads(line)
            if msg.get("id") == 1:
                break  # Handshake complete
        except json.JSONDecodeError:
            continue

    logger.info("[MCP] Persistent Notion process started (pid=%s)", proc.pid)
    return proc


def _get_process(token: str) -> subprocess.Popen:
    """Get or create a persistent process for the given token."""
    with _process_lock:
        proc = _process_pool.get(token)
        if proc is None or proc.poll() is not None:  # not running
            if proc is not None:
                logger.warning("[MCP] Notion process died, restarting...")
                try:
                    proc.kill()
                except Exception:
                    pass
            proc = _start_process(token)
            _process_pool[token] = proc
        return proc


def _call_notion_persistent(method: str, params: dict | None, token: str, timeout: int = 30) -> dict | str:
    """
    Call a Notion MCP method using the persistent process (low-latency path).
    Sends a JSON-RPC request and reads until we get the matching response id.
    Falls back to one-shot if anything goes wrong.
    """
    msg_id = _next_msg_id()
    request = json.dumps({
        "jsonrpc": "2.0",
        "id": msg_id,
        "method": method,
        "params": params or {}
    }) + "\n"

    try:
        proc = _get_process(token)
        proc.stdin.write(request)
        proc.stdin.flush()

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            line = proc.stdout.readline()
            if not line:
                # Process ended
                raise RuntimeError("Notion MCP process closed stdout unexpectedly")
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
        # Remove dead process from pool so next call starts fresh
        with _process_lock:
            _process_pool.pop(token, None)
        return _call_notion_mcp_sync(method, params, token=token, timeout=60)


# ── Graceful cleanup on shutdown ──────────────────────────────────────────────
import atexit

def _cleanup_notion_processes():
    """Kill all persistent Notion MCP processes on server shutdown."""
    with _process_lock:
        for token_key, proc in list(_process_pool.items()):
            try:
                proc.kill()
                logger.info("[MCP] Killed Notion process pid=%s on shutdown", proc.pid)
            except Exception:
                pass
        _process_pool.clear()

atexit.register(_cleanup_notion_processes)


# ── Helper functions ─────────────────────────────────────────────────────────
def _get_notion_token() -> str | None:
    # STRICT MODE: No environment variable fallback.
    # Connections must be explicitly provided via user_id -> Supabase.
    return None


def _disconnected_limb() -> dict:
    return {
        "id": NOTION_LIMB_ID,
        "name": NOTION_LIMB_NAME,
        "status": "disconnected",
        "tools_count": 0,
    }


def get_notion_limb_status_cached() -> dict:
    """Return current Notion limb from cache (never blocks)."""
    global _cached, _cached_at
    now = time.monotonic()
    if _cached is not None and (now - _cached_at) < _CACHE_TTL_SEC:
        return _cached
    return _disconnected_limb()


# ── Legacy one-shot fallback ──────────────────────────────────────────────────
def _call_notion_mcp_sync(method: str, params: dict | None = None, token: str | None = None, timeout: int = 60) -> dict | str:
    """
    Call Notion MCP server synchronously via subprocess.
    Uses communicate() for reliability on Windows.
    """
    if not token and not os.environ.get("NOTION_TOKEN"):
        return "Notion not configured (active connection required)."
    
    # Use provided token or fallback to env (only if allowed, but user requested no fallbacks so agent will pass token)
    # Ideally agent always passes token.
    api_token = token or os.environ.get("NOTION_TOKEN", "")
    
    env = os.environ.copy()
    env["NOTION_TOKEN"] = api_token
    env["PYTHONUNBUFFERED"] = "1"
    env["NODE_NO_WARNINGS"] = "1"
    
    # Build command for Windows vs Unix
    if sys.platform == "win32":
        cmd = ["cmd.exe", "/c", "npx", "-y", "@notionhq/notion-mcp-server"]
    else:
        cmd = ["npx", "-y", "@notionhq/notion-mcp-server"]
    
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
    
    initialized_notif = json.dumps({
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    })
    
    method_request = json.dumps({
        "jsonrpc": "2.0",
        "id": 2,
        "method": method,
        "params": params or {}
    })
    
    # Combine all requests
    full_input = f"{init_request}\n{initialized_notif}\n{method_request}\n"
    
    process = None
    try:
        print(f"[MCP DEBUG] Starting subprocess for method: {method}", flush=True)
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            encoding='utf-8',  # Force UTF-8 instead of Windows default cp1252
            errors='replace',  # Replace invalid characters instead of crashing
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        
        # Send all requests and get all output
        stdout, stderr = process.communicate(input=full_input, timeout=timeout)
        
        print(f"[MCP DEBUG] stdout length: {len(stdout)}, stderr length: {len(stderr)}", flush=True)
        if stderr:
            print(f"[MCP DEBUG] stderr: {stderr[:300]}", flush=True)
        
        if not stdout:
            return f"MCP server returned no output. stderr: {stderr[:200] if stderr else 'none'}"
        
        # Parse the output - find the response to our method request (id=2)
        lines = stdout.strip().split('\n')
        print(f"[MCP DEBUG] Got {len(lines)} response lines", flush=True)
        
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                response = json.loads(line)
                # Look for response with id=2 (our method request)
                if response.get("id") == 2:
                    if "error" in response:
                        error_obj = response.get("error", {})
                        if isinstance(error_obj, dict):
                            return f"MCP error: {error_obj.get('message', str(error_obj))}"
                        return f"MCP error: {error_obj}"
                    print(f"[MCP DEBUG] Found response for id=2", flush=True)
                    return response.get("result", response)
            except json.JSONDecodeError:
                continue
        
        # If no response with id=2 found, return the last valid JSON
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                response = json.loads(line)
                if "result" in response:
                    return response.get("result", response)
            except json.JSONDecodeError:
                continue
        
        return f"No valid response found. Raw output: {stdout[:500]}"
            
    except subprocess.TimeoutExpired:
        if process:
            process.kill()
        return "MCP server timed out"
    except Exception as e:
        logger.exception("MCP subprocess error: %s", e)
        return f"MCP subprocess error: {e}"
    finally:
        if process:
            try:
                process.kill()
            except:
                pass


async def get_notion_limb_status() -> dict:
    """Connect to Notion MCP and get limb status."""
    global _cached, _cached_at
    now = time.monotonic()
    if _cached is not None and (now - _cached_at) < _CACHE_TTL_SEC:
        return _cached

    if not _get_notion_token():
        return _disconnected_limb()

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor, 
            lambda: _call_notion_persistent("tools/list", {}, token=api_token)
        )
        
        if isinstance(result, str):
            logger.warning("Notion MCP failed: %s", result)
            return _disconnected_limb()
        
        tools = result.get("tools", [])
        limb = {
            "id": NOTION_LIMB_ID,
            "name": NOTION_LIMB_NAME,
            "status": "active",
            "tools_count": len(tools),
        }
        _cached = limb
        _cached_at = time.monotonic()
        return limb
        
    except Exception as e:
        logger.warning("get_notion_limb_status failed: %s", e)
        return _disconnected_limb()


async def call_notion_tool(tool_name: str, arguments: dict, token: str | None = None) -> str:
    """Call a Notion MCP tool via synchronous subprocess."""
    # Use provided token or fallback to env (only if allowed, but user requested no fallbacks so agent will pass token)
    api_token = token or _get_notion_token()
    
    if not api_token:
        return "Notion not configured (active connection required)."
    
    logger.info("Calling Notion tool: %s with args: %s", tool_name, arguments)
    
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor,
            lambda: _call_notion_persistent("tools/call", {
                "name": tool_name,
                "arguments": arguments
            }, token=api_token)
        )
        
        logger.info("Notion tool result type: %s", type(result))
        
        if isinstance(result, str):
            logger.warning("Notion tool returned error: %s", result)
            return result  # Error message
        
        # Extract content from result
        content = result.get("content", [])
        parts = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                parts.append(c.get("text", ""))
            elif isinstance(c, str):
                parts.append(c)
            else:
                parts.append(str(c))
        
        response = "\n".join(parts) if parts else json.dumps(result, indent=2)
        
        # Smart Summarization for Gemini
        try:
            # Parse the response string to interact with the data structure
            data = None
            try:
                data = json.loads(response)
            except (json.JSONDecodeError, TypeError):
                # If response isn't valid JSON, fallback to result object if available
                if isinstance(result, dict):
                    data = result

            if data and isinstance(data, dict) and (data.get("object") == "list" or "results" in data):
                logger.info("Summarizing Notion list response...")
                summary = []
                for item in data.get("results", []):
                    # Basic fields
                    item_summary = {
                        "id": item.get("id"),
                        "type": item.get("object"), # page or database
                        "url": item.get("url"),
                    }
                    
                    # Extract Title/Name from properties
                    props = item.get("properties", {})
                    title = "Untitled"
                    
                    # Search for title property
                    for key, val in props.items():
                        # Standard title property
                        if val.get("id") == "title":
                            title_obj = val.get("title", [])
                            if title_obj:
                                title = title_obj[0].get("text", {}).get("content", "Untitled")
                            break
                        # Database title (often just "Name")
                        if key.lower() == "name" and val.get("title"):
                            title_obj = val.get("title", [])
                            if title_obj:
                                title = title_obj[0].get("text", {}).get("content", "Untitled")
                        
                        # GENERIC Property Extraction for ANY schema
                        ptype = val.get("type")
                        if not ptype: continue
                        
                        # Skip title as we handled it
                        if val.get("id") == "title": continue
                        
                        value = None
                        if ptype == "status":
                            value = val.get("status", {}).get("name")
                        elif ptype == "select":
                            s = val.get("select")
                            if s: value = s.get("name")
                        elif ptype == "multi_select":
                            tags = val.get("multi_select")
                            if isinstance(tags, list):
                                value = ", ".join([t.get("name", "") for t in tags[:3]]) # Limit to 3
                        elif ptype == "date":
                            d = val.get("date")
                            if d:
                                start = d.get("start")
                                end = d.get("end")
                                value = f"{start}->{end}" if end else start
                        elif ptype == "checkbox":
                            value = val.get("checkbox")
                        elif ptype == "people":
                            people = val.get("people")
                            if isinstance(people, list):
                                value = ", ".join([p.get("name", "User") for p in people[:2]])
                        elif ptype == "url":
                            value = val.get("url")
                        elif ptype == "email":
                            value = val.get("email")
                        elif ptype == "phone_number":
                            value = val.get("phone_number")
                        elif ptype == "number":
                            value = val.get("number")
                        elif ptype == "rich_text":
                            rt = val.get("rich_text")
                            if isinstance(rt, list) and rt:
                                txt = rt[0].get("plain_text", "")
                                value = txt[:50] + "..." if len(txt) > 50 else txt
                        elif ptype == "formula":
                            # Try to get formula output
                            f = val.get("formula", {})
                            ftype = f.get("type")
                            if ftype in ["string", "number", "boolean", "date"]:
                                value = f.get(ftype)

                        try:
                            if value is not None and value != "" and value != []:
                                item_summary[key] = value
                        except Exception as e:
                            logger.warning("Error adding property %s: %s", key, e)

                    item_summary["title"] = title
                    
                    # For databases, add description if available
                    if item.get("object") == "database":
                        desc = item.get("description", [])
                        if desc:
                            item_summary["description"] = desc[0].get("text", {}).get("content", "")
                            
                    summary.append(item_summary)
                    
                    # Limit to 2000 items for Gemini (1M context)
                    if len(summary) >= 2000:
                        break
                
                # Create compact response
                response = json.dumps({
                    "object": "list", 
                    "total": len(summary), 
                    "results": summary,
                    "note": "Optimized for Gemini: Showing up to 2000 items."
                }, indent=2)
                logger.info("Summarized Notion list to %d chars", len(response))
                
        except Exception as e:
            logger.exception("Failed to summarize Notion response: %s", e)
            # Fallback to truncation only if summarization fails
            MAX_CHARS = 1000000 # 1M Chars
            if len(response) > MAX_CHARS:
                response = response[:MAX_CHARS] + "\n...[truncated]"

        logger.info("Notion tool success, final response length: %d", len(response))
        return response
        
    except Exception as e:
        logger.exception("call_notion_tool failed: %s", e)
        return f"Notion tool failed: {e}"


async def get_notion_tool_list(token: str | None = None) -> list[dict]:
    """Get list of Notion MCP tools."""
    # Use provided token or fallback to env
    api_token = token or _get_notion_token()
    
    if not api_token:
        return []
    
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor,
            lambda: _call_notion_persistent("tools/list", {}, token=api_token)
        )
        
        if isinstance(result, str):
            logger.warning("get_notion_tool_list failed: %s", result)
            return []
        
        tools = result.get("tools", [])
        tool_names = [t.get("name") for t in tools]
        logger.info(f"Available Notion tools ({len(tools)}): {tool_names}")
        logger.info("Got %d Notion tools", len(tools))
        return [{"name": t.get("name", ""), "description": t.get("description", "")} for t in tools]
        
    except Exception as e:
        logger.warning("get_notion_tool_list failed: %s", e)
        return []
