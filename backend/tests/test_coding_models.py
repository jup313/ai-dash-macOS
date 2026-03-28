"""Tests for coding engine data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.coding.models import (
    AnalysisIssue,
    AnalysisResult,
    AnalysisSeverity,
    CodeAction,
    CodeLanguage,
    CodeMetrics,
    CodeRequest,
    CodeResult,
    ExecutionRequest,
    ExecutionResult,
    FileInfo,
    FileReadResult,
    FileWriteRequest,
    FileWriteResult,
)


class TestCodeLanguage:
    def test_values(self):
        assert CodeLanguage.PYTHON == "python"
        assert CodeLanguage.JAVASCRIPT == "javascript"
        assert CodeLanguage.TYPESCRIPT == "typescript"
        assert CodeLanguage.BASH == "bash"
        assert CodeLanguage.UNKNOWN == "unknown"

    def test_all_languages(self):
        assert len(CodeLanguage) == 11


class TestCodeAction:
    def test_values(self):
        assert CodeAction.GENERATE == "generate"
        assert CodeAction.REFACTOR == "refactor"
        assert CodeAction.EXPLAIN == "explain"
        assert CodeAction.FIX == "fix"
        assert CodeAction.TEST == "test"
        assert CodeAction.DOCUMENT == "document"


class TestCodeRequest:
    def test_minimal(self):
        req = CodeRequest(prompt="Write a hello world")
        assert req.action == CodeAction.GENERATE
        assert req.language == CodeLanguage.PYTHON
        assert req.temperature == 0.3
        assert req.prompt == "Write a hello world"

    def test_full(self):
        req = CodeRequest(
            action=CodeAction.REFACTOR,
            prompt="Improve this",
            code="x = 1",
            language=CodeLanguage.JAVASCRIPT,
            model="gpt-4",
            provider="openai",
            temperature=0.5,
            max_tokens=2048,
        )
        assert req.action == CodeAction.REFACTOR
        assert req.code == "x = 1"
        assert req.model == "gpt-4"

    def test_empty_prompt_rejected(self):
        with pytest.raises(ValidationError):
            CodeRequest(prompt="")


class TestCodeResult:
    def test_create(self):
        result = CodeResult(
            action=CodeAction.GENERATE,
            code="print('hello')",
            language=CodeLanguage.PYTHON,
            model_used="llama3:8b",
            provider_used="ollama",
        )
        assert result.code == "print('hello')"
        assert result.created_at is not None


class TestAnalysisModels:
    def test_severity_values(self):
        assert AnalysisSeverity.ERROR == "error"
        assert AnalysisSeverity.WARNING == "warning"
        assert AnalysisSeverity.INFO == "info"
        assert AnalysisSeverity.HINT == "hint"

    def test_issue(self):
        issue = AnalysisIssue(
            severity=AnalysisSeverity.ERROR,
            message="Syntax error",
            line=10,
            rule="syntax",
        )
        assert issue.line == 10

    def test_metrics_defaults(self):
        m = CodeMetrics()
        assert m.total_lines == 0
        assert m.functions == 0
        assert m.complexity_score is None

    def test_analysis_result(self):
        result = AnalysisResult(language=CodeLanguage.PYTHON)
        assert result.syntax_valid is True
        assert result.issues == []
        assert result.suggestions == []


class TestExecutionModels:
    def test_request_minimal(self):
        req = ExecutionRequest(code="print(1)")
        assert req.language == CodeLanguage.PYTHON
        assert req.timeout_seconds == 30

    def test_request_with_stdin(self):
        req = ExecutionRequest(code="input()", stdin="hello")
        assert req.stdin == "hello"

    def test_empty_code_rejected(self):
        with pytest.raises(ValidationError):
            ExecutionRequest(code="")

    def test_result_defaults(self):
        result = ExecutionResult()
        assert result.exit_code == -1
        assert result.timed_out is False


class TestFileModels:
    def test_file_info(self):
        info = FileInfo(path="test.py", name="test.py", extension=".py")
        assert info.is_directory is False

    def test_read_result(self):
        result = FileReadResult(path="test.py", content="hello")
        assert result.size_bytes == 0

    def test_write_request(self):
        req = FileWriteRequest(path="test.py", content="hello")
        assert req.create_dirs is True

    def test_write_request_empty_path_rejected(self):
        with pytest.raises(ValidationError):
            FileWriteRequest(path="", content="hello")

    def test_write_result(self):
        result = FileWriteResult(path="test.py", size_bytes=5, created=True)
        assert result.overwritten is False
