"""
LLM module — providers, router, and adapters.

Provides:
- Universal LLM Router (dispatches to provider adapters)
- Provider adapters: Ollama, OpenAI-compatible, Anthropic
- Data models for requests/responses
- Streaming utilities (SSE)
"""

from backend.app.llm.base import BaseLLMAdapter, ProviderError, ProviderUnavailableError
from backend.app.llm.models import (
    ChatRequest,
    ChatResponse,
    ModelInfo,
    ProviderStatus,
    Role,
    RouterStatus,
    StreamChunk,
    TokenUsage,
)
from backend.app.llm.router import LLMRouter, get_router, reset_router

__all__ = [
    "BaseLLMAdapter",
    "ChatRequest",
    "ChatResponse",
    "LLMRouter",
    "ModelInfo",
    "ProviderError",
    "ProviderStatus",
    "ProviderUnavailableError",
    "Role",
    "RouterStatus",
    "StreamChunk",
    "TokenUsage",
    "get_router",
    "reset_router",
]
