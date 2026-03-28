"""
File manager — safe file operations within a sandbox directory.

Security:
- All paths resolved relative to a sandbox root
- Path traversal protection (no escaping sandbox)
- File size limits enforced
- Only text files allowed
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from backend.app.coding.analyzer import detect_language
from backend.app.coding.models import (
    FileInfo,
    FileReadResult,
    FileWriteRequest,
    FileWriteResult,
)

logger = logging.getLogger(__name__)

# Default sandbox directory
DEFAULT_SANDBOX = "/tmp/ai-dash-sandbox"

# Limits
MAX_FILE_SIZE_BYTES = 1_000_000  # 1 MB
MAX_FILES_PER_LIST = 500


class FileManager:
    """
    Manages file operations within a sandboxed directory.

    All paths are resolved relative to the sandbox root.
    Path traversal attempts are blocked.
    """

    def __init__(self, sandbox_root: str | None = None) -> None:
        self._root = Path(sandbox_root or DEFAULT_SANDBOX)
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def _resolve_safe(self, relative_path: str) -> Path:
        """
        Resolve a relative path safely within the sandbox.

        Raises:
            ValueError: If path escapes the sandbox.
        """
        # Clean the path
        clean = relative_path.lstrip("/").lstrip("\\")
        resolved = (self._root / clean).resolve()

        # Security: ensure resolved path is under root
        try:
            resolved.relative_to(self._root.resolve())
        except ValueError:
            raise ValueError(
                f"Path traversal blocked: '{relative_path}' escapes sandbox"
            )

        return resolved

    def read_file(self, path: str) -> FileReadResult:
        """
        Read a file from the sandbox.

        Args:
            path: Relative path within sandbox.

        Returns:
            FileReadResult with content and metadata.

        Raises:
            FileNotFoundError: If file does not exist.
            ValueError: If path escapes sandbox or file too large.
        """
        resolved = self._resolve_safe(path)

        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if not resolved.is_file():
            raise ValueError(f"Not a file: {path}")

        size = resolved.stat().st_size
        if size > MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"File too large: {size} bytes (max {MAX_FILE_SIZE_BYTES})"
            )

        content = resolved.read_text(encoding="utf-8")
        language = detect_language(resolved.name)

        return FileReadResult(
            path=str(resolved.relative_to(self._root.resolve())),
            content=content,
            language=language,
            size_bytes=size,
        )

    def write_file(self, request: FileWriteRequest) -> FileWriteResult:
        """
        Write a file to the sandbox.

        Args:
            request: Write request with path, content, and options.

        Returns:
            FileWriteResult with metadata.

        Raises:
            ValueError: If path escapes sandbox or content too large.
        """
        resolved = self._resolve_safe(request.path)

        # Size check
        content_size = len(request.content.encode("utf-8"))
        if content_size > MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"Content too large: {content_size} bytes (max {MAX_FILE_SIZE_BYTES})"
            )

        # Track if creating or overwriting
        existed = resolved.exists()

        # Create directories if needed
        if request.create_dirs:
            resolved.parent.mkdir(parents=True, exist_ok=True)

        resolved.write_text(request.content, encoding="utf-8")

        rel_path = str(resolved.relative_to(self._root.resolve()))
        logger.info("Wrote file: %s (%d bytes)", rel_path, content_size)

        return FileWriteResult(
            path=rel_path,
            size_bytes=content_size,
            created=not existed,
            overwritten=existed,
        )

    def delete_file(self, path: str) -> bool:
        """
        Delete a file from the sandbox.

        Returns True if the file was deleted, False if not found.
        """
        resolved = self._resolve_safe(path)
        if resolved.exists() and resolved.is_file():
            resolved.unlink()
            logger.info("Deleted file: %s", path)
            return True
        return False

    def list_files(self, directory: str = "") -> list[FileInfo]:
        """
        List files in a sandbox directory.

        Args:
            directory: Relative directory path (empty = root).

        Returns:
            List of FileInfo objects.
        """
        resolved = self._resolve_safe(directory) if directory else self._root.resolve()

        if not resolved.exists():
            return []

        if not resolved.is_dir():
            return []

        results: list[FileInfo] = []
        count = 0

        for item in sorted(resolved.iterdir()):
            if count >= MAX_FILES_PER_LIST:
                break

            try:
                stat = item.stat()
                is_dir = item.is_dir()
                rel_path = str(item.relative_to(self._root.resolve()))
                language = detect_language(item.name) if not is_dir else None

                results.append(
                    FileInfo(
                        path=rel_path,
                        name=item.name,
                        extension=item.suffix,
                        size_bytes=stat.st_size if not is_dir else 0,
                        is_directory=is_dir,
                        language=language,
                        modified_at=datetime.fromtimestamp(
                            stat.st_mtime, tz=timezone.utc
                        ),
                    )
                )
                count += 1
            except (PermissionError, OSError):
                continue

        return results

    def file_exists(self, path: str) -> bool:
        """Check if a file exists in the sandbox."""
        try:
            resolved = self._resolve_safe(path)
            return resolved.exists() and resolved.is_file()
        except ValueError:
            return False

    def get_info(self, path: str) -> FileInfo | None:
        """Get file info for a path in the sandbox."""
        try:
            resolved = self._resolve_safe(path)
        except ValueError:
            return None

        if not resolved.exists():
            return None

        stat = resolved.stat()
        is_dir = resolved.is_dir()

        return FileInfo(
            path=str(resolved.relative_to(self._root.resolve())),
            name=resolved.name,
            extension=resolved.suffix,
            size_bytes=stat.st_size if not is_dir else 0,
            is_directory=is_dir,
            language=detect_language(resolved.name) if not is_dir else None,
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        )


# Singleton
_file_manager: FileManager | None = None


def get_file_manager() -> FileManager:
    """Get or create the file manager singleton."""
    global _file_manager
    if _file_manager is None:
        _file_manager = FileManager()
    return _file_manager


def reset_file_manager() -> None:
    """Reset the file manager singleton (for testing)."""
    global _file_manager
    _file_manager = None
