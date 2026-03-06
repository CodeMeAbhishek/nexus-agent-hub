"""
Tools (list_tools) handshake — list limbs and connection status.
Limb definitions and tool counts come from the central registry.
"""
from fastapi import APIRouter, Depends

from app.auth.routes import get_current_user
from app.core.limbs import get_all_limbs_for_api, get_tools_count
from app.db.supabase import get_user_connections
from app.utils.response import standard_response

router = APIRouter()


@router.get("/")
async def list_tools(user: dict | None = Depends(get_current_user)):
    """
    List limbs (integrations). Status and tools_count from registry + user connections.
    """
    stub_limbs = get_all_limbs_for_api()
    user_connections = {}
    if user:
        connections = await get_user_connections(user["id"])
        user_connections = {c["limb_id"]: c for c in connections}

    limbs = []
    for limb in stub_limbs:
        if limb["id"] in user_connections:
            conn = user_connections[limb["id"]]
            limbs.append({
                "id": limb["id"],
                "name": limb["name"],
                "status": "active" if conn.get("is_enabled", True) else "disconnected",
                "tools_count": get_tools_count(limb["id"]),
            })
        else:
            limbs.append(limb)

    total_tools = sum(l["tools_count"] for l in limbs)
    return standard_response(data={"limbs": limbs, "total_tools": total_tools})

