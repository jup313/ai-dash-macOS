"""
Anthropic adapter — optional Claude integration.

Requires ANTHROPIC_API_KEY and ALLOW_REMOTE_MODELS=true.
Uses Anthropic Messages API (v1).
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

ANTHROPIC_API_URL = "https://api.anthropic.com"
ANTHROPIC_API_VERSION = "2023-06-01"

# Known Anthropic models (static since there's no list endpoint)
ANTHROPIC_MODELS = [
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
    "claude-3-5-sonnet-20241022",
]


class AnthropicAdapter(BaseLLMAdapter):
    """Anthropic Claude API adapter."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ):
        settings = get_settings()
        self._api_key = api_key or settings.anthropic_api_key
        self._default_model = model or "claude-3-haiku-20240307"
        self._timeout = timeout or float(settings.request_timeout_seconds)
        self._allow_remote = settings.allow_remote_models

    @property
    def provider_name(self) -> str:
        return "anthropic"

    async def get_default_model(self) -> str:
        return self._default_model

    def _headers(self) -> dict[str, str]:
        """Build Anthropic API headers."""
        return {
            "Content-Type": "application/json",
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_API_VERSION,
        }

    def _check_preconditions(self) -> None:
        """Check that Anthropic is properly configured."""
        if not self._allow_remote:
            raise ProviderError(
                "anthropic",
                "Remote models disabled. Set ALLOW_REMOTE_MODELS=true",
            )
        if not self._api_key:
            raise ProviderError(
                "anthropic",
                "ANTHROPIC_API_KEY not configured",
            )

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Send chat request to Anthropic Messages API."""
        self._check_preconditions()
        model = request.model or self._default_model
        payload = self._build_payload(request, model, stream=False)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{ANTHROPIC_API_URL}/v1/messages",
                    json=payload,
                    headers=self._headers(),
                )
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError("anthropic", str(exc)) from exc
        except httpx.TimeoutException as exc:
            raise ProviderError("anthropic", f"Request timed out: {exc}") from exc

        if response.status_code != 200:
            raise ProviderError(
                "anthropic",
                f"HTTP {response.status_code}: {response.text}",
                status_code=response.status_code,
            )

        data = response.json()
        content_blocks = data.get("content", [])
        text = "".join(
            block.get("text", "") for block in content_blocks if block.get("type") == "text"
        )

        return ChatResponse(
            content=text,
            model=data.get("model", model),
            provider="anthropic",
            usage=self._parse_usage(data),
            finish_reason=data.get("stop_reason"),
        )

    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        """Stream chat response from Anthropic."""
        self._check_preconditions()
        model = request.model or self._default_model
        payload = self._build_payload(request, model, stream=True)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST",
                    f"{ANTHROPIC_API_URL}/v1/messages",
                    json=payload,
                    headers=self._headers(),
                ) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        raise ProviderError(
                            "anthropic",
                            f"HTTP {response.status_code}: {body.decode()}",
                            status_code=response.status_code,
                        )

                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line or not line.startswith("data: "):
                            continue

                        data_str = line[6:]
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        event_type = data.get("type", "")

                        if event_type == "content_block_delta":
                            delta = data.get("delta", {})
                            yield StreamChunk(
                                content=delta.get("text", ""),
                                model=model,
                                provider="anthropic",
                                done=False,
                            )

                        elif event_type == "message_stop":
                            yield StreamChunk(
                                content="",
                                model=model,
                                provider="anthropic",
                                done=True,
                                finish_reason="stop",
                            )
                            return

        except httpx.ConnectError as exc:
            raise ProviderUnavailableError("anthropic", str(exc)) from exc
        except httpx.TimeoutException as exc:
            raise ProviderError("anthropic", f"Stream timed out: {exc}") from exc

    async def list_models(self) -> list[ModelInfo]:
        """Return known Anthropic models (static list)."""
        if not self._api_key or not self._allow_remote:
            return []
        return [
            ModelInfo(name=name, provider="anthropic")
            for name in ANTHROPIC_MODELS
        ]

    async def check_availability(self) -> ProviderStatus:
        """Check Anthropic API availability."""
        if not self._allow_remote:
            return ProviderStatus(
                name="anthropic",
                available=False,
                detail="Remote models disabled",
            )
        if not self._api_key:
            return ProviderStatus(
                name="anthropic",
                available=False,
                detail="API key not configured",
            )

        # Lightweight check — just verify we can reach the API
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Use a minimal request to check auth
                response = await client.get(
                    f"{ANTHROPIC_API_URL}/v1/models",
                    headers=self._headers(),
                )
            # Even 404 means the API is reachable
            return ProviderStatus(
                name="anthropic",
                available=True,
                models_count=len(ANTHROPIC_MODELS),
                default_model=self._default_model,
            )
        except Exception as exc:
            return ProviderStatus(
                name="anthropic",
                available=False,
                detail=str(exc),
            )

    def _build_payload(self, request: ChatRequest, model: str, stream: bool) -> dict:
        """Build Anthropic Messages API payload."""
        # Anthropic separates system from messages
        system_prompt = ""
        messages = []
        for msg in request.messages:
            if msg.role.value == "system":
                system_prompt = msg.content
            else:
                messages.append({
                    "role": msg.role.value,
                    "content": msg.content,
                })

        # Ensure messages alternate and start with user
        if not messages or messages[0]["role"] != "user":
            messages.insert(0, {"role": "user", "content": "(continue)"})

        payload: dict = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens or 4096,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": stream,
        }

        if system_prompt:
            payload["system"] = system_prompt

        if request.stop:
            payload["stop_sequences"] = request.stop

        return payload

    def _parse_usage(self, data: dict) -> TokenUsage | None:
        """Parse token usage from Anthropic response."""
        usage = data.get("usage")
        if usage:
            input_tokens = usage.get("input_tokens")
            output_tokens = usage.get("output_tokens")
            total = (input_tokens or 0) + (output_tokens or 0)
            return TokenUsage(
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                total_tokens=total,
            )
        return None
