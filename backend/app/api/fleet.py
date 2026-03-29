"""
Fleet MCP proxy API — forwards requests to the fleet-mcp-server SSE instance.

The fleet-mcp-server runs on http://127.0.0.1:3100 in SSE mode and exposes
REST endpoints that this module proxies into the ai-dash-macOS backend.
"""

from __future__ import annotations

import json
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


# ── Fleet Context Helper (for chat agent) ─────────────────────────────────────


async def fetch_fleet_context(query: str) -> str | None:
    """
    Fetch real-time fleet data relevant to a user's chat query.

    Called by the conversations chat endpoint when it detects fleet-related
    keywords. Returns a formatted context string the LLM can reference,
    or None if the fleet server is unavailable.
    """
    query_lower = query.lower()
    sections: list[str] = []

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Always get fleet overview for fleet questions
            status_resp = await client.get(f"{FLEET_BASE}/api/fleet/status")
            if status_resp.status_code == 200:
                status = status_resp.json()
                sections.append(f"Fleet Status: {json.dumps(status, indent=2)}")

            # UniFi-specific queries
            unifi_keywords = [
                "unifi", "dream machine", "udm", "network", "wifi", "wan",
                "internet", "client", "connected", "firewall", "router",
                "gateway", "access point", "switch",
            ]
            if any(kw in query_lower for kw in unifi_keywords):
                # System info
                sys_resp = await client.get(f"{FLEET_BASE}/api/fleet/unifi/system")
                if sys_resp.status_code == 200:
                    sections.append(f"UniFi System: {json.dumps(sys_resp.json(), indent=2)}")

                # Network health
                health_resp = await client.get(f"{FLEET_BASE}/api/fleet/unifi/health")
                if health_resp.status_code == 200:
                    sections.append(f"Network Health: {json.dumps(health_resp.json(), indent=2)}")

                # WAN/internet status
                if any(kw in query_lower for kw in ["wan", "internet", "uplink", "connection"]):
                    wan_resp = await client.get(f"{FLEET_BASE}/api/fleet/unifi/wan")
                    if wan_resp.status_code == 200:
                        sections.append(f"WAN Status: {json.dumps(wan_resp.json(), indent=2)}")

                # Connected clients
                if any(kw in query_lower for kw in ["client", "connected", "device"]):
                    clients_resp = await client.get(f"{FLEET_BASE}/api/fleet/unifi/clients")
                    if clients_resp.status_code == 200:
                        sections.append(f"Connected Clients: {json.dumps(clients_resp.json(), indent=2)}")

                # Network devices (APs, switches)
                devices_resp = await client.get(f"{FLEET_BASE}/api/fleet/unifi/devices")
                if devices_resp.status_code == 200:
                    sections.append(f"UniFi Devices: {json.dumps(devices_resp.json(), indent=2)}")

                # WiFi networks
                if any(kw in query_lower for kw in ["wifi", "ssid", "wireless"]):
                    wifi_resp = await client.get(f"{FLEET_BASE}/api/fleet/unifi/wifi")
                    if wifi_resp.status_code == 200:
                        sections.append(f"WiFi Networks: {json.dumps(wifi_resp.json(), indent=2)}")

            # Local Mac queries
            mac_keywords = ["local mac", "this mac", "my mac", "cpu", "memory", "disk", "battery"]
            if any(kw in query_lower for kw in mac_keywords):
                info_resp = await client.get(f"{FLEET_BASE}/api/fleet/local/info")
                if info_resp.status_code == 200:
                    sections.append(f"Local Mac: {json.dumps(info_resp.json(), indent=2)}")

                if any(kw in query_lower for kw in ["cpu", "processor"]):
                    cpu_resp = await client.get(f"{FLEET_BASE}/api/fleet/local/cpu")
                    if cpu_resp.status_code == 200:
                        sections.append(f"CPU: {json.dumps(cpu_resp.json(), indent=2)}")

                if any(kw in query_lower for kw in ["memory", "ram"]):
                    mem_resp = await client.get(f"{FLEET_BASE}/api/fleet/local/memory")
                    if mem_resp.status_code == 200:
                        sections.append(f"Memory: {json.dumps(mem_resp.json(), indent=2)}")

                if any(kw in query_lower for kw in ["disk", "storage", "space"]):
                    disk_resp = await client.get(f"{FLEET_BASE}/api/fleet/local/disk")
                    if disk_resp.status_code == 200:
                        sections.append(f"Disk: {json.dumps(disk_resp.json(), indent=2)}")

    except httpx.ConnectError:
        logger.warning("Fleet MCP server not available for context injection")
        return None
    except Exception as exc:
        logger.error("Fleet context fetch error: %s", exc)
        return None

    if not sections:
        return None

    return (
        "=== LIVE FLEET DATA (real-time from your network) ===\n\n"
        + "\n\n".join(sections)
        + "\n\n=== END FLEET DATA ===\n"
        "Use the data above to answer the user's question accurately."
    )


# ── Fleet keyword detection ───────────────────────────────────────────────────

FLEET_KEYWORDS = [
    "fleet", "device", "unifi", "dream machine", "udm", "network",
    "wifi", "wan", "internet", "client", "connected", "firewall",
    "router", "gateway", "access point", "switch", "qnap", "nas",
    "local mac", "this mac", "my mac", "cpu usage", "memory usage",
    "disk usage", "battery", "server", "remote", "mac mini", "rocky",
    "status", "online", "offline", "uptime",
]


def is_fleet_query(text: str) -> bool:
    """Check if a user message is asking about fleet/network/device info."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in FLEET_KEYWORDS)


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


# ── UniFi Dream Machine ──────────────────────────────────────────────────────


@router.get("/unifi/system")
async def unifi_system():
    """UniFi Dream Machine system info (model, firmware, uptime)."""
    return await _proxy_get("/api/fleet/unifi/system")


@router.get("/unifi/health")
async def unifi_health():
    """UniFi network health summary."""
    return await _proxy_get("/api/fleet/unifi/health")


@router.get("/unifi/clients")
async def unifi_clients():
    """List connected network clients."""
    return await _proxy_get("/api/fleet/unifi/clients")


@router.get("/unifi/devices")
async def unifi_devices():
    """List UniFi network devices (APs, switches, gateways)."""
    return await _proxy_get("/api/fleet/unifi/devices")


@router.get("/unifi/wan")
async def unifi_wan():
    """UniFi WAN/internet uplink status."""
    return await _proxy_get("/api/fleet/unifi/wan")


@router.get("/unifi/wifi")
async def unifi_wifi():
    """List WiFi networks configured on UniFi."""
    return await _proxy_get("/api/fleet/unifi/wifi")


# ── Remote Devices ────────────────────────────────────────────────────────────


@router.post("/remote/exec")
async def remote_exec(body: dict):
    """Execute a command on a remote device (SSH)."""
    return await _proxy_post("/api/fleet/remote/exec", body)
