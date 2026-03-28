"""
Pytest configuration and shared fixtures.

Provides:
- FastAPI test client
- Settings override
- Async test support
"""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

# Set test environment variables before importing app
os.environ.setdefault("LLM_PROVIDER", "ollama")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("OLLAMA_MODEL", "llama3:8b")
os.environ.setdefault("ALLOW_REMOTE_MODELS", "false")
os.environ.setdefault("HOST", "127.0.0.1")
os.environ.setdefault("PORT", "8000")
os.environ.setdefault("LOG_LEVEL", "debug")

from backend.app.core.config import Settings, reset_settings
from backend.app.main import app


@pytest.fixture(autouse=True)
def _reset_settings():
    """Reset settings singleton before each test."""
    reset_settings()
    yield
    reset_settings()


@pytest.fixture
def test_settings() -> Settings:
    """Provide test settings instance."""
    return Settings(
        llm_provider="ollama",
        ollama_base_url="http://localhost:11434",
        ollama_model="llama3:8b",
        allow_remote_models=False,
        host="127.0.0.1",
        port=8000,
        log_level="debug",
    )


@pytest.fixture
async def async_client():
    """Provide async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
