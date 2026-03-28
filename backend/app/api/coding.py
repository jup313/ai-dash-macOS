"""
Coding API endpoints — code generation, analysis, execution, and file management.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from backend.app.coding.analyzer import analyze_code
from backend.app.coding.executor import execute_code
from backend.app.coding.file_manager import get_file_manager
from backend.app.coding.generator import generate_code
from backend.app.coding.models import (
    AnalysisResult,
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/coding", tags=["coding"])


# ── Code Generation ────────────────────────────────────────────────────────────


@router.post("/generate", response_model=CodeResult)
async def api_generate_code(request: CodeRequest) -> CodeResult:
    """Generate, refactor, explain, fix, test, or document code via LLM."""
    try:
        return await generate_code(request)
    except Exception as exc:
        logger.error("Code generation error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Code Analysis ──────────────────────────────────────────────────────────────


@router.post("/analyze", response_model=AnalysisResult)
async def api_analyze_code(
    code: str,
    language: CodeLanguage = CodeLanguage.PYTHON,
) -> AnalysisResult:
    """Analyze code for issues, metrics, and suggestions."""
    try:
        return analyze_code(code, language)
    except Exception as exc:
        logger.error("Code analysis error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Code Execution ─────────────────────────────────────────────────────────────


@router.post("/execute", response_model=ExecutionResult)
async def api_execute_code(request: ExecutionRequest) -> ExecutionResult:
    """Execute code in a sandboxed subprocess."""
    try:
        return await execute_code(request)
    except Exception as exc:
        logger.error("Code execution error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── File Management ────────────────────────────────────────────────────────────


@router.get("/files", response_model=list[FileInfo])
async def list_files(directory: str = "") -> list[FileInfo]:
    """List files in the sandbox directory."""
    try:
        fm = get_file_manager()
        return fm.list_files(directory)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/files/read", response_model=FileReadResult)
async def read_file(path: str = Query(..., description="Relative file path")) -> FileReadResult:
    """Read a file from the sandbox."""
    try:
        fm = get_file_manager()
        return fm.read_file(path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/files/write", response_model=FileWriteResult)
async def write_file(request: FileWriteRequest) -> FileWriteResult:
    """Write a file to the sandbox."""
    try:
        fm = get_file_manager()
        return fm.write_file(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/files")
async def delete_file(path: str = Query(..., description="Relative file path")) -> dict:
    """Delete a file from the sandbox."""
    try:
        fm = get_file_manager()
        if not fm.delete_file(path):
            raise HTTPException(status_code=404, detail=f"File not found: {path}")
        return {"deleted": True, "path": path}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
