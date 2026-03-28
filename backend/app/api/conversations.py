"""
Conversation API endpoints — CRUD for conversations and messages.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

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
