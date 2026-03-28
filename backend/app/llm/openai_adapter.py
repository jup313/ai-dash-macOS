"""
OpenAI-compatible adapter — supports any OpenAI API-compatible provider.

Works with: OpenAI, LM Studio, vLLM, LocalAI, text-generation-webui,
and any other OpenAI-compatible endpoint.
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


class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI-compatible API adapter."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ):
        settings = get_settings()
        self._base_url = (base_url or settings.llm_base_url).rstrip("/")
        self._api_key = api_key or settings.llm_api_key
        self._default_model = model or settings.llm_model or "gpt-3.5-turbo"
        self._timeout = timeout or float(settings.request_timeout_seconds)

    @property
    def provider_name(self) -> str:
        return "openai"

    async def get_default_model(self) -> str:
        return self._default_model

    def _headers(self) -> dict[str, str]:
        """Build request headers."""
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Send chat request to OpenAI-compatible endpoint."""
        model = request.model or self._default_model
        payload = self._build_payload(request, model, stream=False)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/v1/chat/completions",
                    json=payload,
                    headers=self._headers(),
                )
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError("openai", str(exc)) from exc
        except httpx.TimeoutException as exc:
            raise ProviderError("openai", f"Request timed out: {exc}") from exc

        if response.status_code != 200:
            raise ProviderError(
                "openai",
                f"HTTP {response.status_code}: {response.text}",
                status_code=response.status_code,
            )

        data = response.json()
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})

        return ChatResponse(
            content=message.get("content", ""),
            model=data.get("model", model),
            provider="openai",
            usage=self._parse_usage(data),
            finish_reason=choice.get("finish_reason"),
        )

    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        """Stream chat response from OpenAI-compatible endpoint."""
        model = request.model or self._default_model
        payload = self._build_payload(request, model, stream=True)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/v1/chat/completions",
                    json=payload,
                    headers=self._headers(),
                ) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        raise ProviderError(
                            "openai",
                            f"HTTP {response.status_code}: {body.decode()}",
                            status_code=response.status_code,
                        )

                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        if not line.startswith("data: "):
                            continue

                        data_str = line[6:]  # Remove "data: " prefix
                        if data_str == "[DONE]":
                            yield StreamChunk(
                                content="",
                                model=model,
                                provider="openai",
                                done=True,
                                finish_reason="stop",
                            )
                            return

                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        choice = data.get("choices", [{}])[0]
                        delta = choice.get("delta", {})
                        finish_reason = choice.get("finish_reason")

                        yield StreamChunk(
                            content=delta.get("content", ""),
                            model=data.get("model", model),
                            provider="openai",
                            done=finish_reason is not None,
                            finish_reason=finish_reason,
                        )

        except httpx.ConnectError as exc:
            raise ProviderUnavailableError("openai", str(exc)) from exc
        except httpx.TimeoutException as exc:
            raise ProviderError("openai", f"Stream timed out: {exc}") from exc

    async def list_models(self) -> list[ModelInfo]:
        """List models from OpenAI-compatible endpoint."""
        if not self._base_url:
            return []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self._base_url}/v1/models",
                    headers=self._headers(),
                )
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.warning("Cannot list OpenAI models: %s", exc)
            return []

        if response.status_code != 200:
            logger.warning("OpenAI /v1/models returned %d", response.status_code)
            return []

        data = response.json()
        return [
            ModelInfo(
                name=m.get("id", "unknown"),
                provider="openai",
            )
            for m in data.get("data", [])
        ]

    async def check_availability(self) -> ProviderStatus:
        """Check OpenAI-compatible endpoint availability."""
        if not self._base_url:
            return ProviderStatus(
                name="openai",
                available=False,
                detail="No base URL configured",
            )

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self._base_url}/v1/models",
                    headers=self._headers(),
                )
            if response.status_code == 200:
                data = response.json()
                model_count = len(data.get("data", []))
                return ProviderStatus(
                    name="openai",
                    available=True,
                    models_count=model_count,
                    default_model=self._default_model,
                )
            return ProviderStatus(
                name="openai",
                available=False,
                detail=f"HTTP {response.status_code}",
            )
        except Exception as exc:
            return ProviderStatus(
                name="openai",
                available=False,
                detail=str(exc),
            )

    def _build_payload(self, request: ChatRequest, model: str, stream: bool) -> dict:
        """Build OpenAI-compatible API payload."""
        messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in request.messages
        ]

        payload: dict = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": stream,
        }

        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        if request.stop is not None:
            payload["stop"] = request.stop

        return payload

    def _parse_usage(self, data: dict) -> TokenUsage | None:
        """Parse token usage from OpenAI response."""
        usage = data.get("usage")
        if usage:
            return TokenUsage(
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
            )
        return None
