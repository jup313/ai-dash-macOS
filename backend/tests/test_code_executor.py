"""Tests for the code executor."""

from __future__ import annotations

import pytest

from backend.app.coding.executor import EXECUTABLE_LANGUAGES, execute_code
from backend.app.coding.models import CodeLanguage, ExecutionRequest


class TestExecuteCode:
    async def test_python_hello(self):
        req = ExecutionRequest(code="print('hello')")
        result = await execute_code(req)
        assert result.exit_code == 0
        assert result.stdout.strip() == "hello"
        assert result.language == CodeLanguage.PYTHON
        assert result.duration_ms > 0

    async def test_python_stderr(self):
        req = ExecutionRequest(code="import sys; sys.stderr.write('err')")
        result = await execute_code(req)
        assert result.exit_code == 0
        assert "err" in result.stderr

    async def test_python_exit_code(self):
        req = ExecutionRequest(code="import sys; sys.exit(42)")
        result = await execute_code(req)
        assert result.exit_code == 42

    async def test_python_stdin(self):
        req = ExecutionRequest(code="x = input(); print(f'got: {x}')", stdin="hello")
        result = await execute_code(req)
        assert result.exit_code == 0
        assert "got: hello" in result.stdout

    async def test_python_syntax_error(self):
        req = ExecutionRequest(code="def (")
        result = await execute_code(req)
        assert result.exit_code != 0
        assert "SyntaxError" in result.stderr

    async def test_timeout(self):
        req = ExecutionRequest(
            code="import time; time.sleep(10)",
            timeout_seconds=1,
        )
        result = await execute_code(req)
        assert result.timed_out is True
        assert result.exit_code == -1

    async def test_bash_echo(self):
        req = ExecutionRequest(
            code="echo 'hello bash'",
            language=CodeLanguage.BASH,
        )
        result = await execute_code(req)
        assert result.exit_code == 0
        assert "hello bash" in result.stdout

    async def test_unsupported_language(self):
        req = ExecutionRequest(
            code="<html></html>",
            language=CodeLanguage.HTML,
        )
        result = await execute_code(req)
        assert result.exit_code == 1
        assert "not executable" in result.stderr

    async def test_executable_languages(self):
        assert CodeLanguage.PYTHON in EXECUTABLE_LANGUAGES
        assert CodeLanguage.BASH in EXECUTABLE_LANGUAGES
        assert CodeLanguage.HTML not in EXECUTABLE_LANGUAGES

    async def test_multiline_output(self):
        req = ExecutionRequest(code="for i in range(3): print(i)")
        result = await execute_code(req)
        assert result.exit_code == 0
        assert "0" in result.stdout
        assert "2" in result.stdout
