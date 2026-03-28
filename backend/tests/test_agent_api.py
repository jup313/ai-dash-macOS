"""
Tests for Agent and Conversation API endpoints.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.agents.executor import reset_executor
from backend.app.agents.models import AgentResult, TaskStatus
from backend.app.agents.registry import reset_registry
from backend.app.memory.store import reset_store
from backend.app.main import app


@pytest.fixture(autouse=True)
def _reset():
    reset_registry()
    reset_executor()
    reset_store()
    yield
    reset_registry()
    reset_executor()
    reset_store()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestAgentEndpoints:
    @pytest.mark.asyncio
    async def test_list_agents(self, client):
        response = await client.get("/api/agents/list")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        names = {a["name"] for a in data}
        assert "chat" in names
        assert "summary" in names
        assert "analysis" in names

    @pytest.mark.asyncio
    async def test_get_agent(self, client):
        response = await client.get("/api/agents/chat")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "chat"
        assert data["agent_type"] == "chat"

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, client):
        response = await client.get("/api/agents/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_executor_status(self, client):
        response = await client.get("/api/agents/status")
        assert response.status_code == 200
        data = response.json()
        assert "active_tasks" in data
        assert "max_concurrency" in data
        assert data["registered_agents"] == 3


class TestConversationEndpoints:
    @pytest.mark.asyncio
    async def test_create_conversation(self, client):
        response = await client.post(
            "/api/conversations/",
            json={"title": "Test Chat", "agent_name": "chat"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Chat"
        assert data["conversation_id"]

    @pytest.mark.asyncio
    async def test_list_conversations(self, client):
        # Create two
        await client.post("/api/conversations/", json={"title": "First"})
        await client.post("/api/conversations/", json={"title": "Second"})

        response = await client.get("/api/conversations/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_get_conversation(self, client):
        create_resp = await client.post("/api/conversations/", json={"title": "Test"})
        conv_id = create_resp.json()["conversation_id"]

        response = await client.get(f"/api/conversations/{conv_id}")
        assert response.status_code == 200
        assert response.json()["title"] == "Test"

    @pytest.mark.asyncio
    async def test_get_conversation_not_found(self, client):
        response = await client.get("/api/conversations/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_conversation(self, client):
        create_resp = await client.post("/api/conversations/", json={"title": "Delete me"})
        conv_id = create_resp.json()["conversation_id"]

        response = await client.delete(f"/api/conversations/{conv_id}")
        assert response.status_code == 200
        assert response.json()["deleted"] is True

    @pytest.mark.asyncio
    async def test_memory_stats(self, client):
        response = await client.get("/api/conversations/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_conversations" in data
        assert "total_messages" in data

    @pytest.mark.asyncio
    async def test_get_messages(self, client):
        create_resp = await client.post("/api/conversations/", json={"title": "Msgs"})
        conv_id = create_resp.json()["conversation_id"]

        response = await client.get(f"/api/conversations/{conv_id}/messages")
        assert response.status_code == 200
        assert response.json() == []
