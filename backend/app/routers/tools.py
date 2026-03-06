"""
Tools (list_tools) handshake — verify all MCP limbs are responsive.
Phase 1.2: Notion MCP wired; /api/tools returns immediately from cache;
background task refreshes limb status so the request never blocks.
"""
from fastapi import APIRouter, Depends

from app.mcp.notion import get_notion_limb_status_cached
from app.mcp.slack import get_slack_limb_status_cached
from app.auth.routes import get_current_user
from app.utils.response import standard_response

router = APIRouter()


# Limb ids aligned with frontend AgentLimbs (Slack, Notion, GitHub, etc.)
STUB_LIMBS = [
    {"id": "slack", "name": "Slack", "status": "disconnected", "tools_count": 0},
    {"id": "notion", "name": "Notion", "status": "disconnected", "tools_count": 0},
    {"id": "github", "name": "GitHub", "status": "disconnected", "tools_count": 0},
    {"id": "mongodb", "name": "MongoDB", "status": "disconnected", "tools_count": 0},
    {"id": "gmail", "name": "Gmail", "status": "disconnected", "tools_count": 0},
    {"id": "calendar", "name": "Google Calendar", "status": "disconnected", "tools_count": 0},
    {"id": "googledrive", "name": "Google Drive", "status": "disconnected", "tools_count": 0},
    {"id": "filesystem", "name": "Local Files", "status": "disconnected", "tools_count": 0},
]


@router.get("/")
async def list_tools(user: dict | None = Depends(get_current_user)):
    """
    List connected MCP tools (limbs).
    Fetches real-time status from Supabase for all user connections.
    """
    from app.db.supabase import get_user_connections
    
    # Get user's actual connections from Supabase
    user_connections = {}
    if user:
        connections = await get_user_connections(user["id"])
        user_connections = {conn["limb_id"]: conn for conn in connections}
    
    limbs = []
    for limb in STUB_LIMBS:
        if limb["id"] in user_connections:
            # User has this limb connected - show as active
            conn = user_connections[limb["id"]]
            # Determine tools count based on limb type
            tools_count = 0
            if limb["id"] == "gmail":
                tools_count = 3
            elif limb["id"] == "slack":
                tools_count = 10  # Slack has 10 tools
            elif limb["id"] == "notion":
                tools_count = 10  # Notion has 10 tools
            elif limb["id"] == "calendar":
                tools_count = 3   # Calendar has 3 tools
            elif limb["id"] == "github":
                tools_count = 5   # GitHub has ~5 core tools
            elif limb["id"] == "googledrive":
                tools_count = 3   # Drive has 3 tools
            elif limb["id"] == "mongodb":
                tools_count = 3   # MongoDB has 3 tools
            
            limbs.append({
                "id": limb["id"],
                "name": limb["name"],
                "status": "active" if conn["is_enabled"] else "disconnected",
                "tools_count": tools_count
            })
        else:
            # Not connected - show default stub
            limbs.append(limb)
    
    total_tools = sum(l["tools_count"] for l in limbs)
    return standard_response(data={"limbs": limbs, "total_tools": total_tools})

