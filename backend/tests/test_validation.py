"""
Tests for system validation module.

Tests:
- ARM64 architecture check
- macOS platform check
- Python version check
- Rosetta detection
- Ollama reachability (mocked)
- Full validation suite
"""

from __future__ import annotations

import platform
import sys
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.core.validation import (
    SystemValidation,
    ValidationResult,
    check_architecture,
    check_ollama,
    check_platform,
    check_python_version,
    check_rosetta,
    run_all_checks,
    run_sync_checks,
)


class TestArchitectureCheck:
    """Tests for ARM64 architecture validation."""

    def test_architecture_is_arm64(self):
        """Verify check passes on ARM64."""
        result = check_architecture()
        assert result.name == "architecture"
        if platform.machine() == "arm64":
            assert result.passed is True
            assert "arm64" in result.message
        else:
            assert result.passed is False

    def test_architecture_result_type(self):
        """Verify result is proper type."""
        result = check_architecture()
        assert isinstance(result, ValidationResult)


class TestPlatformCheck:
    """Tests for macOS platform validation."""

    def test_platform_is_darwin(self):
        """Verify check passes on macOS."""
        result = check_platform()
        assert result.name == "platform"
        if sys.platform == "darwin":
            assert result.passed is True
            assert "darwin" in result.message
        else:
            assert result.passed is False

    def test_platform_result_type(self):
        """Verify result is proper type."""
        result = check_platform()
        assert isinstance(result, ValidationResult)


class TestPythonVersionCheck:
    """Tests for Python version validation."""

    def test_python_version_311_plus(self):
        """Verify check passes on Python 3.11+."""
        result = check_python_version()
        assert result.name == "python_version"
        if sys.version_info >= (3, 11):
            assert result.passed is True
        else:
            assert result.passed is False

    def test_python_version_message_contains_version(self):
        """Verify version string is in message."""
        result = check_python_version()
        version_str = f"{sys.version_info.major}.{sys.version_info.minor}"
        assert version_str in result.message


class TestRosettaCheck:
    """Tests for Rosetta translation detection."""

    def test_rosetta_check_runs(self):
        """Verify Rosetta check completes without error."""
        result = check_rosetta()
        assert result.name == "rosetta"
        assert isinstance(result.passed, bool)

    def test_rosetta_not_translated_on_arm64(self):
        """On native ARM64, Rosetta should not be detected."""
        if platform.machine() == "arm64":
            result = check_rosetta()
            assert result.passed is True


class TestOllamaCheck:
    """Tests for Ollama reachability (mocked)."""

    @pytest.mark.asyncio
    async def test_ollama_reachable(self):
        """Test Ollama reachable scenario (mocked)."""
        import httpx

        mock_response = httpx.Response(
            status_code=200,
            json={"models": [{"name": "llama3:8b"}]},
            request=httpx.Request("GET", "http://localhost:11434/api/tags"),
        )

        async def mock_get(*args, **kwargs):
            return mock_response

        with patch("backend.app.core.validation.httpx.AsyncClient") as mock_client_cls:
            mock_instance = AsyncMock()
            mock_instance.get = mock_get
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await check_ollama("http://localhost:11434")
            assert result.name == "ollama"
            assert result.passed is True
            assert "1 models available" in result.message

    @pytest.mark.asyncio
    async def test_ollama_unreachable(self):
        """Test Ollama unreachable scenario (mocked)."""
        import httpx

        async def mock_get(*args, **kwargs):
            raise httpx.ConnectError("Connection refused")

        with patch("backend.app.core.validation.httpx.AsyncClient") as mock_client_cls:
            mock_instance = AsyncMock()
            mock_instance.get = mock_get
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await check_ollama("http://localhost:11434")
            assert result.name == "ollama"
            assert result.passed is False
            assert "not reachable" in result.message

    @pytest.mark.asyncio
    async def test_ollama_timeout(self):
        """Test Ollama timeout scenario (mocked)."""
        import httpx

        async def mock_get(*args, **kwargs):
            raise httpx.TimeoutException("Timed out")

        with patch("backend.app.core.validation.httpx.AsyncClient") as mock_client_cls:
            mock_instance = AsyncMock()
            mock_instance.get = mock_get
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await check_ollama("http://localhost:11434")
            assert result.name == "ollama"
            assert result.passed is False
            assert "timed out" in result.message


class TestSyncChecks:
    """Tests for synchronous validation suite."""

    def test_sync_checks_returns_list(self):
        """Verify sync checks return a list of results."""
        results = run_sync_checks()
        assert isinstance(results, list)
        assert len(results) == 4

    def test_sync_checks_all_named(self):
        """Verify all sync checks have names."""
        results = run_sync_checks()
        names = {r.name for r in results}
        assert "architecture" in names
        assert "platform" in names
        assert "python_version" in names
        assert "rosetta" in names


class TestFullValidation:
    """Tests for complete validation suite."""

    @pytest.mark.asyncio
    async def test_full_validation_returns_system_validation(self):
        """Verify full validation returns proper type."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": []}

        with patch("backend.app.core.validation.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            validation = await run_all_checks()
            assert isinstance(validation, SystemValidation)
            assert len(validation.checks) == 5

    @pytest.mark.asyncio
    async def test_validation_summary(self):
        """Verify validation summary structure."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": []}

        with patch("backend.app.core.validation.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            validation = await run_all_checks()
            summary = validation.summary
            assert "all_passed" in summary
            assert "total" in summary
            assert "passed" in summary
            assert "failed" in summary
            assert "checks" in summary
            assert summary["total"] == 5
