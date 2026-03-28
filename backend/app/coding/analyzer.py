"""
Code analyzer — static analysis using Python AST and heuristics.

Provides:
- Syntax validation
- Code metrics (lines, functions, classes, imports, complexity)
- Issue detection (basic patterns)
- Language detection from extension
"""

from __future__ import annotations

import ast
import logging
import re

from backend.app.coding.models import (
    AnalysisIssue,
    AnalysisResult,
    AnalysisSeverity,
    CodeLanguage,
    CodeMetrics,
)

logger = logging.getLogger(__name__)

# Extension to language mapping
EXTENSION_MAP: dict[str, CodeLanguage] = {
    ".py": CodeLanguage.PYTHON,
    ".js": CodeLanguage.JAVASCRIPT,
    ".jsx": CodeLanguage.JAVASCRIPT,
    ".ts": CodeLanguage.TYPESCRIPT,
    ".tsx": CodeLanguage.TYPESCRIPT,
    ".sh": CodeLanguage.BASH,
    ".bash": CodeLanguage.BASH,
    ".html": CodeLanguage.HTML,
    ".htm": CodeLanguage.HTML,
    ".css": CodeLanguage.CSS,
    ".json": CodeLanguage.JSON,
    ".yaml": CodeLanguage.YAML,
    ".yml": CodeLanguage.YAML,
    ".md": CodeLanguage.MARKDOWN,
    ".sql": CodeLanguage.SQL,
}


def detect_language(filename: str) -> CodeLanguage:
    """Detect language from file extension."""
    for ext, lang in EXTENSION_MAP.items():
        if filename.lower().endswith(ext):
            return lang
    return CodeLanguage.UNKNOWN


def analyze_code(code: str, language: CodeLanguage = CodeLanguage.PYTHON) -> AnalysisResult:
    """
    Analyze code and return metrics, issues, and suggestions.

    For Python, uses AST parsing for deep analysis.
    For other languages, uses line-based heuristics.
    """
    if language == CodeLanguage.PYTHON:
        return _analyze_python(code)
    return _analyze_generic(code, language)


def _analyze_python(code: str) -> AnalysisResult:
    """Analyze Python code using AST."""
    issues: list[AnalysisIssue] = []
    suggestions: list[str] = []
    syntax_valid = True

    # Syntax check
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        syntax_valid = False
        issues.append(
            AnalysisIssue(
                severity=AnalysisSeverity.ERROR,
                message=f"Syntax error: {exc.msg}",
                line=exc.lineno,
                column=exc.offset,
                rule="syntax",
            )
        )
        # Still compute basic metrics from lines
        metrics = _compute_line_metrics(code)
        return AnalysisResult(
            language=CodeLanguage.PYTHON,
            syntax_valid=False,
            issues=issues,
            metrics=metrics,
            suggestions=suggestions,
        )

    # Compute metrics from AST
    metrics = _compute_line_metrics(code)
    functions = 0
    classes = 0
    imports = 0
    complexity = 0

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions += 1
            # Count branches for complexity
            complexity += _count_branches(node)
        elif isinstance(node, ast.ClassDef):
            classes += 1
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            imports += 1

    metrics.functions = functions
    metrics.classes = classes
    metrics.imports = imports
    # Cyclomatic complexity approximation
    metrics.complexity_score = round(1.0 + complexity / max(functions, 1), 2)

    # Check for common issues
    issues.extend(_check_python_patterns(code, tree))

    # Generate suggestions
    if metrics.comment_lines == 0 and metrics.code_lines > 10:
        suggestions.append("Consider adding comments to explain complex logic")
    if functions == 0 and metrics.code_lines > 20:
        suggestions.append("Consider breaking code into functions for better organization")
    if metrics.complexity_score and metrics.complexity_score > 10:
        suggestions.append("High complexity detected — consider simplifying")

    return AnalysisResult(
        language=CodeLanguage.PYTHON,
        syntax_valid=syntax_valid,
        issues=issues,
        metrics=metrics,
        suggestions=suggestions,
    )


