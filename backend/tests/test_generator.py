"""Tests for the code generator."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.app.coding.generator import (
    _build_user_message,
    _parse_response,
    generate_code,
)
from backend.app.coding.models import CodeAction, CodeLanguage, CodeRequest
from backend.app.llm.models import ChatResponse, TokenUsage


class TestBuildUserMessage:
    def test_generate(self):
        req = CodeRequest(prompt="Write a hello world", language=CodeLanguage.PYTHON)
        msg = _build_user_message(req)
        assert "python" in msg.lower()
        assert "hello world" in msg.lower()

    def test_explain_with_code(self):
        req = CodeRequest(
            action=CodeAction.EXPLAIN,
            prompt="What does this do",
            code="x = 1",
            language=CodeLanguage.PYTHON,
        )
        msg = _build_user_message(req)
        assert "Explain" in msg
        assert "x = 1" in msg

    def test_refactor(self):
        req = CodeRequest(
            action=CodeAction.REFACTOR,
            prompt="Improve",
            code="x=1",
            language=CodeLanguage.PYTHON,
        )
        msg = _build_user_message(req)
        assert "Refactor" in msg
        assert "x=1" in msg

    def test_fix(self):
        req = CodeRequest(
            action=CodeAction.FIX,
            prompt="Fix bug",
            code="print(x",
            language=CodeLanguage.PYTHON,
        )
        msg = _build_user_message(req)
        assert "Fix" in msg

    def test_test(self):
        req = CodeRequest(
            action=CodeAction.TEST,
            prompt="Test this",
            code="def f(): pass",
            language=CodeLanguage.PYTHON,
        )
        msg = _build_user_message(req)
        assert "test" in msg.lower()

    def test_document(self):
        req = CodeRequest(
            action=CodeAction.DOCUMENT,
            prompt="Add docs",
            code="def f(): pass",
            language=CodeLanguage.PYTHON,
        )
        msg = _build_user_message(req)
        assert "Document" in msg


class TestParseResponse:
    def test_code_block(self):
        content = "Here is the code:\n```python\nprint('hello')\n```\nDone."
        code, explanation = _parse_response(content, CodeAction.GENERATE)
        assert code == "print('hello')"
        assert "Done" in explanation

    def test_no_code_block_generate(self):
        content = "print('hello')"
        code, explanation = _parse_response(content, CodeAction.GENERATE)
        assert code == "print('hello')"
        assert explanation == ""

    def test_no_code_block_explain(self):
        content = "This function prints hello."
        code, explanation = _parse_response(content, CodeAction.EXPLAIN)
        assert code == ""
        assert "prints hello" in explanation

    def test_code_block_no_language(self):
        content = "```\nprint('hello')\n```"
        code, explanation = _parse_response(content, CodeAction.GENERATE)
        assert code == "print('hello')"


class TestGenerateCode:
    @pytest.fixture(autouse=True)
    def reset_singletons(self):
        from backend.app.llm.router import reset_router
        reset_router()
        yield
        reset_router()

    async def test_success(self):
        mock_response = ChatResponse(
            content="```python\nprint('hello')\n```\nA simple hello.",
            model="llama3:8b",
            provider="ollama",
            usage=TokenUsage(total_tokens=50),
        )

        with patch("backend.app.coding.generator.get_router") as mock_get:
            mock_router = AsyncMock()
            mock_router.chat = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_router

            req = CodeRequest(prompt="Write hello world")
            result = await generate_code(req)

            assert result.code == "print('hello')"
            assert result.model_used == "llama3:8b"
            assert result.tokens_used == 50
            assert result.duration_ms > 0

    async def test_error_handling(self):
        with patch("backend.app.coding.generator.get_router") as mock_get:
            mock_router = AsyncMock()
            mock_router.chat = AsyncMock(side_effect=RuntimeError("LLM down"))
            mock_get.return_value = mock_router

            req = CodeRequest(prompt="Write code")
            result = await generate_code(req)

            assert result.code == ""
            assert "Error" in result.explanation
            assert result.duration_ms > 0
