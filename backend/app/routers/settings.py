"""
Settings API routes for user preferences and limb connections.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel

from app.auth.routes import require_auth, get_current_user
from app.db.supabase import (
    get_user_settings,
    upsert_user_settings,
    get_user_connections,
    save_connection,
    delete_connection,
    is_supabase_configured,
)

logger = logging.getLogger(__name__)
from app.utils.response import standard_response
router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class UserSettings(BaseModel):
    theme: str = "dark"
    default_model: str = "gemini-2.0-flash"
    notifications_enabled: bool = True


class ConnectionRequest(BaseModel):
    token: str  # The API token/key for the limb
    team_id: Optional[str] = None # Required for Slack


class ConnectionResponse(BaseModel):
    limb_id: str
    is_enabled: bool
    last_verified_at: Optional[str] = None


class MessageResponse(BaseModel):
    message: str
    success: bool


# ============================================================================
# Routes
# ============================================================================

@router.get("/status")
async def settings_status():
    """Check if settings service is configured."""
    return standard_response(data={
        "configured": is_supabase_configured(),
        "database": "supabase" if is_supabase_configured() else "memory",
    })


@router.get("")
async def get_settings(user: dict = Depends(require_auth)):
    """Get current user's settings."""
    settings = await get_user_settings(user["id"])
    
    if settings:
        return standard_response(data=UserSettings(
            theme=settings.get("theme", "dark"),
            default_model=settings.get("default_model", "gemini-2.0-flash"),
            notifications_enabled=settings.get("notifications_enabled", True),
        ))
    
    # Return defaults if no settings exist
    return standard_response(data=UserSettings())


@router.put("")
async def update_settings(settings: UserSettings, user: dict = Depends(require_auth)):
    """Update current user's settings."""
    success = await upsert_user_settings(user["id"], settings.model_dump())
    
    if success:
        return standard_response(data={"message": "Settings updated"})
    else:
        raise HTTPException(status_code=500, detail="Failed to update settings")


@router.get("/connections")
async def get_connections(user: dict = Depends(require_auth)):
    """Get all limb connections for current user."""
    connections = await get_user_connections(user["id"])
    
    return standard_response(data=[
        {
            "limb_id": conn["limb_id"],
            "is_enabled": conn.get("is_enabled", False),
            "last_verified_at": conn.get("last_verified_at"),
        }
        for conn in connections
    ])


@router.post("/connections/{limb_id}")
async def connect_limb(
    limb_id: str, 
    request: ConnectionRequest, 
    authorization: str = Header(...),
    user: dict = Depends(require_auth)
):
    """
    Connect a limb by storing its credentials.
    The token is encrypted before storage.
    """
    from app.core.limbs import get_valid_limb_ids
    if limb_id not in get_valid_limb_ids():
        raise HTTPException(status_code=400, detail=f"Invalid limb: {limb_id}")
    
    # Store the credentials
    jwt = authorization.replace("Bearer ", "")
    
    credentials = {"token": request.token}
    if request.team_id:
        credentials["team_id"] = request.team_id
        
    success = await save_connection(user["id"], limb_id, credentials, jwt=jwt)
    
    if success:
        return standard_response(data={
            "message": f"Successfully connected to {limb_id}", 
            "success": True
        })
    else:
        raise HTTPException(status_code=500, detail="Failed to save connection")


@router.delete("/connections/{limb_id}")
async def disconnect_limb(
    limb_id: str, 
    authorization: str = Header(...),
    user: dict = Depends(require_auth)
):
    """Disconnect a limb by removing its credentials."""
    jwt = authorization.replace("Bearer ", "")
    success = await delete_connection(user["id"], limb_id, jwt=jwt)
    
    if success:
        return standard_response(data={
            "message": f"Successfully disconnected from {limb_id}", 
            "success": True
        })
    else:
        raise HTTPException(status_code=500, detail="Failed to disconnect")


class GmailExchangeRequest(BaseModel):
    code: str
    client_config: dict


