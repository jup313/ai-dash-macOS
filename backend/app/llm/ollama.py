"""
Ollama adapter — local LLM provider via Ollama REST API.

Default provider. Connects to localhost:11434.
Supports chat completion, streaming, and model listing.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

import httpx

from backend.app.core.config import get_settings
from backend.app.llm.base import BaseLLMAdapter, ProviderError, ProviderUnavailableError
from backend.app.llm.models import (
    ChatRequest,
    ChatResponse,
    ModelInfo,
    ProviderStatus,
    StreamChunk,
    TokenUsage,
)

logger = logging.getLogger(__name__)


class OllamaAdapter(BaseLLMAdapter):
    """Ollama local LLM adapter."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        settings = get_settings()
        self._base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._timeout = timeout or float(settings.request_timeout_seconds)
        self._default_model = settings.ollama_model

    @property
    def provider_name(self) -> str:
        return "ollama"

    async def get_default_model(self) -> str:
        return self._default_model

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Send chat request to Ollama /api/chat endpoint."""
        model = request.model or self._default_model
        payload = self._build_payload(request, model, stream=False)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/api/chat",
                    json=payload,
                )
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError("ollama", str(exc)) from exc
        except httpx.TimeoutException as exc:
            raise ProviderError("ollama", f"Request timed out: {exc}") from exc

        if response.status_code != 200:
            raise ProviderError(
                "ollama",
                f"HTTP {response.status_code}: {response.text}",
                status_code=response.status_code,
            )

        data = response.json()
        message = data.get("message", {})

        return ChatResponse(
            content=message.get("content", ""),
            model=data.get("model", model),
            provider="ollama",
            usage=self._parse_usage(data),
            finish_reason="stop" if data.get("done") else None,
        )

    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        """Stream chat response from Ollama."""
        model = request.model or self._default_model
        payload = self._build_payload(request, model, stream=True)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/api/chat",
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        raise ProviderError(
                            "ollama",
                            f"HTTP {response.status_code}: {body.decode()}",
                            status_code=response.status_code,
                        )

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        message = data.get("message", {})
                        done = data.get("done", False)

                        yield StreamChunk(
                            content=message.get("content", ""),
                            model=data.get("model", model),
                            provider="ollama",
                            done=done,
                            finish_reason="stop" if done else None,
                        )

                        if done:
                            return

        except httpx.ConnectError as exc:
            raise ProviderUnavailableError("ollama", str(exc)) from exc
        except httpx.TimeoutException as exc:
            raise ProviderError("ollama", f"Stream timed out: {exc}") from exc

    async def list_models(self) -> list[ModelInfo]:
        """List models available in Ollama."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.warning("Cannot list Ollama models: %s", exc)
            return []

        if response.status_code != 200:
            logger.warning("Ollama /api/tags returned %d", response.status_code)
            return []

        data = response.json()
        models = []
        for m in data.get("models", []):
            details = m.get("details", {})
            size_bytes = m.get("size", 0)
            models.append(
                ModelInfo(
                    name=m.get("name", "unknown"),
                    provider="ollama",
                    size_gb=round(size_bytes / (1024**3), 2) if size_bytes else None,
                    parameters=details.get("parameter_size"),
                    quantization=details.get("quantization_level"),
                    family=details.get("family"),
                )
            )
        return models

    async def check_availability(self) -> ProviderStatus:
        """Check Ollama reachability."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                model_count = len(data.get("models", []))
                return ProviderStatus(
                    name="ollama",
                    available=True,
                    models_count=model_count,
                    default_model=self._default_model,
                )
            return ProviderStatus(
                name="ollama",
                available=False,
                detail=f"HTTP {response.status_code}",
            )
        except Exception as exc:
            return ProviderStatus(
                name="ollama",
                available=False,
                detail=str(exc),
            )

    def _build_payload(self, request: ChatRequest, model: str, stream: bool) -> dict:
        """Build Ollama API request payload."""
        messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in request.messages
        ]

        payload: dict = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": request.temperature,
                "top_p": request.top_p,
            },
        }

        if request.max_tokens is not None:
            payload["options"]["num_predict"] = request.max_tokens

        if request.stop is not None:
            payload["options"]["stop"] = request.stop

        return payload

    def _parse_usage(self, data: dict) -> TokenUsage | None:
        """Parse token usage from Ollama response."""
        prompt_tokens = data.get("prompt_eval_count")
        completion_tokens = data.get("eval_count")
        if prompt_tokens is not None or completion_tokens is not None:
            total = (prompt_tokens or 0) + (completion_tokens or 0)
            return TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total,
            )
        return None
