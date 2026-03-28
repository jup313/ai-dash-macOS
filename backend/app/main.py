"""
ai-dash-macOS — FastAPI Application Entry Point.

Universal LLM Control Center for macOS Apple Silicon.
Phase 0: Health check and environment validation only.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.agents import router as agents_router
from backend.app.api.coding import router as coding_router
from backend.app.api.conversations import router as conversations_router
from backend.app.api.health import router as health_router
from backend.app.api.llm import router as llm_router
from backend.app.agents.executor import reset_executor
from backend.app.agents.registry import reset_registry
from backend.app.coding.file_manager import reset_file_manager
from backend.app.core.config import get_settings
from backend.app.llm.router import reset_router
from backend.app.memory.store import reset_store

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("ai-dash-macOS starting up")
    logger.info("Provider: %s", settings.llm_provider)
    logger.info("Ollama URL: %s", settings.ollama_base_url)
    logger.info("Remote models: %s", settings.allow_remote_models)
    yield
    reset_router()
    reset_registry()
    reset_executor()
    reset_store()
    reset_file_manager()
    logger.info("ai-dash-macOS shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="ai-dash-macOS",
        description="Universal LLM Control Center for macOS Apple Silicon",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS — localhost only
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    application.include_router(health_router, tags=["health"])
    application.include_router(llm_router)
    application.include_router(agents_router)
    application.include_router(conversations_router)
    application.include_router(coding_router)

    return application


# Application instance
app = create_app()
