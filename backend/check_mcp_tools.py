import asyncio
import json
import os
import subprocess
import sys

def get_notion_token():
    # Read from .env if needed
    try:
        with open(".env", "r") as f:
            for line in f:
                if line.startswith("NOTION_TOKEN="):
                    return line.split("=", 1)[1].strip()
    except:
        pass
    return os.environ.get("NOTION_TOKEN", "")

def call_mcp_list_tools():
    token = get_notion_token()
    if not token:
        print("NOTION_TOKEN not found.")
        return

    env = os.environ.copy()
    env["NOTION_TOKEN"] = token
    env["PYTHONUNBUFFERED"] = "1"
    
    cmd = ["cmd.exe", "/c", "npx", "-y", "@notionhq/notion-mcp-server"]
    
    init_request = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "nexus-agent-inspector", "version": "1.0.0"}
        }
    })
    
    initialized_notif = json.dumps({
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    })
    
    list_tools_request = json.dumps({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    })
    
    full_input = f"{init_request}\n{initialized_notif}\n{list_tools_request}\n"
    
    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        
        stdout, stderr = process.communicate(input=full_input, timeout=30)
        
        if stderr:
            print(f"STDERR: {stderr[:500]}")
            
        print("\n--- TOOLS LIST RESPONSE ---")
        lines = stdout.strip().split('\n')
        for line in lines:
            try:
                data = json.loads(line)
                if data.get("id") == 2 and "result" in data:
                    tools = data["result"].get("tools", [])
                    for tool in tools:
                        print(f"- {tool['name']}: {tool.get('description', 'No description')}")
            except:
                pass
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    call_mcp_list_tools()
