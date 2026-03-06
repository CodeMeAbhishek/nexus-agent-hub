import asyncio
import os
import sys
import json

# Make sure we can import app modules
sys.path.append(os.getcwd())

from app.mcp.github import _call_github_mcp_sync

if __name__ == "__main__":
    if not os.getcwd().endswith("backend"):
        os.chdir("backend")
    
    print("Fetching tools and saving to tools_output.json...")
    try:
        # Use dummy token again
        res = _call_github_mcp_sync("tools/list", token="dummy-token")
        
        with open("tools_output.json", "w") as f:
            json.dump(res, f, indent=2)
            
        print("Done. Check tools_output.json")
    except Exception as e:
        print(f"Error: {e}")
