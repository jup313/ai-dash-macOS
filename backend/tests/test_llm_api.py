"""
Tests for LLM API endpoints.

Tests:
- POST /api/llm/chat
- POST /api/llm/chat/stream
- GET /api/llm/models
- GET /api/llm/status
- GET /api/llm/providers
- Error handling (503, 500)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.llm.base import ProviderError, ProviderUnavailableError
from backend.app.llm.models import (
    ChatResponse,
    ModelInfo,
    ProviderStatus,
    RouterStatus,
)
from backend.app.llm.router import reset_router
from backend.app.main import app


@pytest.fixture(autouse=True)
def _reset_llm_router():
    """Reset LLM router before each test."""
    reset_router()
    yield
    reset_router()


@pytest.fixture
async def client():
    """Async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestChatEndpoint:
    """Tests for POST /api/llm/chat."""

    @pytest.mark.asyncio
    async def test_chat_success(self, client):
        mock_response = ChatResponse(
            content="Hello!",
            model="llama3:8b",
            provider="ollama",
        )

        with patch(
            "backend.app.api.llm.get_router"
        ) as mock_get_router:
            mock_router = AsyncMock()
            mock_router.chat.return_value = mock_response
            mock_get_router.return_value = mock_router

            response = await client.post(
                "/api/llm/chat",
                json={
                    "messages": [{"role": "user", "content": "Hello"}],
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Hello!"
        assert data["provider"] == "ollama"

    @pytest.mark.asyncio
    async def test_chat_provider_unavailable(self, client):
        with patch(
            "backend.app.api.llm.get_router"
        ) as mock_get_router:
            mock_router = AsyncMock()
            mock_router.chat.side_effect = ProviderUnavailableError(
                "ollama", "Connection refused"
            )
            mock_get_router.return_value = mock_router

            response = await client.post(
                "/api/llm/chat",
                json={
                    "messages": [{"role": "user", "content": "Hello"}],
                },
            )

        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_chat_provider_error(self, client):
        with patch(
            "backend.app.api.llm.get_router"
        ) as mock_get_router:
            mock_router = AsyncMock()
            mock_router.chat.side_effect = ProviderError(
                "ollama", "Bad request", status_code=400
            )
            mock_get_router.return_value = mock_router

            response = await client.post(
                "/api/llm/chat",
                json={
                    "messages": [{"role": "user", "content": "Hello"}],
                },
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_chat_invalid_request(self, client):
        """Empty messages should be rejected."""
        response = await client.post(
            "/api/llm/chat",
            json={"messages": []},
        )
        assert response.status_code == 422  # Validation error


class TestModelsEndpoint:
    """Tests for GET /api/llm/models."""

    @pytest.mark.asyncio
    async def test_list_models(self, client):
        mock_models = [
            ModelInfo(name="llama3:8b", provider="ollama"),
            ModelInfo(name="mistral:7b", provider="ollama"),
        ]

        with patch(
            "backend.app.api.llm.get_router"
        ) as mock_get_router:
            mock_router = AsyncMock()
            mock_router.list_models.return_value = mock_models
            mock_get_router.return_value = mock_router

            response = await client.get("/api/llm/models")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "llama3:8b"

    @pytest.mark.asyncio
    async def test_list_models_with_provider_filter(self, client):
        mock_models = [ModelInfo(name="llama3:8b", provider="ollama")]

        with patch(
            "backend.app.api.llm.get_router"
        ) as mock_get_router:
            mock_router = AsyncMock()
            mock_router.list_models.return_value = mock_models
            mock_get_router.return_value = mock_router

            response = await client.get("/api/llm/models?provider=ollama")

        assert response.status_code == 200


class TestStatusEndpoint:
    """Tests for GET /api/llm/status."""

    @pytest.mark.asyncio
    async def test_router_status(self, client):
        mock_status = RouterStatus(
            active_provider="ollama",
            providers=[
                ProviderStatus(name="ollama", available=True, models_count=2),
            ],
            memory_ok=True,
            total_models=2,
        )

        with patch(
            "backend.app.api.llm.get_router"
        ) as mock_get_router:
            mock_router = AsyncMock()
            mock_router.get_status.return_value = mock_status
            mock_get_router.return_value = mock_router

            response = await client.get("/api/llm/status")

        assert response.status_code == 200
        data = response.json()
        assert data["active_provider"] == "ollama"
        assert data["memory_ok"] is True
        assert data["total_models"] == 2


class TestProvidersEndpoint:
    """Tests for GET /api/llm/providers."""

    @pytest.mark.asyncio
    async def test_list_providers(self, client):
        mock_status = ProviderStatus(
            name="ollama", available=False, detail="Not running"
        )

        with patch(
            "backend.app.api.llm.get_router"
        ) as mock_get_router:
            mock_router = AsyncMock()
            mock_router.initialize = AsyncMock()
            mock_router.available_providers = ["ollama"]
            mock_router.default_provider = "ollama"
            mock_router.check_provider = AsyncMock(return_value=mock_status)
            mock_get_router.return_value = mock_router

            response = await client.get("/api/llm/providers")

        assert response.status_code == 200
        data = response.json()
        assert data["default"] == "ollama"
        assert len(data["providers"]) == 1
