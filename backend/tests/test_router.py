"""
Tests for LLM Router.

Tests:
- Router initialization
- Provider selection (default, override)
- Memory gating
- Model listing
- Status reporting
- Error handling (unavailable provider)
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.app.llm.base import ProviderError
from backend.app.llm.models import (
    ChatRequest,
    ChatResponse,
    Message,
    ModelInfo,
    ProviderStatus,
    Role,
)
from backend.app.llm.router import LLMRouter, get_router, reset_router


def _make_request(content: str = "Hello", provider: str | None = None) -> ChatRequest:
    return ChatRequest(
        messages=[Message(role=Role.USER, content=content)],
        provider=provider,
    )


class TestRouterInit:
    """Tests for router initialization."""

    @pytest.mark.asyncio
    async def test_initialize_creates_ollama(self):
        router = LLMRouter()
        await router.initialize()
        assert "ollama" in router.available_providers

    @pytest.mark.asyncio
    async def test_default_provider_is_ollama(self):
        router = LLMRouter()
        await router.initialize()
        assert router.default_provider == "ollama"

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self):
        router = LLMRouter()
        await router.initialize()
        await router.initialize()  # Should not fail
        assert "ollama" in router.available_providers

    @pytest.mark.asyncio
    async def test_openai_not_initialized_without_url(self):
        """OpenAI adapter should not be created without LLM_BASE_URL."""
        router = LLMRouter()
        await router.initialize()
        # Default config has empty LLM_BASE_URL
        assert "openai" not in router.available_providers

    @pytest.mark.asyncio
    async def test_anthropic_not_initialized_without_key(self):
        """Anthropic adapter should not be created without API key."""
        router = LLMRouter()
        await router.initialize()
        assert "anthropic" not in router.available_providers


class TestRouterProviderSelection:
    """Tests for provider selection logic."""

    @pytest.mark.asyncio
    async def test_get_default_adapter(self):
        router = LLMRouter()
        await router.initialize()
        adapter = router._get_adapter()
        assert adapter.provider_name == "ollama"

    @pytest.mark.asyncio
    async def test_get_specific_adapter(self):
        router = LLMRouter()
        await router.initialize()
        adapter = router._get_adapter("ollama")
        assert adapter.provider_name == "ollama"

    @pytest.mark.asyncio
    async def test_get_unavailable_adapter(self):
        router = LLMRouter()
        await router.initialize()
        with pytest.raises(ProviderError, match="not available"):
            router._get_adapter("nonexistent")


class TestRouterMemoryGating:
    """Tests for memory-based request gating."""

    @pytest.mark.asyncio
    async def test_chat_blocked_high_memory(self):
        """Should block chat when memory is critical."""
        router = LLMRouter()
        await router.initialize()

        mock_metrics = type("MockMetrics", (), {
            "heavy_model_allowed": False,
            "percent_used": 85.0,
            "available_gb": 2.0,
        })()

        with patch("backend.app.llm.router.get_memory_metrics", return_value=mock_metrics):
            with pytest.raises(ProviderError, match="Memory usage too high"):
                await router.chat(_make_request())

    @pytest.mark.asyncio
    async def test_chat_allowed_normal_memory(self):
        """Should allow chat when memory is normal (will fail at Ollama connect, but passes gating)."""
        router = LLMRouter()
        await router.initialize()

        mock_metrics = type("MockMetrics", (), {
            "heavy_model_allowed": True,
            "percent_used": 50.0,
            "available_gb": 8.0,
        })()

        mock_response = ChatResponse(
            content="Hello!",
            model="llama3:8b",
            provider="ollama",
        )

        with patch("backend.app.llm.router.get_memory_metrics", return_value=mock_metrics):
            with patch.object(
                router._adapters["ollama"], "chat", return_value=mock_response
            ):
                result = await router.chat(_make_request())
                assert result.content == "Hello!"


class TestRouterModelListing:
    """Tests for model listing through router."""

    @pytest.mark.asyncio
    async def test_list_models_single_provider(self):
        router = LLMRouter()
        await router.initialize()

        mock_models = [
            ModelInfo(name="llama3:8b", provider="ollama"),
            ModelInfo(name="mistral:7b", provider="ollama"),
        ]

        with patch.object(
            router._adapters["ollama"], "list_models", return_value=mock_models
        ):
            models = await router.list_models(provider="ollama")

        assert len(models) == 2

    @pytest.mark.asyncio
    async def test_list_all_models(self):
        router = LLMRouter()
        await router.initialize()

        mock_models = [
            ModelInfo(name="llama3:8b", provider="ollama"),
        ]

        with patch.object(
            router._adapters["ollama"], "list_models", return_value=mock_models
        ):
            models = await router.list_models()

        assert len(models) >= 1


class TestRouterStatus:
    """Tests for router status reporting."""

    @pytest.mark.asyncio
    async def test_get_status(self):
        router = LLMRouter()
        await router.initialize()

        mock_provider_status = ProviderStatus(
            name="ollama",
            available=False,
            detail="Not running",
        )

        with patch.object(
            router._adapters["ollama"],
            "check_availability",
            return_value=mock_provider_status,
        ):
            status = await router.get_status()

        assert status.active_provider == "ollama"
        assert len(status.providers) == 1
        assert isinstance(status.memory_ok, bool)

    @pytest.mark.asyncio
    async def test_check_provider(self):
        router = LLMRouter()
        await router.initialize()

        mock_status = ProviderStatus(
            name="ollama", available=True, models_count=2
        )

        with patch.object(
            router._adapters["ollama"],
            "check_availability",
            return_value=mock_status,
        ):
            status = await router.check_provider("ollama")
            assert status.available is True


class TestRouterSingleton:
    """Tests for router singleton management."""

    def test_get_router_returns_instance(self):
        reset_router()
        r1 = get_router()
        r2 = get_router()
        assert r1 is r2

    def test_reset_router_clears(self):
        reset_router()
        r1 = get_router()
        reset_router()
        r2 = get_router()
        assert r1 is not r2
