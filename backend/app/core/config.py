"""
Application configuration — env-backed settings with validation.
Use for CORS, rate limits, and optional feature flags; keeps os.environ for legacy paths.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS (comma-separated origins)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080"

    # Rate limiting (requests per minute per identifier; 0 = disabled)
    rate_limit_per_minute: int = 60

    # Supabase (optional for startup; validated when auth is used)
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None

    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings instance. Load .env from backend root when running as app."""
    return Settings()
