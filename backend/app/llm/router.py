"""
LLM Router — dispatches requests to the correct provider adapter.

Central hub for all LLM operations. Manages provider lifecycle,
model listing, and request routing with memory-aware gating.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

from backend.app.core.config import get_settings
from backend.app.core.memory import get_memory_metrics
from backend.app.llm.anthropic_adapter import AnthropicAdapter
from backend.app.llm.base import BaseLLMAdapter, ProviderError, ProviderUnavailableError
from backend.app.llm.models import (
    ChatRequest,
    ChatResponse,
    LLMConfig,
    LLMConfigUpdate,
    ModelInfo,
    ProviderStatus,
    RouterStatus,
    StreamChunk,
)
from backend.app.llm.ollama import OllamaAdapter
from backend.app.llm.openai_adapter import OpenAIAdapter

logger = logging.getLogger(__name__)

# Provider registry — maps provider name to adapter class
PROVIDER_REGISTRY: dict[str, type[BaseLLMAdapter]] = {
    "ollama": OllamaAdapter,
    "openai": OpenAIAdapter,
    "anthropic": AnthropicAdapter,
}


class LLMRouter:
    """
    Central LLM request router.

    Routes requests to the appropriate provider adapter based on
    configuration or per-request overrides. Manages provider instances
    and performs memory gating.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, BaseLLMAdapter] = {}
        self._default_provider: str = ""
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the router with configured providers."""
        if self._initialized:
            return

        settings = get_settings()
        self._default_provider = settings.llm_provider

        # Always initialize Ollama (local default)
        self._adapters["ollama"] = OllamaAdapter()

        # Initialize OpenAI if configured
        if settings.llm_base_url:
            self._adapters["openai"] = OpenAIAdapter()

        # Initialize Anthropic if configured
        if settings.anthropic_api_key and settings.allow_remote_models:
            self._adapters["anthropic"] = AnthropicAdapter()

        self._initialized = True
        logger.info(
            "LLM Router initialized: default=%s, providers=%s",
            self._default_provider,
            list(self._adapters.keys()),
        )

    def _get_adapter(self, provider: str | None = None) -> BaseLLMAdapter:
        """
        Get the adapter for the specified or default provider.

        Args:
            provider: Provider name override, or None for default.

        Returns:
            The provider adapter.

        Raises:
            ProviderError: If provider is not available.
        """
        name = provider or self._default_provider

        adapter = self._adapters.get(name)
        if adapter is None:
            available = list(self._adapters.keys())
            raise ProviderError(
                name,
                f"Provider '{name}' not available. Available: {available}",
            )
        return adapter

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Route a chat request to the appropriate provider.

        Memory-gated: checks memory before processing.

        Args:
            request: Universal chat request.

        Returns:
            Universal chat response.
        """
        await self.initialize()

        # Memory check
        metrics = get_memory_metrics()
        if not metrics.heavy_model_allowed:
            raise ProviderError(
                "router",
                f"Memory usage too high ({metrics.percent_used:.1f}%). "
                f"Available: {metrics.available_gb:.1f}GB. "
                "Free memory before making requests.",
            )

        adapter = self._get_adapter(request.provider)
        logger.info(
            "Routing chat to %s (model=%s)",
            adapter.provider_name,
            request.model or "default",
        )

        return await adapter.chat(request)

    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        """
        Route a streaming chat request.

        Args:
            request: Universal chat request.

        Yields:
            StreamChunk objects.
        """
        await self.initialize()

        # Memory check
        metrics = get_memory_metrics()
        if not metrics.heavy_model_allowed:
            raise ProviderError(
                "router",
                f"Memory usage too high ({metrics.percent_used:.1f}%). "
                f"Available: {metrics.available_gb:.1f}GB.",
            )

        adapter = self._get_adapter(request.provider)
        logger.info(
            "Routing stream to %s (model=%s)",
            adapter.provider_name,
            request.model or "default",
        )

        async for chunk in adapter.chat_stream(request):
            yield chunk

    async def list_models(self, provider: str | None = None) -> list[ModelInfo]:
        """
        List available models, optionally filtered by provider.

        Args:
            provider: Filter by provider name, or None for all.

        Returns:
            List of ModelInfo from one or all providers.
        """
        await self.initialize()

        if provider:
            adapter = self._get_adapter(provider)
            return await adapter.list_models()

        all_models: list[ModelInfo] = []
        for adapter in self._adapters.values():
            try:
                models = await adapter.list_models()
                all_models.extend(models)
            except Exception as exc:
                logger.warning(
                    "Failed to list models from %s: %s",
                    adapter.provider_name,
                    exc,
                )
        return all_models

    async def get_status(self) -> RouterStatus:
        """Get the overall router status."""
        await self.initialize()

        providers: list[ProviderStatus] = []
        total_models = 0

        for adapter in self._adapters.values():
            try:
                status = await adapter.check_availability()
                providers.append(status)
                total_models += status.models_count
            except Exception as exc:
                providers.append(
                    ProviderStatus(
                        name=adapter.provider_name,
                        available=False,
                        detail=str(exc),
                    )
                )

        metrics = get_memory_metrics()

        return RouterStatus(
            active_provider=self._default_provider,
            providers=providers,
            memory_ok=metrics.heavy_model_allowed,
            total_models=total_models,
        )

    async def check_provider(self, provider: str) -> ProviderStatus:
        """Check a specific provider's availability."""
        await self.initialize()
        adapter = self._get_adapter(provider)
        return await adapter.check_availability()

    async def switch_provider(self, provider: str) -> None:
        """
        Switch the active default provider at runtime.

        If the provider adapter isn't initialized yet, create it.
        """
        await self.initialize()

        provider = provider.lower()
        if provider not in PROVIDER_REGISTRY:
            raise ProviderError(
                provider,
                f"Unknown provider '{provider}'. Known: {list(PROVIDER_REGISTRY.keys())}",
            )

        # Lazy-init the adapter if not yet created
        if provider not in self._adapters:
            self._adapters[provider] = PROVIDER_REGISTRY[provider]()

        self._default_provider = provider
        logger.info("Switched default provider to: %s", provider)

    async def set_model(self, model: str) -> None:
        """
        Set the default model for the current active provider at runtime.
        """
        await self.initialize()

        adapter = self._get_adapter()
        # Update the adapter's internal default model
        if hasattr(adapter, "_default_model"):
            adapter._default_model = model
            logger.info("Set default model for %s to: %s", adapter.provider_name, model)
        else:
            raise ProviderError(
                adapter.provider_name,
                "This provider does not support runtime model switching.",
            )

    async def get_config(self) -> LLMConfig:
        """Get current LLM configuration."""
        await self.initialize()

        ollama_model = ""
        openai_model = ""
        if "ollama" in self._adapters:
            ollama_model = await self._adapters["ollama"].get_default_model()
        if "openai" in self._adapters:
            openai_model = await self._adapters["openai"].get_default_model()

        return LLMConfig(
            active_provider=self._default_provider,
            ollama_model=ollama_model,
            openai_model=openai_model,
            available_providers=list(self._adapters.keys()),
        )

    async def update_config(self, update: LLMConfigUpdate) -> LLMConfig:
        """Apply a configuration update and return the new config."""
        if update.provider:
            await self.switch_provider(update.provider)
        if update.model:
            await self.set_model(update.model)
        return await self.get_config()

    @property
    def available_providers(self) -> list[str]:
        """Return list of configured provider names."""
        return list(self._adapters.keys())

    @property
    def default_provider(self) -> str:
        """Return the default provider name."""
        return self._default_provider


# Singleton router instance
_router: LLMRouter | None = None


def get_router() -> LLMRouter:
    """Get or create the router singleton."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router


def reset_router() -> None:
    """Reset the router singleton (for testing)."""
    global _router
    _router = None
