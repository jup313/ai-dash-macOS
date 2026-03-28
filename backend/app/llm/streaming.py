"""
Streaming utilities — Server-Sent Events (SSE) for LLM responses.

Converts async StreamChunk iterators into SSE-formatted responses
compatible with frontend EventSource consumers.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from backend.app.llm.models import StreamChunk

logger = logging.getLogger(__name__)


async def stream_to_sse(chunks: AsyncIterator[StreamChunk]) -> AsyncIterator[str]:
    """
    Convert StreamChunk async iterator to SSE-formatted strings.

    Each chunk is sent as a Server-Sent Event:
        data: {"content": "...", "done": false}

    Final event includes done=true.
    Stream ends with [DONE] sentinel.

    Args:
        chunks: Async iterator of StreamChunk objects.

    Yields:
        SSE-formatted strings ready for StreamingResponse.
    """
    try:
        async for chunk in chunks:
            payload = {
                "content": chunk.content,
                "model": chunk.model,
                "provider": chunk.provider,
                "done": chunk.done,
            }
            if chunk.finish_reason:
                payload["finish_reason"] = chunk.finish_reason

            yield f"data: {json.dumps(payload)}\n\n"

            if chunk.done:
                break

        # Send terminal event
        yield "data: [DONE]\n\n"

    except Exception as exc:
        logger.error("Stream error: %s", exc)
        error_payload = {
            "error": str(exc),
            "done": True,
        }
        yield f"data: {json.dumps(error_payload)}\n\n"
        yield "data: [DONE]\n\n"


async def collect_stream(chunks: AsyncIterator[StreamChunk]) -> str:
    """
    Collect all chunks from a stream into a single string.

    Useful for testing or when a non-streaming result is needed
    from a streaming source.

    Args:
        chunks: Async iterator of StreamChunk objects.

    Returns:
        Concatenated content from all chunks.
    """
    parts: list[str] = []
    async for chunk in chunks:
        parts.append(chunk.content)
        if chunk.done:
            break
    return "".join(parts)