@router.post("/connections/gmail/exchange")
async def exchange_gmail_token(
    request: GmailExchangeRequest,
    authorization: str = Header(...),
    user: dict = Depends(require_auth)
):
    """
    Exchange OAuth code for Gmail tokens using provided client config.
    Saves the full credentials JSON to Supabase.
    """
    try:
        from google_auth_oauthlib.flow import Flow
        from app.mcp.gmail import GMAIL_SCOPES
        
        # flow.from_client_config expects the full dict
        flow = Flow.from_client_config(
            request.client_config,
            scopes=GMAIL_SCOPES,
            redirect_uri='urn:ietf:wg:oauth:2.0:oob'
        )
        
        # Exchange code
        flow.fetch_token(code=request.code)
        
        # Get credentials
        creds = flow.credentials
        
        creds_data = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }
        
        # Save to Supabase
        jwt = authorization.replace("Bearer ", "")
        
        # We assume limb_id is "gmail"
        success = await save_connection(user["id"], "gmail", creds_data, jwt=jwt)
        
        if success:
            return standard_response(data={
                "message": "Successfully connected to Gmail",
                "success": True
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to save Gmail connection")
            
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Gmail exchange failed: {e}")
        # Return partial error message to user
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed. check logs.")


class CalendarExchangeRequest(BaseModel):
    code: str
    client_config: dict


@router.post("/connections/calendar/exchange")
async def exchange_calendar_token(
    request: CalendarExchangeRequest,
    authorization: str = Header(...),
    user: dict = Depends(require_auth)
):
    """
    Exchange OAuth code for Google Calendar tokens using provided client config.
    Saves the full credentials JSON to Supabase.
    """
    try:
        from google_auth_oauthlib.flow import Flow
        from app.mcp.calendar import CALENDAR_SCOPES
        
        flow = Flow.from_client_config(
            request.client_config,
            scopes=CALENDAR_SCOPES,
            redirect_uri='urn:ietf:wg:oauth:2.0:oob'
        )
        
        flow.fetch_token(code=request.code)
        creds = flow.credentials
        
        creds_data = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }
        
        jwt = authorization.replace("Bearer ", "")
        success = await save_connection(user["id"], "calendar", creds_data, jwt=jwt)
        
        if success:
            return standard_response(data={
                "message": "Successfully connected to Google Calendar",
                "success": True
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to save Calendar connection")
            
    except Exception as e:
        logger.error(f"Calendar exchange failed: {e}")
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed. Check logs.")


class DriveExchangeRequest(BaseModel):
    code: str
    client_config: dict


@router.post("/connections/googledrive/exchange")
async def exchange_drive_token(
    request: DriveExchangeRequest,
    authorization: str = Header(...),
    user: dict = Depends(require_auth)
):
    """
    Exchange OAuth code for Google Drive tokens using provided client config.
    Saves the full credentials JSON to Supabase.
    """
    try:
        from google_auth_oauthlib.flow import Flow
        from app.mcp.drive import DRIVE_SCOPES
        
        flow = Flow.from_client_config(
            request.client_config,
            scopes=DRIVE_SCOPES,
            redirect_uri='urn:ietf:wg:oauth:2.0:oob'
        )
        
        flow.fetch_token(code=request.code)
        creds = flow.credentials
        
        creds_data = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }
        
        jwt = authorization.replace("Bearer ", "")
        success = await save_connection(user["id"], "googledrive", creds_data, jwt=jwt)
        
        if success:
            return standard_response(data={
                "message": "Successfully connected to Google Drive",
                "success": True
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to save Drive connection")
            
    except Exception as e:
        logger.error(f"Drive exchange failed: {e}")
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed. Check logs.")


@router.post("/connections/{limb_id}/test")
async def test_connection(limb_id: str, user: dict = Depends(require_auth)):
    """
    Test if a limb connection is working.
    TODO: Implement actual connection testing per limb.
    """
    # For now, just check if credentials exist
    connections = await get_user_connections(user["id"])
    limb_conn = next((c for c in connections if c["limb_id"] == limb_id), None)
    
    if limb_conn and limb_conn.get("is_enabled"):
        return standard_response(data={
            "message": f"Connection to {limb_id} is active", 
            "success": True
        })
    else:
        return standard_response(data={
            "message": f"No active connection to {limb_id}", 
            "success": False
        })
