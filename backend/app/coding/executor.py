"""
Code executor — sandboxed code execution via subprocess.

Security:
- Runs code in subprocess with timeout
- Limited to Python and Bash
- No network access enforcement (subprocess isolation)
- Working directory set to sandbox
- Resource limits via timeout
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
import time
from pathlib import Path

from backend.app.coding.models import CodeLanguage, ExecutionRequest, ExecutionResult

logger = logging.getLogger(__name__)

# Languages that support execution
EXECUTABLE_LANGUAGES = {CodeLanguage.PYTHON, CodeLanguage.BASH}

# Command templates per language
_COMMANDS: dict[CodeLanguage, list[str]] = {
    CodeLanguage.PYTHON: ["python3", "-u"],
    CodeLanguage.BASH: ["bash"],
}


async def execute_code(request: ExecutionRequest) -> ExecutionResult:
    """
    Execute code in a sandboxed subprocess.

    Args:
        request: Execution request with code, language, timeout.

    Returns:
        ExecutionResult with stdout, stderr, exit_code.
    """
    if request.language not in EXECUTABLE_LANGUAGES:
        return ExecutionResult(
            stdout="",
            stderr=f"Language '{request.language.value}' is not executable. "
            f"Supported: {[l.value for l in EXECUTABLE_LANGUAGES]}",
            exit_code=1,
            language=request.language,
        )

    start = time.monotonic()

    # Write code to temp file
    suffix = ".py" if request.language == CodeLanguage.PYTHON else ".sh"
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=suffix,
            delete=False,
            prefix="ai-dash-exec-",
        ) as tmp:
            tmp.write(request.code)
            tmp_path = tmp.name

        # Build command
        cmd = _COMMANDS[request.language] + [tmp_path]

        # Execute
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tempfile.gettempdir(),
            )

            stdin_bytes = request.stdin.encode("utf-8") if request.stdin else None

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(input=stdin_bytes),
                    timeout=request.timeout_seconds,
                )
                timed_out = False
                exit_code = proc.returncode or 0
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                stdout_bytes = b""
                stderr_bytes = f"Execution timed out after {request.timeout_seconds}s".encode()
                timed_out = True
                exit_code = -1

            duration = (time.monotonic() - start) * 1000

            return ExecutionResult(
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
                exit_code=exit_code,
                timed_out=timed_out,
                duration_ms=duration,
                language=request.language,
            )

        except FileNotFoundError:
            duration = (time.monotonic() - start) * 1000
            return ExecutionResult(
                stdout="",
                stderr=f"Runtime not found for {request.language.value}",
                exit_code=1,
                duration_ms=duration,
                language=request.language,
            )

    except Exception as exc:
        duration = (time.monotonic() - start) * 1000
        logger.error("Execution error: %s", exc)
        return ExecutionResult(
            stdout="",
            stderr=f"Execution error: {exc}",
            exit_code=1,
            duration_ms=duration,
            language=request.language,
        )
    finally:
        # Clean up temp file
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except (NameError, OSError):
            pass