def _analyze_generic(code: str, language: CodeLanguage) -> AnalysisResult:
    """Analyze non-Python code using line-based heuristics."""
    metrics = _compute_line_metrics(code)
    issues: list[AnalysisIssue] = []
    suggestions: list[str] = []

    # Basic checks
    if language == CodeLanguage.JSON:
        try:
            import json
            json.loads(code)
        except (json.JSONDecodeError, ValueError) as exc:
            issues.append(
                AnalysisIssue(
                    severity=AnalysisSeverity.ERROR,
                    message=f"Invalid JSON: {exc}",
                    rule="syntax",
                )
            )
            return AnalysisResult(
                language=language,
                syntax_valid=False,
                issues=issues,
                metrics=metrics,
                suggestions=suggestions,
            )

    # Line length check
    for i, line in enumerate(code.splitlines(), 1):
        if len(line) > 120:
            issues.append(
                AnalysisIssue(
                    severity=AnalysisSeverity.WARNING,
                    message=f"Line exceeds 120 characters ({len(line)})",
                    line=i,
                    rule="line-length",
                )
            )
            if len(issues) >= 10:  # Cap issues
                break

    if metrics.total_lines > 300:
        suggestions.append("File is quite long — consider splitting into modules")

    return AnalysisResult(
        language=language,
        syntax_valid=len([i for i in issues if i.severity == AnalysisSeverity.ERROR]) == 0,
        issues=issues,
        metrics=metrics,
        suggestions=suggestions,
    )


def _compute_line_metrics(code: str) -> CodeMetrics:
    """Compute basic line-based metrics."""
    lines = code.splitlines()
    total = len(lines)
    blank = sum(1 for line in lines if not line.strip())
    comment = sum(1 for line in lines if line.strip().startswith("#"))
    code_lines = total - blank - comment

    return CodeMetrics(
        total_lines=total,
        code_lines=code_lines,
        comment_lines=comment,
        blank_lines=blank,
    )


def _count_branches(node: ast.AST) -> int:
    """Count branching statements for complexity estimation."""
    count = 0
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
            count += 1
        elif isinstance(child, (ast.And, ast.Or)):
            count += 1
    return count


def _check_python_patterns(code: str, tree: ast.Module) -> list[AnalysisIssue]:
    """Check for common Python anti-patterns."""
    issues: list[AnalysisIssue] = []

    for node in ast.walk(tree):
        # Bare except
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append(
                AnalysisIssue(
                    severity=AnalysisSeverity.WARNING,
                    message="Bare 'except:' catches all exceptions — be specific",
                    line=node.lineno,
                    rule="bare-except",
                )
            )

        # Mutable default arguments
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in node.args.defaults + node.args.kw_defaults:
                if default is not None and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    issues.append(
                        AnalysisIssue(
                            severity=AnalysisSeverity.WARNING,
                            message=f"Mutable default argument in '{node.name}()' — use None instead",
                            line=node.lineno,
                            rule="mutable-default",
                        )
                    )

        # Global statement
        if isinstance(node, ast.Global):
            issues.append(
                AnalysisIssue(
                    severity=AnalysisSeverity.INFO,
                    message="Global statement used — consider alternatives",
                    line=node.lineno,
                    rule="global-statement",
                )
            )

    # Check for TODO/FIXME/HACK comments
    for i, line in enumerate(code.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            upper = stripped.upper()
            if "TODO" in upper:
                issues.append(
                    AnalysisIssue(
                        severity=AnalysisSeverity.INFO,
                        message="TODO comment found",
                        line=i,
                        rule="todo",
                    )
                )
            elif "FIXME" in upper or "HACK" in upper:
                issues.append(
                    AnalysisIssue(
                        severity=AnalysisSeverity.WARNING,
                        message="FIXME/HACK comment found",
                        line=i,
                        rule="fixme",
                    )
                )

    return issues
