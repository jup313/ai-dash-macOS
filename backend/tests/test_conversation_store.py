"""
Tests for conversation store and memory models.
"""

from __future__ import annotations

import pytest

from backend.app.memory.models import (
    Conversation,
    ConversationCreate,
    ConversationMessage,
    MemoryStats,
)
from backend.app.memory.store import ConversationStore, get_store, reset_store


@pytest.fixture(autouse=True)
def _reset():
    reset_store()
    yield
    reset_store()


class TestConversationModels:
    def test_message_auto_id(self):
        msg = ConversationMessage(role="user", content="Hello")
        assert msg.message_id
        assert msg.role == "user"

    def test_conversation_auto_id(self):
        conv = Conversation()
        assert conv.conversation_id
        assert conv.message_count == 0
        assert conv.total_tokens == 0

    def test_conversation_token_count(self):
        conv = Conversation(messages=[
            ConversationMessage(role="user", content="Hi", tokens=5),
            ConversationMessage(role="assistant", content="Hello!", tokens=10),
        ])
        assert conv.message_count == 2
        assert conv.total_tokens == 15

    def test_create_request(self):
        req = ConversationCreate(title="Test", agent_name="summary")
        assert req.title == "Test"
        assert req.agent_name == "summary"

    def test_create_request_defaults(self):
        req = ConversationCreate()
        assert req.title == "New Conversation"
        assert req.agent_name == "chat"


class TestConversationStore:
    def test_create(self):
        store = ConversationStore()
        conv = store.create(title="Test Chat")
        assert conv.title == "Test Chat"
        assert conv.conversation_id

    def test_get(self):
        store = ConversationStore()
        conv = store.create()
        retrieved = store.get(conv.conversation_id)
        assert retrieved is not None
        assert retrieved.conversation_id == conv.conversation_id

    def test_get_nonexistent(self):
        store = ConversationStore()
        assert store.get("nonexistent") is None

    def test_add_message(self):
        store = ConversationStore()
        conv = store.create()
        msg = store.add_message(conv.conversation_id, role="user", content="Hello")
        assert msg is not None
        assert msg.content == "Hello"

        retrieved = store.get(conv.conversation_id)
        assert retrieved.message_count == 1

    def test_add_message_nonexistent(self):
        store = ConversationStore()
        msg = store.add_message("nonexistent", role="user", content="Hello")
        assert msg is None

    def test_get_messages(self):
        store = ConversationStore()
        conv = store.create()
        store.add_message(conv.conversation_id, role="user", content="First")
        store.add_message(conv.conversation_id, role="assistant", content="Second")
        store.add_message(conv.conversation_id, role="user", content="Third")

        msgs = store.get_messages(conv.conversation_id)
        assert len(msgs) == 3

    def test_get_messages_with_limit(self):
        store = ConversationStore()
        conv = store.create()
        for i in range(5):
            store.add_message(conv.conversation_id, role="user", content=f"Msg {i}")

        msgs = store.get_messages(conv.conversation_id, limit=2)
        assert len(msgs) == 2
        assert msgs[0].content == "Msg 3"
        assert msgs[1].content == "Msg 4"

    def test_list_conversations(self):
        store = ConversationStore()
        store.create(title="First")
        store.create(title="Second")
        summaries = store.list_conversations()
        assert len(summaries) == 2
        # Newest first
        assert summaries[0].title == "Second"

    def test_delete(self):
        store = ConversationStore()
        conv = store.create()
        assert store.delete(conv.conversation_id) is True
        assert store.get(conv.conversation_id) is None

    def test_delete_nonexistent(self):
        store = ConversationStore()
        assert store.delete("nonexistent") is False

    def test_clear(self):
        store = ConversationStore()
        store.create()
        store.create()
        count = store.clear()
        assert count == 2
        assert store.list_conversations() == []

    def test_stats(self):
        store = ConversationStore()
        conv = store.create()
        store.add_message(conv.conversation_id, role="user", content="Hi", tokens=5)
        store.add_message(conv.conversation_id, role="assistant", content="Hello", tokens=10)

        stats = store.get_stats()
        assert stats.total_conversations == 1
        assert stats.total_messages == 2
        assert stats.total_tokens == 15

    def test_enforce_limit(self):
        store = ConversationStore(max_conversations=2)
        store.create(title="First")
        store.create(title="Second")
        store.create(title="Third")
        summaries = store.list_conversations()
        assert len(summaries) == 2
        # First should be evicted
        titles = {s.title for s in summaries}
        assert "First" not in titles

    def test_singleton(self):
        reset_store()
        s1 = get_store()
        s2 = get_store()
        assert s1 is s2

    def test_reset(self):
        reset_store()
        s1 = get_store()
        reset_store()
        s2 = get_store()
        assert s1 is not s2
