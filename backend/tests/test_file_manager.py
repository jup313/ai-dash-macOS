"""Tests for the file manager."""

from __future__ import annotations

import shutil
import tempfile

import pytest

from backend.app.coding.file_manager import (
    FileManager,
    get_file_manager,
    reset_file_manager,
)
from backend.app.coding.models import CodeLanguage, FileWriteRequest


@pytest.fixture()
def sandbox(tmp_path):
    """Create a temporary sandbox directory."""
    return FileManager(sandbox_root=str(tmp_path))


class TestFileManager:
    def test_root_created(self, sandbox):
        assert sandbox.root.exists()

    def test_write_and_read(self, sandbox):
        req = FileWriteRequest(path="hello.py", content="print('hi')")
        result = sandbox.write_file(req)
        assert result.created is True
        assert result.size_bytes > 0

        read = sandbox.read_file("hello.py")
        assert read.content == "print('hi')"
        assert read.language == CodeLanguage.PYTHON

    def test_overwrite(self, sandbox):
        req = FileWriteRequest(path="file.txt", content="v1")
        sandbox.write_file(req)

        req2 = FileWriteRequest(path="file.txt", content="v2")
        result = sandbox.write_file(req2)
        assert result.overwritten is True

        read = sandbox.read_file("file.txt")
        assert read.content == "v2"

    def test_write_creates_dirs(self, sandbox):
        req = FileWriteRequest(path="sub/dir/file.py", content="x=1")
        result = sandbox.write_file(req)
        assert result.created is True

        read = sandbox.read_file("sub/dir/file.py")
        assert read.content == "x=1"

    def test_read_nonexistent(self, sandbox):
        with pytest.raises(FileNotFoundError):
            sandbox.read_file("nope.py")

    def test_delete_file(self, sandbox):
        req = FileWriteRequest(path="delete_me.py", content="bye")
        sandbox.write_file(req)
        assert sandbox.delete_file("delete_me.py") is True
        assert sandbox.file_exists("delete_me.py") is False

    def test_delete_nonexistent(self, sandbox):
        assert sandbox.delete_file("nope.py") is False

    def test_file_exists(self, sandbox):
        assert sandbox.file_exists("nope.py") is False
        req = FileWriteRequest(path="exists.py", content="x")
        sandbox.write_file(req)
        assert sandbox.file_exists("exists.py") is True

    def test_list_files_empty(self, sandbox):
        files = sandbox.list_files()
        assert files == []

    def test_list_files(self, sandbox):
        sandbox.write_file(FileWriteRequest(path="a.py", content="a"))
        sandbox.write_file(FileWriteRequest(path="b.js", content="b"))
        files = sandbox.list_files()
        assert len(files) == 2
        names = {f.name for f in files}
        assert names == {"a.py", "b.js"}

    def test_list_files_subdirectory(self, sandbox):
        sandbox.write_file(FileWriteRequest(path="sub/c.py", content="c"))
        files = sandbox.list_files("sub")
        assert len(files) == 1
        assert files[0].name == "c.py"

    def test_get_info(self, sandbox):
        sandbox.write_file(FileWriteRequest(path="info.py", content="x=1"))
        info = sandbox.get_info("info.py")
        assert info is not None
        assert info.name == "info.py"
        assert info.extension == ".py"
        assert info.language == CodeLanguage.PYTHON

    def test_get_info_nonexistent(self, sandbox):
        assert sandbox.get_info("nope.py") is None

    def test_path_traversal_blocked(self, sandbox):
        with pytest.raises(ValueError, match="traversal"):
            sandbox.read_file("../../etc/passwd")

    def test_path_traversal_write_blocked(self, sandbox):
        with pytest.raises(ValueError, match="traversal"):
            sandbox.write_file(FileWriteRequest(path="../../evil.py", content="x"))

    def test_path_traversal_exists_returns_false(self, sandbox):
        assert sandbox.file_exists("../../etc/passwd") is False


class TestFileManagerSingleton:
    def test_singleton(self):
        reset_file_manager()
        fm1 = get_file_manager()
        fm2 = get_file_manager()
        assert fm1 is fm2
        reset_file_manager()

    def test_reset(self):
        reset_file_manager()
        fm1 = get_file_manager()
        reset_file_manager()
        fm2 = get_file_manager()
        assert fm1 is not fm2
        reset_file_manager()
