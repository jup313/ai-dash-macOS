"""Tests for the code analyzer."""

from __future__ import annotations

import pytest

from backend.app.coding.analyzer import (
    EXTENSION_MAP,
    analyze_code,
    detect_language,
)
from backend.app.coding.models import AnalysisSeverity, CodeLanguage


class TestDetectLanguage:
    def test_python(self):
        assert detect_language("main.py") == CodeLanguage.PYTHON

    def test_javascript(self):
        assert detect_language("app.js") == CodeLanguage.JAVASCRIPT

    def test_typescript(self):
        assert detect_language("index.ts") == CodeLanguage.TYPESCRIPT

    def test_tsx(self):
        assert detect_language("component.tsx") == CodeLanguage.TYPESCRIPT

    def test_bash(self):
        assert detect_language("deploy.sh") == CodeLanguage.BASH

    def test_html(self):
        assert detect_language("index.html") == CodeLanguage.HTML

    def test_css(self):
        assert detect_language("styles.css") == CodeLanguage.CSS

    def test_json(self):
        assert detect_language("package.json") == CodeLanguage.JSON

    def test_yaml(self):
        assert detect_language("config.yaml") == CodeLanguage.YAML

    def test_yml(self):
        assert detect_language("ci.yml") == CodeLanguage.YAML

    def test_markdown(self):
        assert detect_language("README.md") == CodeLanguage.MARKDOWN

    def test_sql(self):
        assert detect_language("query.sql") == CodeLanguage.SQL

    def test_unknown(self):
        assert detect_language("file.xyz") == CodeLanguage.UNKNOWN

    def test_case_insensitive(self):
        assert detect_language("FILE.PY") == CodeLanguage.PYTHON


class TestAnalyzePython:
    def test_valid_code(self):
        code = "def hello():\n    print('hello')\n"
        result = analyze_code(code, CodeLanguage.PYTHON)
        assert result.syntax_valid is True
        assert result.language == CodeLanguage.PYTHON
        assert result.metrics.functions == 1

    def test_syntax_error(self):
        code = "def hello(\n"
        result = analyze_code(code, CodeLanguage.PYTHON)
        assert result.syntax_valid is False
        assert any(i.severity == AnalysisSeverity.ERROR for i in result.issues)

    def test_metrics_lines(self):
        code = "# comment\nx = 1\n\ny = 2\n"
        result = analyze_code(code, CodeLanguage.PYTHON)
        assert result.metrics.total_lines == 4
        assert result.metrics.comment_lines == 1
        assert result.metrics.blank_lines == 1
        assert result.metrics.code_lines == 2

    def test_metrics_classes(self):
        code = "class Foo:\n    pass\n\nclass Bar:\n    pass\n"
        result = analyze_code(code, CodeLanguage.PYTHON)
        assert result.metrics.classes == 2

    def test_metrics_imports(self):
        code = "import os\nfrom sys import path\n"
        result = analyze_code(code, CodeLanguage.PYTHON)
        assert result.metrics.imports == 2

    def test_complexity_score(self):
        code = "def f():\n    if True:\n        for x in []:\n            pass\n"
        result = analyze_code(code, CodeLanguage.PYTHON)
        assert result.metrics.complexity_score is not None
        assert result.metrics.complexity_score > 1.0

    def test_bare_except_warning(self):
        code = "try:\n    pass\nexcept:\n    pass\n"
        result = analyze_code(code, CodeLanguage.PYTHON)
        bare = [i for i in result.issues if i.rule == "bare-except"]
        assert len(bare) == 1
        assert bare[0].severity == AnalysisSeverity.WARNING

    def test_mutable_default_warning(self):
        code = "def f(x=[]):\n    pass\n"
        result = analyze_code(code, CodeLanguage.PYTHON)
        mutable = [i for i in result.issues if i.rule == "mutable-default"]
        assert len(mutable) == 1

    def test_global_statement_info(self):
        code = "x = 1\ndef f():\n    global x\n    x = 2\n"
        result = analyze_code(code, CodeLanguage.PYTHON)
        globs = [i for i in result.issues if i.rule == "global-statement"]
        assert len(globs) == 1
        assert globs[0].severity == AnalysisSeverity.INFO

    def test_todo_comment(self):
        code = "# TODO: fix this\nx = 1\n"
        result = analyze_code(code, CodeLanguage.PYTHON)
        todos = [i for i in result.issues if i.rule == "todo"]
        assert len(todos) == 1

    def test_fixme_comment(self):
        code = "# FIXME: broken\nx = 1\n"
        result = analyze_code(code, CodeLanguage.PYTHON)
        fixes = [i for i in result.issues if i.rule == "fixme"]
        assert len(fixes) == 1

    def test_suggestion_no_comments(self):
        # More than 10 code lines with no comments
        code = "\n".join(f"x{i} = {i}" for i in range(15))
        result = analyze_code(code, CodeLanguage.PYTHON)
        assert any("comment" in s.lower() for s in result.suggestions)

    def test_suggestion_no_functions(self):
        # More than 20 code lines with no functions
        code = "\n".join(f"x{i} = {i}" for i in range(25))
        result = analyze_code(code, CodeLanguage.PYTHON)
        assert any("function" in s.lower() for s in result.suggestions)

    def test_async_function_counted(self):
        code = "async def f():\n    pass\n"
        result = analyze_code(code, CodeLanguage.PYTHON)
        assert result.metrics.functions == 1

    def test_empty_code(self):
        result = analyze_code("", CodeLanguage.PYTHON)
        assert result.syntax_valid is True
        assert result.metrics.total_lines == 0  # empty string splitlines() is []


class TestAnalyzeGeneric:
    def test_json_valid(self):
        result = analyze_code('{"key": "value"}', CodeLanguage.JSON)
        assert result.syntax_valid is True

    def test_json_invalid(self):
        result = analyze_code("{invalid}", CodeLanguage.JSON)
        assert result.syntax_valid is False

    def test_line_length_warning(self):
        code = "x" * 130
        result = analyze_code(code, CodeLanguage.JAVASCRIPT)
        long_lines = [i for i in result.issues if i.rule == "line-length"]
        assert len(long_lines) == 1

    def test_long_file_suggestion(self):
        code = "\n".join(f"line {i}" for i in range(350))
        result = analyze_code(code, CodeLanguage.BASH)
        assert any("splitting" in s.lower() for s in result.suggestions)

    def test_basic_metrics(self):
        code = "# comment\ncode\n\n"
        result = analyze_code(code, CodeLanguage.BASH)
        assert result.metrics.total_lines == 3
        assert result.metrics.comment_lines == 1
