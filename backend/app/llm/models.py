"""
LLM data models — request/response schemas for all providers.

Provider-agnostic data structures used across the router and adapters.
No provider-specific logic here — pure data definitions.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Role(str, Enum):
    """Chat message roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    """A single chat message."""

    role: Role
    content: str


class ChatRequest(BaseModel):
    """Universal chat completion request."""

    messages: list[Message] = Field(
        ...,
        min_length=1,
        description="Conversation messages",
    )
    model: Optional[str] = Field(
        default=None,
        description="Model override (uses provider default if None)",
    )
    provider: Optional[str] = Field(
        default=None,
        description="Provider override (uses configured default if None)",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        le=32768,
        description="Maximum tokens to generate",
    )
    stream: bool = Field(
        default=False,
        description="Enable streaming response",
    )
    top_p: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter",
    )
    stop: Optional[list[str]] = Field(
        default=None,
        description="Stop sequences",
    )


class TokenUsage(BaseModel):
    """Token usage statistics."""

    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class ChatResponse(BaseModel):
    """Universal chat completion response."""

    content: str = Field(
        ...,
        description="Generated text content",
    )
    model: str = Field(
        ...,
        description="Model that generated the response",
    )
    provider: str = Field(
        ...,
        description="Provider that served the request",
    )
    usage: Optional[TokenUsage] = Field(
        default=None,
        description="Token usage statistics",
    )
    finish_reason: Optional[str] = Field(
        default=None,
        description="Reason generation stopped",
    )


class StreamChunk(BaseModel):
    """A single chunk in a streaming response."""

    content: str = ""
    model: str = ""
    provider: str = ""
    done: bool = False
    finish_reason: Optional[str] = None


class ModelInfo(BaseModel):
    """Information about an available model."""

    name: str = Field(
        ...,
        description="Model identifier",
    )
    provider: str = Field(
        ...,
        description="Provider name",
    )
    size_gb: Optional[float] = Field(
        default=None,
        description="Model size in GB (estimated)",
    )
    parameters: Optional[str] = Field(
        default=None,
        description="Parameter count (e.g., '7b', '13b')",
    )
    quantization: Optional[str] = Field(
        default=None,
        description="Quantization level (e.g., 'q4_0', 'q8_0')",
    )
    family: Optional[str] = Field(
        default=None,
        description="Model family (e.g., 'llama', 'mistral')",
    )
    loaded: bool = Field(
        default=False,
        description="Whether model is currently loaded in memory",
    )


class ProviderStatus(BaseModel):
    """Status of an LLM provider."""

    name: str
    available: bool
    models_count: int = 0
    default_model: str = ""
    detail: Optional[str] = None


class RouterStatus(BaseModel):
    """Overall router status."""

    active_provider: str
    providers: list[ProviderStatus]
    memory_ok: bool
    total_models: int


class LLMConfigUpdate(BaseModel):
    """Request to update LLM configuration at runtime."""

    provider: Optional[str] = Field(
        default=None,
        description="Switch active provider (ollama, openai, anthropic)",
    )
    model: Optional[str] = Field(
        default=None,
        description="Set default model for the active provider",
    )


class LLMConfig(BaseModel):
    """Current LLM configuration."""

    active_provider: str
    ollama_model: str
    openai_model: str
    available_providers: list[str]
