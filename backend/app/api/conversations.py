"""
Conversation API endpoints — CRUD for conversations and messages.

Includes chat endpoints that connect conversations to LLM agents,
providing a full ChatGPT-like experience with persistent memory.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.app.agents.registry import get_registry
from backend.app.api.fleet import fetch_fleet_context, is_fleet_query
from backend.app.api.personalities import get_personality
from backend.app.llm.base import ProviderError, ProviderUnavailableError
from backend.app.llm.models import ChatRequest, Message, Role, StreamChunk
from backend.app.llm.router import get_router
from backend.app.llm.streaming import stream_to_sse
from backend.app.memory.models import (
    Conversation,
    ConversationCreate,
    ConversationMessage,
    ConversationSummary,
    MemoryStats,
)
from backend.app.memory.store import get_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# ── Chat request model ────────────────────────────────────────────────────────

class ChatMessageRequest(BaseModel):
    """Request to send a chat message and get an LLM response."""
    content: str = Field(..., min_length=1, description="User message content")
    agent: str = Field(default="chat", description="Agent name to use")
    model: str | None = Field(default=None, description="Model override")
    provider: str | None = Field(default=None, description="Provider override")
    stream: bool = Field(default=False, description="Enable streaming response")
    personality: str | None = Field(default=None, description="Personality preset ID")


@router.post("/", response_model=Conversation)
async def create_conversation(request: ConversationCreate) -> Conversation:
    """Create a new conversation."""
    store = get_store()
    return store.create(title=request.title, agent_name=request.agent_name)


@router.get("/", response_model=list[ConversationSummary])
async def list_conversations() -> list[ConversationSummary]:
    """List all conversations (newest first)."""
    store = get_store()
    return store.list_conversations()


@router.get("/stats", response_model=MemoryStats)
async def memory_stats() -> MemoryStats:
    """Get conversation memory statistics."""
    store = get_store()
    return store.get_stats()


@router.get("/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str) -> Conversation:
    """Get a conversation by ID."""
    store = get_store()
    conv = store.get(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str) -> dict:
    """Delete a conversation."""
    store = get_store()
    if not store.delete(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True, "conversation_id": conversation_id}


@router.post("/{conversation_id}/messages", response_model=ConversationMessage)
async def add_message(
    conversation_id: str,
    role: str,
    content: str,
) -> ConversationMessage:
    """Add a message to a conversation."""
    store = get_store()
    msg = store.add_message(conversation_id, role=role, content=content)
    if msg is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return msg


@router.get("/{conversation_id}/messages", response_model=list[ConversationMessage])
async def get_messages(
    conversation_id: str,
    limit: int | None = None,
) -> list[ConversationMessage]:
    """Get messages from a conversation."""
    store = get_store()
    conv = store.get(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return store.get_messages(conversation_id, limit=limit)


@router.delete("/")
async def clear_all() -> dict:
    """Clear all conversations."""
    store = get_store()
    count = store.clear()
    return {"cleared": count}


# ── Chat endpoints ────────────────────────────────────────────────────────────


@router.post("/{conversation_id}/chat")
async def chat_in_conversation(
    conversation_id: str,
    request: ChatMessageRequest,
):
    """
    Send a message in a conversation and get an LLM response.

    This is the core chat endpoint — a local ChatGPT replacement.
    It:
    1. Stores the user message in conversation history
    2. Builds context from conversation history + agent system prompt
    3. Calls the LLM via the router
    4. Stores and returns the assistant response
    5. Optionally streams via SSE
    """
    store = get_store()
    conv = store.get(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # 1. Store user message
    store.add_message(conversation_id, role="user", content=request.content)

    # 2. Build system prompt from agent + personality
    system_prompt = "You are a helpful AI assistant running locally on macOS Apple Silicon."
    registry = get_registry()
    agent_info_list = registry.list_agents()
    for a in agent_info_list:
        if a.name == (request.agent or conv.agent_name):
            system_prompt = a.system_prompt
            break

    # Apply personality overlay if specified
    if request.personality:
        personality = get_personality(request.personality)
        if personality:
            system_prompt = f"{personality.system_prompt}\n\n{system_prompt}"

    # 2b. Auto-inject fleet context for device/network queries
    fleet_context: str | None = None
    if is_fleet_query(request.content):
        logger.info("Fleet query detected, fetching live data for: %s", request.content[:80])
        fleet_context = await fetch_fleet_context(request.content)
        if fleet_context:
            system_prompt = f"{system_prompt}\n\n{fleet_context}"

    # 3. Build messages from conversation history
    history = store.get_messages(conversation_id, limit=50)
    messages: list[Message] = [Message(role=Role.SYSTEM, content=system_prompt)]
    for msg in history:
        if msg.role == "user":
            messages.append(Message(role=Role.USER, content=msg.content))
        elif msg.role == "assistant":
            messages.append(Message(role=Role.ASSISTANT, content=msg.content))

    # 4. Build LLM request
    chat_request = ChatRequest(
        messages=messages,
        model=request.model,
        provider=request.provider,
        stream=request.stream,
    )

    try:
        llm_router = get_router()

        if request.stream:
            # Streaming response — store message when final chunk arrives
            async def stream_and_store():
                full_content = ""
                async for chunk in llm_router.chat_stream(chat_request):
                    full_content += chunk.content
                    if chunk.done:
                        # Store BEFORE yielding the final chunk, because
                        # stream_to_sse breaks on done=True which would
                        # prevent any code after the yield from executing.
                        store.add_message(
                            conversation_id,
                            role="assistant",
                            content=full_content,
                        )
                    yield chunk

            return StreamingResponse(
                stream_to_sse(stream_and_store()),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            # Non-streaming response
            response = await llm_router.chat(chat_request)

            # 5. Store assistant response
            store.add_message(conversation_id, role="assistant", content=response.content)

            return {
                "content": response.content,
                "model": response.model,
                "provider": response.provider,
                "usage": response.usage.model_dump() if response.usage else None,
                "conversation_id": conversation_id,
            }

    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ProviderError as exc:
        status = exc.status_code or 500
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Chat error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat error: {exc}") from exc
