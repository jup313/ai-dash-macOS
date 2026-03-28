"""
Conversation store — in-memory conversation persistence.

Local-first: stores conversations in memory with no external dependencies.
Future: can be extended with SQLite or file-based persistence.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from backend.app.memory.models import (
    Conversation,
    ConversationMessage,
    ConversationSummary,
    MemoryStats,
)

logger = logging.getLogger(__name__)


class ConversationStore:
    """In-memory conversation store."""

    def __init__(self, max_conversations: int = 100) -> None:
        self._conversations: dict[str, Conversation] = {}
        self._max_conversations = max_conversations

    def create(self, title: str = "New Conversation", agent_name: str = "chat") -> Conversation:
        """Create a new conversation."""
        conv = Conversation(title=title, agent_name=agent_name)
        self._conversations[conv.conversation_id] = conv
        self._enforce_limit()
        logger.info("Created conversation %s", conv.conversation_id[:8])
        return conv

    def get(self, conversation_id: str) -> Conversation | None:
        """Get a conversation by ID."""
        return self._conversations.get(conversation_id)

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        model: str = "",
        provider: str = "",
        tokens: int | None = None,
    ) -> ConversationMessage | None:
        """Add a message to a conversation."""
        conv = self._conversations.get(conversation_id)
        if conv is None:
            return None

        msg = ConversationMessage(
            role=role,
            content=content,
            model=model,
            provider=provider,
            tokens=tokens,
        )
        conv.messages.append(msg)
        conv.updated_at = datetime.now(timezone.utc)
        return msg

    def get_messages(
        self,
        conversation_id: str,
        limit: int | None = None,
    ) -> list[ConversationMessage]:
        """Get messages from a conversation, optionally limited to last N."""
        conv = self._conversations.get(conversation_id)
        if conv is None:
            return []
        if limit is not None:
            return conv.messages[-limit:]
        return conv.messages

    def list_conversations(self) -> list[ConversationSummary]:
        """List all conversations as summaries, newest first."""
        summaries = [
            ConversationSummary(
                conversation_id=c.conversation_id,
                title=c.title,
                agent_name=c.agent_name,
                message_count=c.message_count,
                total_tokens=c.total_tokens,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in self._conversations.values()
        ]
        return sorted(summaries, key=lambda s: s.updated_at, reverse=True)

    def delete(self, conversation_id: str) -> bool:
        """Delete a conversation. Returns True if found and deleted."""
        return self._conversations.pop(conversation_id, None) is not None

    def clear(self) -> int:
        """Clear all conversations. Returns count of deleted conversations."""
        count = len(self._conversations)
        self._conversations.clear()
        return count

    def get_stats(self) -> MemoryStats:
        """Get memory statistics."""
        total_messages = sum(c.message_count for c in self._conversations.values())
        total_tokens = sum(c.total_tokens for c in self._conversations.values())
        return MemoryStats(
            total_conversations=len(self._conversations),
            total_messages=total_messages,
            total_tokens=total_tokens,
        )

    def _enforce_limit(self) -> None:
        """Remove oldest conversations if over limit."""
        if len(self._conversations) <= self._max_conversations:
            return
        sorted_convs = sorted(
            self._conversations.values(),
            key=lambda c: c.updated_at,
        )
        to_remove = len(self._conversations) - self._max_conversations
        for conv in sorted_convs[:to_remove]:
            self._conversations.pop(conv.conversation_id, None)
            logger.info("Evicted conversation %s (limit reached)", conv.conversation_id[:8])


# Singleton store
_store: ConversationStore | None = None


def get_store() -> ConversationStore:
    """Get or create the store singleton."""
    global _store
    if _store is None:
        _store = ConversationStore()
    return _store


def reset_store() -> None:
    """Reset the store singleton (for testing)."""
    global _store
    _store = None
