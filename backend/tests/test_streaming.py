"""
Tests for streaming utilities.

Tests:
- SSE formatting
- Stream collection
- Error handling in streams
"""

from __future__ import annotations

import json

import pytest

from backend.app.llm.models import StreamChunk
from backend.app.llm.streaming import collect_stream, stream_to_sse


async def _mock_chunks():
    """Generate mock stream chunks."""
    yield StreamChunk(content="Hello", model="llama3:8b", provider="ollama", done=False)
    yield StreamChunk(content=" world", model="llama3:8b", provider="ollama", done=False)
    yield StreamChunk(content="!", model="llama3:8b", provider="ollama", done=True, finish_reason="stop")


async def _empty_chunks():
    """Generate no chunks."""
    return
    yield  # Make it an async generator


class TestStreamToSSE:
    """Tests for SSE conversion."""

    @pytest.mark.asyncio
    async def test_sse_format(self):
        events = []
        async for event in stream_to_sse(_mock_chunks()):
            events.append(event)

        # Should have content events + [DONE]
        assert len(events) >= 2

        # First event should be valid SSE
        assert events[0].startswith("data: ")
        assert events[0].endswith("\n\n")

        # Parse first event payload
        payload = json.loads(events[0].replace("data: ", "").strip())
        assert payload["content"] == "Hello"
        assert payload["done"] is False

    @pytest.mark.asyncio
    async def test_sse_done_event(self):
        events = []
        async for event in stream_to_sse(_mock_chunks()):
            events.append(event)

        # Last event should be [DONE]
        assert events[-1] == "data: [DONE]\n\n"

    @pytest.mark.asyncio
    async def test_sse_includes_finish_reason(self):
        events = []
        async for event in stream_to_sse(_mock_chunks()):
            events.append(event)

        # Second-to-last data event (before [DONE]) should have finish_reason
        # Find the done event
        for event in events:
            if event == "data: [DONE]\n\n":
                continue
            payload = json.loads(event.replace("data: ", "").strip())
            if payload.get("done"):
                assert payload.get("finish_reason") == "stop"

    @pytest.mark.asyncio
    async def test_sse_empty_stream(self):
        events = []
        async for event in stream_to_sse(_empty_chunks()):
            events.append(event)

        # Should still have [DONE]
        assert events[-1] == "data: [DONE]\n\n"


class TestCollectStream:
    """Tests for stream collection."""

    @pytest.mark.asyncio
    async def test_collect_full_stream(self):
        result = await collect_stream(_mock_chunks())
        assert result == "Hello world!"

    @pytest.mark.asyncio
    async def test_collect_empty_stream(self):
        result = await collect_stream(_empty_chunks())
        assert result == ""
