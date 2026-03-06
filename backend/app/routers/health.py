"""Health and readiness for Nexus backend."""
from fastapi import APIRouter

router = APIRouter()


from app.utils.response import standard_response

@router.get("/health")
async def health():
    return standard_response(data={"status": "ok", "service": "nexus-agent-hub"})
