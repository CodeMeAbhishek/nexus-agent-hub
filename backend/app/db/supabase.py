"""
Supabase client initialization and helper functions.
Provides database access for user settings, connections, and auth.
"""
import os
import logging
from typing import Optional
from functools import lru_cache

from supabase import create_client, Client
from supabase.lib.client_options import SyncClientOptions
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# Cache the Supabase client
@lru_cache(maxsize=1)
def get_supabase_client() -> Optional[Client]:
    """
    Get a cached Supabase client instance using anon key (respects RLS).
    Returns None if not configured (allows app to run without Supabase).
    """
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_ANON_KEY", "").strip()
    
    if not url or not key:
        logger.warning(
            "Supabase not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY in .env"
        )
        return None
    
    try:
        client = create_client(url, key)
        logger.info("Supabase client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        return None


@lru_cache(maxsize=1)
def get_service_client() -> Optional[Client]:
    """
    Get a cached Supabase client using SERVICE_ROLE key (bypasses RLS).
    Use this for backend operations that need to access user data on their behalf.
    """
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    
    if not url or not key:
        logger.warning(
            "Supabase service role not configured. Set SUPABASE_SERVICE_ROLE_KEY in .env"
        )
        # Fallback to anon client (will fail with RLS)
        return get_supabase_client()
    
    try:
        client = create_client(url, key)
        logger.info("Supabase service client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to create Supabase service client: {e}")
        return None



# Encryption for storing API credentials
_fernet: Optional[Fernet] = None

def get_fernet() -> Optional[Fernet]:
    """Get Fernet instance for encrypting/decrypting credentials."""
    global _fernet
    if _fernet is not None:
        return _fernet
    
    key = os.environ.get("CREDENTIALS_ENCRYPTION_KEY", "").strip()
    if not key:
        logger.error(
            "CREDENTIALS_ENCRYPTION_KEY not set in environment. "
            "Cannot encrypt/decrypt credentials!"
        )
        return None
    
    try:
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
        return _fernet
    except Exception as e:
        logger.error(f"Failed to initialize Fernet: {e}")
        return None


def encrypt_credentials(data: str) -> Optional[str]:
    """Encrypt a string (e.g., JSON credentials) for storage."""
    fernet = get_fernet()
    if not fernet:
        return None
    try:
        return fernet.encrypt(data.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return None


def decrypt_credentials(encrypted: str) -> Optional[str]:
    """Decrypt stored credentials."""
    fernet = get_fernet()
    if not fernet:
        return None
    try:
        return fernet.decrypt(encrypted.encode()).decode()
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return None


# ============================================================================
# User Settings Operations
# ============================================================================

async def get_user_settings(user_id: str) -> Optional[dict]:
    """Get user settings from database."""
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        response = client.table("user_settings").select("*").eq("user_id", user_id).single().execute()
        return response.data
    except Exception as e:
        logger.error(f"Failed to get user settings: {e}")
        return None


async def upsert_user_settings(user_id: str, settings: dict) -> bool:
    """Create or update user settings."""
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        data = {**settings, "user_id": user_id}
        client.table("user_settings").upsert(data, on_conflict="user_id").execute()
        return True
    except Exception as e:
        logger.error(f"Failed to upsert user settings: {e}")
        return False


# ============================================================================
# User Connections (Limb Credentials) Operations
# ============================================================================

async def get_user_connections(user_id: str) -> list[dict]:
    """Get all limb connections for a user."""
    # Use service client to bypass RLS
    client = get_service_client()
    if not client:
        return []
    
    try:
        response = client.table("user_connections").select("*").eq("user_id", user_id).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get user connections: {e}")
        return []


async def save_connection(
    user_id: str, 
    limb_id: str, 
    credentials: dict, 
    jwt: Optional[str] = None
) -> bool:
    """Save or update a limb connection with encrypted credentials."""
    # If JWT provided, create a fresh authenticated client to satisfy RLS
    if jwt:
        url = os.environ.get("SUPABASE_URL", "").strip()
        key = os.environ.get("SUPABASE_ANON_KEY", "").strip()
        # Create client with user's auth token
        # Note: We pass headers directly to emulate an authenticated request
        try:
            # Use SyncClientOptions to pass headers
            options = SyncClientOptions()
            options.headers.update({"Authorization": f"Bearer {jwt}"})
            client = create_client(url, key, options=options)
        except Exception as e:
            logger.error(f"Failed to create authenticated client: {e}")
            return False
    else:
        # Fallback to anonymous client (only works if RLS allows anon inserts)
        client = get_supabase_client()
    
    if not client:
        return False
    
    try:
        import json
        encrypted = encrypt_credentials(json.dumps(credentials))
        if not encrypted:
            return False
        
        data = {
            "user_id": user_id,
            "limb_id": limb_id,
            "encrypted_credentials": encrypted,
            "is_enabled": True,
        }
        
        client.table("user_connections").upsert(
            data, 
            on_conflict="user_id,limb_id"
        ).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to save connection: {e}")
        return False


async def get_connection_credentials(user_id: str, limb_id: str) -> Optional[dict]:
    """Get decrypted credentials for a specific limb."""
    # Use service client to bypass RLS - backend needs to read user data on their behalf
    client = get_service_client()
    if not client:
        return None
    
    try:
        response = (
            client.table("user_connections")
            .select("encrypted_credentials")
            .eq("user_id", user_id)
            .eq("limb_id", limb_id)
            .eq("is_enabled", True)
            .single()
            .execute()
        )
        
        if not response.data or not response.data.get("encrypted_credentials"):
            logger.warning(f"No credentials found for {limb_id}")
            return None
        
        import json
        decrypted = decrypt_credentials(response.data["encrypted_credentials"])
        if not decrypted:
            logger.error("Failed to decrypt credentials")
            return None
        
        return json.loads(decrypted)
    except Exception as e:
        logger.error(f"Failed to get connection credentials: {e}")
        return None


async def delete_connection(user_id: str, limb_id: str, jwt: Optional[str] = None) -> bool:
    """Delete a limb connection."""
    if jwt:
        url = os.environ.get("SUPABASE_URL", "").strip()
        key = os.environ.get("SUPABASE_ANON_KEY", "").strip()
        try:
            options = SyncClientOptions()
            options.headers.update({"Authorization": f"Bearer {jwt}"})
            client = create_client(url, key, options=options)
        except Exception:
            return False
    else:
        client = get_supabase_client()

    if not client:
        return False
    
    try:
        client.table("user_connections").delete().eq("user_id", user_id).eq("limb_id", limb_id).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to delete connection: {e}")
        return False


def is_supabase_configured() -> bool:
    """Check if Supabase is properly configured."""
    return get_supabase_client() is not None
