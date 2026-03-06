"""
Simple in-memory rate limit middleware — per-identifier (IP or user), optional.
For multi-worker deployments, replace with Redis-backed limiter.
"""
import time
from collections import defaultdict
from typing import Callable

from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import get_settings


def _get_identifier(request: Request) -> str:
    """Prefer authenticated user id, else client IP."""
    auth = request.headers.get("Authorization") or ""
    if auth.startswith("Bearer ") and len(auth) > 20:
        # Use a hash of the token so same user counts as one (don't store raw token)
        return f"user:{hash(auth) % (10 ** 10)}"
    client = getattr(request, "client", None)
    if client:
        return f"ip:{client.host}"
    return "ip:unknown"


class InMemoryRateLimitMiddleware:
    """In-memory sliding window; resets when RATE_LIMIT_PER_MINUTE is 0."""

    def __init__(self, app, get_identifier: Callable[[Request], str] | None = None):
        self.app = app
        self.get_identifier = get_identifier or _get_identifier
        self._counts: dict[str, list[float]] = defaultdict(list)
        self._window_sec = 60

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        limit = get_settings().rate_limit_per_minute
        if limit <= 0:
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive, send)
        key = self.get_identifier(request)
        now = time.monotonic()
        # Drop timestamps outside window
        self._counts[key] = [t for t in self._counts[key] if now - t < self._window_sec]
        if len(self._counts[key]) >= limit:
            response = JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "message": "Too many requests. Please try again later.",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                },
            )
            await response(scope, receive, send)
            return

        self._counts[key].append(now)
        await self.app(scope, receive, send)
