"""
Tests for LLM provider adapters.

Tests:
- OllamaAdapter: chat, list_models, check_availability
- OpenAIAdapter: chat, check_availability
- AnthropicAdapter: preconditions, check_availability
- ProviderError / ProviderUnavailableError
- All with mocked HTTP responses (no real API calls)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from backend.app.llm.base import ProviderError, ProviderUnavailableError
from backend.app.llm.models import ChatRequest, Message, Role
from backend.app.llm.ollama import OllamaAdapter
from backend.app.llm.openai_adapter import OpenAIAdapter
from backend.app.llm.anthropic_adapter import AnthropicAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(content: str = "Hello") -> ChatRequest:
    """Create a simple test ChatRequest."""
    return ChatRequest(
        messages=[Message(role=Role.USER, content=content)]
    )


def _ollama_chat_response() -> dict:
    """Mock Ollama /api/chat response."""
    return {
        "model": "llama3:8b",
        "message": {"role": "assistant", "content": "Hi there!"},
        "done": True,
        "prompt_eval_count": 10,
        "eval_count": 5,
    }


def _ollama_tags_response() -> dict:
    """Mock Ollama /api/tags response."""
    return {
        "models": [
            {
                "name": "llama3:8b",
                "size": 5368709120,
                "details": {
                    "parameter_size": "8B",
                    "quantization_level": "Q4_0",
                    "family": "llama",
                },
            },
            {
                "name": "mistral:7b",
                "size": 4294967296,
                "details": {
                    "parameter_size": "7B",
                    "family": "mistral",
                },
            },
        ]
    }


def _openai_chat_response() -> dict:
    """Mock OpenAI /v1/chat/completions response."""
    return {
        "id": "chatcmpl-test",
        "model": "gpt-3.5-turbo",
        "choices": [
            {
                "message": {"role": "assistant", "content": "Hello!"},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }


# ---------------------------------------------------------------------------
# ProviderError Tests
# ---------------------------------------------------------------------------

class TestProviderErrors:
    """Tests for error types."""

    def test_provider_error_message(self):
        err = ProviderError("ollama", "Something failed")
        assert "ollama" in str(err)
        assert "Something failed" in str(err)
        assert err.provider == "ollama"

    def test_provider_error_with_status(self):
        err = ProviderError("openai", "Not found", status_code=404)
        assert err.status_code == 404

    def test_provider_unavailable(self):
        err = ProviderUnavailableError("ollama", "Connection refused")
        assert "unavailable" in str(err).lower()
        assert err.provider == "ollama"


# ---------------------------------------------------------------------------
# Ollama Adapter Tests
# ---------------------------------------------------------------------------

class TestOllamaAdapter:
    """Tests for OllamaAdapter."""

    def test_provider_name(self):
        adapter = OllamaAdapter()
        assert adapter.provider_name == "ollama"

    @pytest.mark.asyncio
    async def test_chat_success(self):
        adapter = OllamaAdapter()
        mock_response = httpx.Response(200, json=_ollama_chat_response())

        async def mock_post(*args, **kwargs):
            return mock_response

        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            response = await adapter.chat(_make_request())

        assert response.content == "Hi there!"
        assert response.provider == "ollama"
        assert response.model == "llama3:8b"
        assert response.usage is not None
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 5

    @pytest.mark.asyncio
    async def test_chat_connection_error(self):
        adapter = OllamaAdapter()

        async def mock_post(*args, **kwargs):
            raise httpx.ConnectError("Connection refused")

        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            with pytest.raises(ProviderUnavailableError):
                await adapter.chat(_make_request())

    @pytest.mark.asyncio
    async def test_chat_timeout(self):
        adapter = OllamaAdapter()

        async def mock_post(*args, **kwargs):
            raise httpx.ReadTimeout("Timed out")

        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            with pytest.raises(ProviderError):
                await adapter.chat(_make_request())

    @pytest.mark.asyncio
    async def test_chat_http_error(self):
        adapter = OllamaAdapter()
        mock_response = httpx.Response(500, text="Internal error")

        async def mock_post(*args, **kwargs):
            return mock_response

        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            with pytest.raises(ProviderError) as exc_info:
                await adapter.chat(_make_request())
            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_list_models(self):
        adapter = OllamaAdapter()
        mock_response = httpx.Response(200, json=_ollama_tags_response())

        async def mock_get(*args, **kwargs):
            return mock_response

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            models = await adapter.list_models()

        assert len(models) == 2
        assert models[0].name == "llama3:8b"
        assert models[0].provider == "ollama"
        assert models[0].family == "llama"
        assert models[1].name == "mistral:7b"

    @pytest.mark.asyncio
    async def test_list_models_connection_error(self):
        adapter = OllamaAdapter()

        async def mock_get(*args, **kwargs):
            raise httpx.ConnectError("Connection refused")

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            models = await adapter.list_models()

        assert models == []

    @pytest.mark.asyncio
    async def test_check_availability_success(self):
        adapter = OllamaAdapter()
        mock_response = httpx.Response(200, json=_ollama_tags_response())

        async def mock_get(*args, **kwargs):
            return mock_response

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            status = await adapter.check_availability()

        assert status.available is True
        assert status.name == "ollama"
        assert status.models_count == 2

    @pytest.mark.asyncio
    async def test_check_availability_failure(self):
        adapter = OllamaAdapter()

        async def mock_get(*args, **kwargs):
            raise httpx.ConnectError("Connection refused")

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            status = await adapter.check_availability()

        assert status.available is False

    @pytest.mark.asyncio
    async def test_get_default_model(self):
        adapter = OllamaAdapter()
        model = await adapter.get_default_model()
        assert model == "llama3:8b"

    def test_build_payload(self):
        adapter = OllamaAdapter()
        request = ChatRequest(
            messages=[Message(role=Role.USER, content="Hi")],
            temperature=0.5,
            max_tokens=100,
            stop=["END"],
        )
        payload = adapter._build_payload(request, "llama3:8b", stream=False)

        assert payload["model"] == "llama3:8b"
        assert payload["stream"] is False
        assert payload["options"]["temperature"] == 0.5
        assert payload["options"]["num_predict"] == 100
        assert payload["options"]["stop"] == ["END"]

    def test_parse_usage(self):
        adapter = OllamaAdapter()
        usage = adapter._parse_usage({
            "prompt_eval_count": 20,
            "eval_count": 10,
        })
        assert usage is not None
        assert usage.prompt_tokens == 20
        assert usage.completion_tokens == 10
        assert usage.total_tokens == 30

    def test_parse_usage_none(self):
        adapter = OllamaAdapter()
        usage = adapter._parse_usage({})
        assert usage is None


# ---------------------------------------------------------------------------
# OpenAI Adapter Tests
# ---------------------------------------------------------------------------

class TestOpenAIAdapter:
    """Tests for OpenAIAdapter."""

    def test_provider_name(self):
        adapter = OpenAIAdapter(base_url="http://localhost:1234")
        assert adapter.provider_name == "openai"

    @pytest.mark.asyncio
    async def test_chat_success(self):
        adapter = OpenAIAdapter(
            base_url="http://localhost:1234",
            api_key="test-key",
        )
        mock_response = httpx.Response(200, json=_openai_chat_response())

        async def mock_post(*args, **kwargs):
            return mock_response

        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            response = await adapter.chat(_make_request())

        assert response.content == "Hello!"
        assert response.provider == "openai"
        assert response.usage.total_tokens == 15

    @pytest.mark.asyncio
    async def test_chat_connection_error(self):
        adapter = OpenAIAdapter(base_url="http://localhost:1234")

        async def mock_post(*args, **kwargs):
            raise httpx.ConnectError("Connection refused")

        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            with pytest.raises(ProviderUnavailableError):
                await adapter.chat(_make_request())

    @pytest.mark.asyncio
    async def test_check_availability_no_url(self):
        adapter = OpenAIAdapter(base_url="")
        status = await adapter.check_availability()
        assert status.available is False
        assert "No base URL" in (status.detail or "")

    @pytest.mark.asyncio
    async def test_check_availability_success(self):
        adapter = OpenAIAdapter(base_url="http://localhost:1234")
        mock_response = httpx.Response(200, json={
            "data": [{"id": "gpt-3.5-turbo"}, {"id": "gpt-4"}]
        })

        async def mock_get(*args, **kwargs):
            return mock_response

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            status = await adapter.check_availability()

        assert status.available is True
        assert status.models_count == 2

    @pytest.mark.asyncio
    async def test_list_models_no_url(self):
        adapter = OpenAIAdapter(base_url="")
        models = await adapter.list_models()
        assert models == []

    def test_headers_with_key(self):
        adapter = OpenAIAdapter(
            base_url="http://localhost:1234",
            api_key="sk-test123",
        )
        headers = adapter._headers()
        assert headers["Authorization"] == "Bearer sk-test123"

    def test_headers_without_key(self):
        adapter = OpenAIAdapter(base_url="http://localhost:1234", api_key="")
        headers = adapter._headers()
        assert "Authorization" not in headers

    def test_build_payload(self):
        adapter = OpenAIAdapter(base_url="http://localhost:1234")
        request = ChatRequest(
            messages=[Message(role=Role.USER, content="Hi")],
            temperature=0.8,
            max_tokens=200,
        )
        payload = adapter._build_payload(request, "gpt-4", stream=False)

        assert payload["model"] == "gpt-4"
        assert payload["temperature"] == 0.8
        assert payload["max_tokens"] == 200
        assert payload["stream"] is False


# ---------------------------------------------------------------------------
# Anthropic Adapter Tests
# ---------------------------------------------------------------------------

class TestAnthropicAdapter:
    """Tests for AnthropicAdapter."""

    def test_provider_name(self):
        adapter = AnthropicAdapter()
        assert adapter.provider_name == "anthropic"

    @pytest.mark.asyncio
    async def test_chat_blocked_remote_disabled(self):
        """Should raise error when remote models are disabled."""
        adapter = AnthropicAdapter()
        adapter._allow_remote = False

        with pytest.raises(ProviderError, match="Remote models disabled"):
            await adapter.chat(_make_request())

    @pytest.mark.asyncio
    async def test_chat_blocked_no_key(self):
        """Should raise error when API key is missing."""
        adapter = AnthropicAdapter()
        adapter._allow_remote = True
        adapter._api_key = ""

        with pytest.raises(ProviderError, match="ANTHROPIC_API_KEY"):
            await adapter.chat(_make_request())

    @pytest.mark.asyncio
    async def test_check_availability_remote_disabled(self):
        adapter = AnthropicAdapter()
        adapter._allow_remote = False
        status = await adapter.check_availability()
        assert status.available is False
        assert "Remote models disabled" in (status.detail or "")

    @pytest.mark.asyncio
    async def test_check_availability_no_key(self):
        adapter = AnthropicAdapter()
        adapter._allow_remote = True
        adapter._api_key = ""
        status = await adapter.check_availability()
        assert status.available is False
        assert "API key" in (status.detail or "")

    @pytest.mark.asyncio
    async def test_list_models_disabled(self):
        adapter = AnthropicAdapter()
        adapter._allow_remote = False
        models = await adapter.list_models()
        assert models == []

    @pytest.mark.asyncio
    async def test_list_models_enabled(self):
        adapter = AnthropicAdapter()
        adapter._allow_remote = True
        adapter._api_key = "test-key"
        models = await adapter.list_models()
        assert len(models) > 0
        assert all(m.provider == "anthropic" for m in models)

    def test_build_payload_separates_system(self):
        adapter = AnthropicAdapter()
        request = ChatRequest(
            messages=[
                Message(role=Role.SYSTEM, content="Be helpful"),
                Message(role=Role.USER, content="Hello"),
            ],
            max_tokens=1024,
        )
        payload = adapter._build_payload(request, "claude-3-haiku-20240307", stream=False)

        assert payload["system"] == "Be helpful"
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["role"] == "user"
        assert payload["max_tokens"] == 1024

    def test_build_payload_ensures_user_first(self):
        adapter = AnthropicAdapter()
        request = ChatRequest(
            messages=[
                Message(role=Role.ASSISTANT, content="Previous response"),
            ],
        )
        payload = adapter._build_payload(request, "claude-3-haiku-20240307", stream=False)

        # Should prepend a user message
        assert payload["messages"][0]["role"] == "user"

    def test_parse_usage(self):
        adapter = AnthropicAdapter()
        usage = adapter._parse_usage({
            "usage": {"input_tokens": 15, "output_tokens": 8}
        })
        assert usage is not None
        assert usage.prompt_tokens == 15
        assert usage.completion_tokens == 8
        assert usage.total_tokens == 23
