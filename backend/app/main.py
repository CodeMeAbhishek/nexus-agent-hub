"""
Nexus Agent Hub — FastAPI backend.
Orchestration + MCP connectivity; SSE streaming. Scalable, config-driven design.
"""
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.auth import routes as auth_routes
from app.core.config import get_settings
from app.middleware.rate_limit import InMemoryRateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.routers import chat, health, tools, stream, settings, history
from app.utils.exceptions import NexusException
from app.utils.response import error_response

_backend_root = Path(__file__).resolve().parent.parent
load_dotenv(_backend_root / ".env")

# Structured logging: include module and level; request_id can be added per-request in log format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("watchfiles").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # NOTE: Background limb refresh loops removed — they were no-ops
    # because _get_notion_token() returns None in strict mode.
    # Limb status is fetched on-demand when tools are loaded per request.
    logger.info("Nexus Agent Hub backend started")
    yield
    logger.info("Nexus Agent Hub backend shutting down")


app = FastAPI(
    title="Nexus Agent Hub API",
    description="Agentic AI backend for TEC-4 — Internal Knowledge Access and Action",
    version="0.1.0",
    lifespan=lifespan,
)

config = get_settings()
app.add_middleware(RequestIDMiddleware)
app.add_middleware(InMemoryRateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(stream.router, prefix="/api", tags=["Stream"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(tools.router, prefix="/api/tools", tags=["Tools"])
app.include_router(history.router, prefix="/api/history", tags=["History"])
app.include_router(auth_routes.router, tags=["auth"])

@app.exception_handler(NexusException)
async def nexus_exception_handler(request: Request, exc: NexusException):
    return error_response(
        message=exc.message,
        status_code=exc.status_code,
        error_code=exc.error_code
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return error_response(
        message="Request validation failed",
        status_code=422,
        error_code="VALIDATION_ERROR",
        details=exc.errors()
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return error_response(
        message="An unexpected server error occurred.",
        status_code=500,
        error_code="INTERNAL_SERVER_ERROR",
        details=str(exc) if app.debug else None
    )