"""
Authentication routes using Supabase Auth.
Provides signup, login, logout, and current user endpoints.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr

from app.db.supabase import get_supabase_client, is_supabase_configured
from app.utils.response import standard_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


# ============================================================================
# Request/Response Models
# ============================================================================

class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    created_at: Optional[str] = None


class MessageResponse(BaseModel):
    message: str


# ============================================================================
# Auth Dependency
# ============================================================================

async def get_current_user(authorization: str = Header(None)) -> Optional[dict]:
    """
    Extract and verify user from Authorization header.
    Returns None if not authenticated (allows optional auth).
    """
    if not authorization:
        return None
    
    if not authorization.startswith("Bearer "):
        return None
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        # Verify token with Supabase
        response = client.auth.get_user(token)
        if response and response.user:
            return {
                "id": response.user.id,
                "email": response.user.email,
                "created_at": str(response.user.created_at) if response.user.created_at else None,
            }
    except Exception as e:
        logger.debug(f"Token verification failed: {e}")
    
    return None


async def require_auth(authorization: str = Header(...)) -> dict:
    """
    Require authentication. Raises 401 if not authenticated.
    """
    user = await get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ============================================================================
# Routes
# ============================================================================

@router.get("/status")
async def auth_status():
    """Check if authentication is configured."""
    return standard_response(data={
        "configured": is_supabase_configured(),
        "provider": "supabase" if is_supabase_configured() else None,
    })


@router.post("/signup")
async def signup(request: SignupRequest):
    """
    Create a new user account.
    Returns AuthResponse if auto-confirmed, or a message if email confirmation is required.
    """
    client = get_supabase_client()
    if not client:
        raise HTTPException(
            status_code=503, 
            detail="Authentication service not configured"
        )
    
    try:
        response = client.auth.sign_up({
            "email": request.email,
            "password": request.password,
        })
        
        # If we got a session, user is auto-confirmed
        if response.user and response.session:
            return standard_response(data={
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                },
            })
        # User created but needs email confirmation
        elif response.user:
            return standard_response(data={
                "email_confirmation_required": True,
                "message": "Account created! Please check your email to confirm your account.",
                "user": {
                    "id": response.user.id,
                    "email": response.user.email,
                },
            })
        else:
            raise HTTPException(
                status_code=400, 
                detail="Signup failed. Please try again."
            )
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        if "already registered" in error_msg:
            raise HTTPException(status_code=409, detail="Email already registered")
        logger.error(f"Signup failed: {e}")
        if "getaddrinfo" in error_msg or "11001" in str(e) or "name or service not known" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="Cannot reach the authentication server. Check your internet connection and DNS, or try again in a few minutes.",
            )
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(request: LoginRequest):
    """
    Sign in an existing user.
    """
    client = get_supabase_client()
    if not client:
        raise HTTPException(
            status_code=503, 
            detail="Authentication service not configured"
        )
    
    try:
        response = client.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password,
        })
        
        if response.user and response.session:
            return standard_response(data=AuthResponse(
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token,
                user={
                    "id": response.user.id,
                    "email": response.user.email,
                },
            ))
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid" in error_msg or "credentials" in error_msg:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        logger.error(f"Login failed: {e}")
        # User-friendly message for DNS/network failures (e.g. getaddrinfo failed)
        if "getaddrinfo" in error_msg or "11001" in str(e) or "name or service not known" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="Cannot reach the authentication server. Check your internet connection and DNS, or try again in a few minutes.",
            )
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/logout")
async def logout(user: dict = Depends(require_auth)):
    """
    Sign out the current user.
    """
    client = get_supabase_client()
    if not client:
        raise HTTPException(
            status_code=503, 
            detail="Authentication service not configured"
        )
    
    try:
        client.auth.sign_out()
        return standard_response(data={"message": "Successfully logged out"})
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me")
async def get_me(user: dict = Depends(require_auth)):
    """
    Get the current authenticated user.
    """
    return standard_response(data=UserResponse(
        id=user["id"],
        email=user["email"],
        created_at=user.get("created_at"),
    ))


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """
    Refresh an expired access token.
    """
    client = get_supabase_client()
    if not client:
        raise HTTPException(
            status_code=503, 
            detail="Authentication service not configured"
        )
    
    try:
        response = client.auth.refresh_session(refresh_token)
        
        if response.user and response.session:
            return standard_response(data=AuthResponse(
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token,
                user={
                    "id": response.user.id,
                    "email": response.user.email,
                },
            ))
        else:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid refresh token")
