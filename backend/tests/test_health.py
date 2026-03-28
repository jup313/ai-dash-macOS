"""
Tests for health check endpoint.

Tests:
- Health endpoint returns 200
- Response schema validation
- Platform information present
- Memory metrics present
- Config information present
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_health_endpoint_returns_200(async_client):
    """Health endpoint should return HTTP 200."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"models": []}

    with patch("backend.app.core.validation.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        response = await async_client.get("/health")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_has_status(async_client):
    """Health response must include status field."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"models": []}

    with patch("backend.app.core.validation.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        response = await async_client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] in ("healthy", "degraded")


@pytest.mark.asyncio
async def test_health_response_has_platform(async_client):
    """Health response must include platform information."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"models": []}

    with patch("backend.app.core.validation.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        response = await async_client.get("/health")
        data = response.json()
        assert "platform" in data
        platform_data = data["platform"]
        assert "arch" in platform_data
        assert "os" in platform_data
        assert "python" in platform_data
        assert "rosetta" in platform_data


@pytest.mark.asyncio
async def test_health_response_has_memory(async_client):
    """Health response must include memory metrics."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"models": []}

    with patch("backend.app.core.validation.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        response = await async_client.get("/health")
        data = response.json()
        assert "memory" in data
        memory_data = data["memory"]
        assert "total_gb" in memory_data
        assert "available_gb" in memory_data
        assert "percent_used" in memory_data
        assert "heavy_model_allowed" in memory_data
        assert "status" in memory_data


@pytest.mark.asyncio
async def test_health_response_has_ollama(async_client):
    """Health response must include Ollama status."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"models": []}

    with patch("backend.app.core.validation.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        response = await async_client.get("/health")
        data = response.json()
        assert "ollama" in data
        ollama_data = data["ollama"]
        assert "reachable" in ollama_data
        assert "url" in ollama_data


@pytest.mark.asyncio
async def test_health_response_has_config(async_client):
    """Health response must include configuration status."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"models": []}

    with patch("backend.app.core.validation.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        response = await async_client.get("/health")
        data = response.json()
        assert "config" in data
        config_data = data["config"]
        assert "loaded" in config_data
        assert config_data["loaded"] is True
        assert "provider" in config_data


@pytest.mark.asyncio
async def test_health_response_has_version(async_client):
    """Health response must include version."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"models": []}

    with patch("backend.app.core.validation.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        response = await async_client.get("/health")
        data = response.json()
        assert "version" in data
        assert data["version"] == "0.1.0"
