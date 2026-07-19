"""
FastAPI application factory.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes.health import router as health_router
from api.routes.tasks  import router as tasks_router
from config.logging_config import configure_logging
from config.settings import get_settings
from persistence.database import init_db

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    configure_logging()
    settings = get_settings()
    log.info("app.startup", env=settings.log_format)

    await init_db()
    log.info("db.ready")

    # Warm up singletons
    from core.knowledge.graph import KnowledgeGraph
    from core.memory.manager   import MemoryManager
    from tools.registry        import ToolRegistry

    KnowledgeGraph.instance()
    MemoryManager.instance()
    ToolRegistry.instance()

    yield

    log.info("app.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title       = "Self-Healing Multi-Agent Framework",
        description = "Autonomous agents that detect failures, identify root causes, and repair their plans.",
        version     = "1.0.0",
        lifespan    = lifespan,
        debug       = settings.api_debug,
    )

    # ── CORS ──────────────────────────────────────────────────────
    # Allow the React dev server (port 5173) and any localhost origin.
    # In production, restrict this to your actual domain.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global exception handler ───────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        log.error("unhandled_exception", path=request.url.path, error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error."},
        )

    # ── Routes ─────────────────────────────────────────────────────
    app.include_router(tasks_router)
    app.include_router(health_router)

    # ── MCP sub-app (FastMCP HTTP + SSE transport) ─────────────────
    from tools.mcp.server import get_mcp_http_app
    app.mount("/mcp", get_mcp_http_app())

    return app


app = create_app()
