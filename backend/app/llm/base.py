"""
Base LLM adapter — abstract interface all providers must implement.

Adapter pattern: each provider (Ollama, OpenAI, Anthropic) implements
this interface. The router dispatches to the correct adapter.
"""

from __future__ import annotations

import abc
from typing import AsyncIterator

from backend.app.llm.models import (
    ChatRequest,
    ChatResponse,
    ModelInfo,
    ProviderStatus,
    StreamChunk,
)


class BaseLLMAdapter(abc.ABC):
    """Abstract base class for LLM provider adapters."""

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'ollama', 'openai')."""
        ...

    @abc.abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Send a chat completion request and return the full response.

        Args:
            request: Universal chat request.

        Returns:
            Universal chat response.

        Raises:
            ProviderError: If the provider returns an error.
            ConnectionError: If the provider is unreachable.
        """
        ...

    @abc.abstractmethod
    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        """
        Send a streaming chat completion request.

        Args:
            request: Universal chat request (stream=True).

        Yields:
            StreamChunk objects as they arrive.

        Raises:
            ProviderError: If the provider returns an error.
            ConnectionError: If the provider is unreachable.
        """
        ...
        # Make this an async generator
        yield  # pragma: no cover

    @abc.abstractmethod
    async def list_models(self) -> list[ModelInfo]:
        """
        List available models from this provider.

        Returns:
            List of ModelInfo objects.
        """
        ...

    @abc.abstractmethod
    async def check_availability(self) -> ProviderStatus:
        """
        Check if the provider is available and return status.

        Returns:
            ProviderStatus with availability info.
        """
        ...

    async def get_default_model(self) -> str | None:
        """
        Get the default model for this provider.

        Can be overridden by subclasses. Returns None by default.
        """
        return None


class ProviderError(Exception):
    """Raised when a provider returns an error."""

    def __init__(self, provider: str, message: str, status_code: int | None = None):
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}")


class ProviderUnavailableError(ProviderError):
    """Raised when a provider is unreachable."""

    def __init__(self, provider: str, detail: str = ""):
        super().__init__(
            provider=provider,
            message=f"Provider unavailable: {detail}" if detail else "Provider unavailable",
        )
