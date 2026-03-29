"""
Fleet MCP proxy API — forwards requests to the fleet-mcp-server SSE instance.

The fleet-mcp-server runs on http://127.0.0.1:3100 in SSE mode and exposes
REST endpoints that this module proxies into the ai-dash-macOS backend.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fleet", tags=["fleet"])

FLEET_BASE = "http://127.0.0.1:3100"


async def _proxy_get(path: str) -> Any:
    """Forward a GET request to the fleet-mcp REST API."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{FLEET_BASE}{path}")
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Fleet MCP server is not running. Start it with: npm run start:sse",
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=str(exc))
    except Exception as exc:
        logger.error("Fleet proxy error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


async def _proxy_post(path: str, body: dict | None = None) -> Any:
    """Forward a POST request to the fleet-mcp REST API."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{FLEET_BASE}{path}", json=body or {})
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Fleet MCP server is not running. Start it with: npm run start:sse",
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=str(exc))
    except Exception as exc:
        logger.error("Fleet proxy error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Fleet Overview ────────────────────────────────────────────────────────────


@router.get("/status")
async def fleet_status():
    """Aggregate fleet status — online/offline for each device."""
    return await _proxy_get("/api/fleet/status")


@router.get("/devices")
async def fleet_devices():
    """List all configured devices."""
    return await _proxy_get("/api/fleet/devices")


@router.get("/health")
async def fleet_health():
    """Fleet MCP server health check."""
    return await _proxy_get("/health")


# ── Local Mac ─────────────────────────────────────────────────────────────────


@router.get("/local/info")
async def local_info():
    """Local Mac system information."""
    return await _proxy_get("/api/fleet/local/info")


@router.get("/local/cpu")
async def local_cpu():
    """Local Mac CPU usage."""
    return await _proxy_get("/api/fleet/local/cpu")


@router.get("/local/memory")
async def local_memory():
    """Local Mac memory usage."""
    return await _proxy_get("/api/fleet/local/memory")


@router.get("/local/disk")
async def local_disk():
    """Local Mac disk usage."""
    return await _proxy_get("/api/fleet/local/disk")


@router.get("/local/battery")
async def local_battery():
    """Local Mac battery status."""
    return await _proxy_get("/api/fleet/local/battery")


# ── Remote Devices ────────────────────────────────────────────────────────────


@router.post("/remote/exec")
async def remote_exec(body: dict):
    """Execute a command on a remote device (SSH)."""
    return await _proxy_post("/api/fleet/remote/exec", body)
