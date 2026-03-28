"""Coding module — AI-powered code generation, analysis, execution, and file management."""

from backend.app.coding.analyzer import analyze_code, detect_language
from backend.app.coding.executor import execute_code
from backend.app.coding.file_manager import FileManager, get_file_manager, reset_file_manager
from backend.app.coding.generator import generate_code
from backend.app.coding.models import (
    AnalysisResult,
    CodeAction,
    CodeLanguage,
    CodeRequest,
    CodeResult,
    ExecutionRequest,
    ExecutionResult,
    FileInfo,
    FileReadResult,
    FileWriteRequest,
    FileWriteResult,
)

__all__ = [
    "analyze_code",
    "detect_language",
    "execute_code",
    "generate_code",
    "FileManager",
    "get_file_manager",
    "reset_file_manager",
    "AnalysisResult",
    "CodeAction",
    "CodeLanguage",
    "CodeRequest",
    "CodeResult",
    "ExecutionRequest",
    "ExecutionResult",
    "FileInfo",
    "FileReadResult",
    "FileWriteRequest",
    "FileWriteResult",
]
