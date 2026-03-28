"""
Conversation memory models — message storage and session tracking.

Local-first conversation persistence with in-memory store.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    """A single message in a conversation."""

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str = Field(..., description="Message role: system, user, assistant")
    content: str = Field(..., description="Message content")
    model: str = ""
    provider: str = ""
    tokens: Optional[int] = None
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class Conversation(BaseModel):
    """A conversation session with message history."""

    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(default="New Conversation")
    agent_name: str = Field(default="chat")
    messages: list[ConversationMessage] = Field(default_factory=list)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def total_tokens(self) -> int:
        return sum(m.tokens or 0 for m in self.messages)


class ConversationSummary(BaseModel):
    """Lightweight conversation summary for listing."""

    conversation_id: str
    title: str
    agent_name: str
    message_count: int
    total_tokens: int
    created_at: datetime
    updated_at: datetime


class ConversationCreate(BaseModel):
    """Request to create a new conversation."""

    title: str = Field(default="New Conversation")
    agent_name: str = Field(default="chat")


class MemoryStats(BaseModel):
    """Conversation memory statistics."""

    total_conversations: int
    total_messages: int
    total_tokens: int
