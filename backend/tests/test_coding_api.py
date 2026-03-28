"""Tests for coding API endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.coding.file_manager import FileManager, reset_file_manager
from backend.app.coding.models import CodeLanguage
from backend.app.main import app
import backend.app.coding.file_manager as fm_module


@pytest.fixture(autouse=True)
def isolated_sandbox(tmp_path):
    """Give each test a fresh sandbox directory."""
    reset_file_manager()
    # Create an isolated FileManager and inject it as the singleton
    isolated_fm = FileManager(sandbox_root=str(tmp_path))
    fm_module._file_manager = isolated_fm
    yield
    reset_file_manager()


@pytest.fixture()
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestAnalyzeEndpoint:
    async def test_analyze_python(self, client):
        resp = await client.post(
            "/api/coding/analyze",
            params={"code": "def hello():\n    pass\n", "language": "python"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["syntax_valid"] is True
        assert data["language"] == "python"

    async def test_analyze_invalid_python(self, client):
        resp = await client.post(
            "/api/coding/analyze",
            params={"code": "def ("},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["syntax_valid"] is False


class TestExecuteEndpoint:
    async def test_execute_python(self, client):
        resp = await client.post(
            "/api/coding/execute",
            json={"code": "print('api test')"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["exit_code"] == 0
        assert "api test" in data["stdout"]

    async def test_execute_unsupported(self, client):
        resp = await client.post(
            "/api/coding/execute",
            json={"code": "<html>", "language": "html"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["exit_code"] == 1


class TestGenerateEndpoint:
    async def test_generate_calls_llm(self, client):
        from backend.app.llm.models import ChatResponse, TokenUsage

        mock_response = ChatResponse(
            content="```python\nprint('gen')\n```",
            model="llama3:8b",
            provider="ollama",
            usage=TokenUsage(total_tokens=10),
        )

        with patch("backend.app.coding.generator.get_router") as mock_get:
            mock_router = AsyncMock()
            mock_router.chat = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_router

            resp = await client.post(
                "/api/coding/generate",
                json={"prompt": "hello world"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["code"] == "print('gen')"


class TestFileEndpoints:
    async def test_list_files_empty(self, client):
        resp = await client.get("/api/coding/files")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_write_and_read(self, client):
        # Write
        resp = await client.post(
            "/api/coding/files/write",
            json={"path": "test.py", "content": "x = 1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] is True

        # Read
        resp = await client.get(
            "/api/coding/files/read",
            params={"path": "test.py"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "x = 1"

    async def test_read_not_found(self, client):
        resp = await client.get(
            "/api/coding/files/read",
            params={"path": "nope.py"},
        )
        assert resp.status_code == 404

    async def test_delete_file(self, client):
        # Create first
        await client.post(
            "/api/coding/files/write",
            json={"path": "del.py", "content": "x"},
        )
        # Delete
        resp = await client.delete(
            "/api/coding/files",
            params={"path": "del.py"},
        )
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    async def test_delete_not_found(self, client):
        resp = await client.delete(
            "/api/coding/files",
            params={"path": "nope.py"},
        )
        assert resp.status_code == 404
