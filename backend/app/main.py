"""
Nexus Agent Hub — FastAPI backend.
Orchestration + MCP connectivity; SSE streaming in Phase 3.
"""
import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import chat, health, tools, stream, settings, history
from app.auth import routes as auth_routes
from app.utils.response import error_response
from app.utils.exceptions import NexusException
from fastapi import Request
from fastapi.exceptions import RequestValidationError
import logging
import sys

# Configure logging for the entire application
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)

# Suppress noisy libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("watchfiles").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Load .env from backend/ so OPENAI_API_KEY etc. are found regardless of cwd
_backend_root = Path(__file__).resolve().parent.parent
load_dotenv(_backend_root / ".env")


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080"
    ).split(","),
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