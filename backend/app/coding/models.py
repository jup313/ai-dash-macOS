"""
Coding engine data models — code generation, analysis, execution, file ops.

Provider-agnostic data structures for the coding engine.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class CodeLanguage(str, Enum):
    """Supported programming languages."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    BASH = "bash"
    HTML = "html"
    CSS = "css"
    JSON = "json"
    YAML = "yaml"
    MARKDOWN = "markdown"
    SQL = "sql"
    UNKNOWN = "unknown"


class CodeAction(str, Enum):
    """Code generation actions."""

    GENERATE = "generate"
    REFACTOR = "refactor"
    EXPLAIN = "explain"
    FIX = "fix"
    TEST = "test"
    DOCUMENT = "document"


class CodeRequest(BaseModel):
    """Request for code generation or transformation."""

    action: CodeAction = Field(
        default=CodeAction.GENERATE,
        description="Code action to perform",
    )
    prompt: str = Field(
        ...,
        min_length=1,
        description="Description of what to generate/transform",
    )
    code: str = Field(
        default="",
        description="Existing code (for refactor/explain/fix actions)",
    )
    language: CodeLanguage = Field(
        default=CodeLanguage.PYTHON,
        description="Target programming language",
    )
    model: Optional[str] = Field(
        default=None,
        description="Model override",
    )
    provider: Optional[str] = Field(
        default=None,
        description="Provider override",
    )
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Lower temperature for code accuracy",
    )
    max_tokens: Optional[int] = Field(
        default=4096,
        ge=1,
        le=32768,
    )


class CodeResult(BaseModel):
    """Result of a code generation or transformation."""

    action: CodeAction
    code: str = ""
    language: CodeLanguage = CodeLanguage.UNKNOWN
    explanation: str = ""
    model_used: str = ""
    provider_used: str = ""
    tokens_used: Optional[int] = None
    duration_ms: Optional[float] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class AnalysisSeverity(str, Enum):
    """Code analysis issue severity."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"


class AnalysisIssue(BaseModel):
    """A single code analysis issue."""

    severity: AnalysisSeverity
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    rule: str = ""


class CodeMetrics(BaseModel):
    """Code complexity and size metrics."""

    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    functions: int = 0
    classes: int = 0
    imports: int = 0
    complexity_score: Optional[float] = None


class AnalysisResult(BaseModel):
    """Result of static code analysis."""

    language: CodeLanguage
    syntax_valid: bool = True
    issues: list[AnalysisIssue] = Field(default_factory=list)
    metrics: CodeMetrics = Field(default_factory=CodeMetrics)
    suggestions: list[str] = Field(default_factory=list)


class ExecutionRequest(BaseModel):
    """Request for code execution."""

    code: str = Field(
        ...,
        min_length=1,
        description="Code to execute",
    )
    language: CodeLanguage = Field(
        default=CodeLanguage.PYTHON,
        description="Language of the code",
    )
    timeout_seconds: int = Field(
        default=30,
        ge=1,
        le=120,
        description="Execution timeout",
    )
    stdin: str = Field(
        default="",
        description="Standard input to provide",
    )


class ExecutionResult(BaseModel):
    """Result of code execution."""

    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    timed_out: bool = False
    duration_ms: float = 0.0
    language: CodeLanguage = CodeLanguage.UNKNOWN


class FileInfo(BaseModel):
    """Information about a file."""

    path: str
    name: str
    extension: str = ""
    size_bytes: int = 0
    is_directory: bool = False
    language: CodeLanguage = CodeLanguage.UNKNOWN
    modified_at: Optional[datetime] = None


class FileReadResult(BaseModel):
    """Result of reading a file."""

    path: str
    content: str
    language: CodeLanguage = CodeLanguage.UNKNOWN
    size_bytes: int = 0


class FileWriteRequest(BaseModel):
    """Request to write a file."""

    path: str = Field(
        ...,
        min_length=1,
        description="Relative path within sandbox",
    )
    content: str = Field(
        ...,
        description="File content to write",
    )
    create_dirs: bool = Field(
        default=True,
        description="Create parent directories if needed",
    )


class FileWriteResult(BaseModel):
    """Result of writing a file."""

    path: str
    size_bytes: int
    created: bool = False
    overwritten: bool = False
