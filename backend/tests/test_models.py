"""
Tests for LLM data models.

Tests:
- Message creation and role validation
- ChatRequest validation (temperature, max_tokens, etc.)
- ChatResponse structure
- StreamChunk structure
- ModelInfo structure
- TokenUsage structure
- ProviderStatus / RouterStatus
"""

from __future__ import annotations

import pytest

from backend.app.llm.models import (
    ChatRequest,
    ChatResponse,
    Message,
    ModelInfo,
    ProviderStatus,
    Role,
    RouterStatus,
    StreamChunk,
    TokenUsage,
)


class TestRole:
    """Tests for Role enum."""

    def test_role_values(self):
        assert Role.SYSTEM == "system"
        assert Role.USER == "user"
        assert Role.ASSISTANT == "assistant"

    def test_role_from_string(self):
        assert Role("system") == Role.SYSTEM
        assert Role("user") == Role.USER


class TestMessage:
    """Tests for Message model."""

    def test_create_message(self):
        msg = Message(role=Role.USER, content="Hello")
        assert msg.role == Role.USER
        assert msg.content == "Hello"

    def test_create_system_message(self):
        msg = Message(role=Role.SYSTEM, content="You are helpful.")
        assert msg.role == Role.SYSTEM

    def test_message_serialization(self):
        msg = Message(role=Role.USER, content="test")
        data = msg.model_dump()
        assert data["role"] == "user"
        assert data["content"] == "test"


class TestChatRequest:
    """Tests for ChatRequest model."""

    def test_minimal_request(self):
        req = ChatRequest(
            messages=[Message(role=Role.USER, content="Hi")]
        )
        assert len(req.messages) == 1
        assert req.temperature == 0.7
        assert req.stream is False
        assert req.model is None
        assert req.provider is None

    def test_full_request(self):
        req = ChatRequest(
            messages=[
                Message(role=Role.SYSTEM, content="Be helpful"),
                Message(role=Role.USER, content="Hello"),
            ],
            model="llama3:8b",
            provider="ollama",
            temperature=0.5,
            max_tokens=1024,
            stream=True,
            top_p=0.9,
            stop=["END"],
        )
        assert req.model == "llama3:8b"
        assert req.provider == "ollama"
        assert req.temperature == 0.5
        assert req.max_tokens == 1024
        assert req.stream is True
        assert req.top_p == 0.9
        assert req.stop == ["END"]

    def test_empty_messages_rejected(self):
        with pytest.raises(Exception):
            ChatRequest(messages=[])

    def test_temperature_range(self):
        # Valid
        ChatRequest(
            messages=[Message(role=Role.USER, content="Hi")],
            temperature=0.0,
        )
        ChatRequest(
            messages=[Message(role=Role.USER, content="Hi")],
            temperature=2.0,
        )
        # Invalid
        with pytest.raises(Exception):
            ChatRequest(
                messages=[Message(role=Role.USER, content="Hi")],
                temperature=2.5,
            )

    def test_max_tokens_range(self):
        with pytest.raises(Exception):
            ChatRequest(
                messages=[Message(role=Role.USER, content="Hi")],
                max_tokens=0,
            )


class TestChatResponse:
    """Tests for ChatResponse model."""

    def test_create_response(self):
        resp = ChatResponse(
            content="Hello!",
            model="llama3:8b",
            provider="ollama",
        )
        assert resp.content == "Hello!"
        assert resp.model == "llama3:8b"
        assert resp.provider == "ollama"
        assert resp.usage is None
        assert resp.finish_reason is None

    def test_response_with_usage(self):
        resp = ChatResponse(
            content="Hi",
            model="gpt-4",
            provider="openai",
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            finish_reason="stop",
        )
        assert resp.usage.total_tokens == 15
        assert resp.finish_reason == "stop"


class TestStreamChunk:
    """Tests for StreamChunk model."""

    def test_default_chunk(self):
        chunk = StreamChunk()
        assert chunk.content == ""
        assert chunk.done is False

    def test_content_chunk(self):
        chunk = StreamChunk(
            content="Hello",
            model="llama3:8b",
            provider="ollama",
            done=False,
        )
        assert chunk.content == "Hello"

    def test_final_chunk(self):
        chunk = StreamChunk(done=True, finish_reason="stop")
        assert chunk.done is True
        assert chunk.finish_reason == "stop"


class TestTokenUsage:
    """Tests for TokenUsage model."""

    def test_create_usage(self):
        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )
        assert usage.prompt_tokens == 100
        assert usage.total_tokens == 150

    def test_optional_fields(self):
        usage = TokenUsage()
        assert usage.prompt_tokens is None
        assert usage.total_tokens is None


class TestModelInfo:
    """Tests for ModelInfo model."""

    def test_minimal_model_info(self):
        info = ModelInfo(name="llama3:8b", provider="ollama")
        assert info.name == "llama3:8b"
        assert info.loaded is False
        assert info.size_gb is None

    def test_full_model_info(self):
        info = ModelInfo(
            name="llama3:8b",
            provider="ollama",
            size_gb=5.0,
            parameters="8b",
            quantization="q4_0",
            family="llama",
            loaded=True,
        )
        assert info.size_gb == 5.0
        assert info.loaded is True


class TestProviderStatus:
    """Tests for ProviderStatus model."""

    def test_available_provider(self):
        status = ProviderStatus(
            name="ollama",
            available=True,
            models_count=3,
            default_model="llama3:8b",
        )
        assert status.available is True
        assert status.models_count == 3

    def test_unavailable_provider(self):
        status = ProviderStatus(
            name="openai",
            available=False,
            detail="No API key",
        )
        assert status.available is False


class TestRouterStatus:
    """Tests for RouterStatus model."""

    def test_router_status(self):
        status = RouterStatus(
            active_provider="ollama",
            providers=[
                ProviderStatus(name="ollama", available=True, models_count=2),
            ],
            memory_ok=True,
            total_models=2,
        )
        assert status.active_provider == "ollama"
        assert status.memory_ok is True
        assert status.total_models == 2
