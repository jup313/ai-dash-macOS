"""
LLM API endpoints — chat, streaming, models, status.

All endpoints route through the LLM Router which dispatches
to the configured provider adapter.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.app.llm.base import ProviderError, ProviderUnavailableError
from backend.app.llm.models import ChatRequest, ChatResponse, ModelInfo, RouterStatus
from backend.app.llm.router import get_router
from backend.app.llm.streaming import stream_to_sse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Send a chat completion request.

    Routes to the configured default provider or the provider
    specified in the request. Memory-gated.
    """
    try:
        llm_router = get_router()
        return await llm_router.chat(request)
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ProviderError as exc:
        status = exc.status_code or 500
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Chat error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}") from exc


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """
    Send a streaming chat completion request.

    Returns Server-Sent Events (SSE) stream.
    """
    try:
        llm_router = get_router()
        # Force stream mode
        request.stream = True
        chunks = llm_router.chat_stream(request)
        return StreamingResponse(
            stream_to_sse(chunks),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ProviderError as exc:
        status = exc.status_code or 500
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Stream error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}") from exc


@router.get("/models", response_model=list[ModelInfo])
async def list_models(provider: str | None = None) -> list[ModelInfo]:
    """
    List available models.

    Optionally filter by provider name.
    """
    try:
        llm_router = get_router()
        return await llm_router.list_models(provider=provider)
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("List models error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}") from exc


@router.get("/status", response_model=RouterStatus)
async def router_status() -> RouterStatus:
    """
    Get LLM router status.

    Returns active provider, all provider statuses,
    memory status, and total available models.
    """
    try:
        llm_router = get_router()
        return await llm_router.get_status()
    except Exception as exc:
        logger.error("Status error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}") from exc


@router.get("/providers")
async def list_providers() -> dict:
    """List configured providers and their availability."""
    try:
        llm_router = get_router()
        await llm_router.initialize()
        providers = []
        for name in llm_router.available_providers:
            status = await llm_router.check_provider(name)
            providers.append(status.model_dump())
        return {
            "default": llm_router.default_provider,
            "providers": providers,
        }
    except Exception as exc:
        logger.error("Providers error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}") from exc
