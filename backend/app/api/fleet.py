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
                sys_resp = await client.get(f"{FLEET_BASE}/api/fleet/unifi/system")
                if sys_resp.status_code == 200:
                    sections.append(f"UniFi System: {json.dumps(sys_resp.json(), indent=2)}")

                health_resp = await client.get(f"{FLEET_BASE}/api/fleet/unifi/health")
                if health_resp.status_code == 200:
                    sections.append(f"Network Health: {json.dumps(health_resp.json(), indent=2)}")

                if any(kw in query_lower for kw in ["wan", "internet", "uplink", "connection"]):
                    wan_resp = await client.get(f"{FLEET_BASE}/api/fleet/unifi/wan")
                    if wan_resp.status_code == 200:
                        sections.append(f"WAN Status: {json.dumps(wan_resp.json(), indent=2)}")

                if any(kw in query_lower for kw in ["client", "connected", "device"]):
                    clients_resp = await client.get(f"{FLEET_BASE}/api/fleet/unifi/clients")
                    if clients_resp.status_code == 200:
                        sections.append(f"Connected Clients: {json.dumps(clients_resp.json(), indent=2)}")

                devices_resp = await client.get(f"{FLEET_BASE}/api/fleet/unifi/devices")
                if devices_resp.status_code == 200:
                    sections.append(f"UniFi Devices: {json.dumps(devices_resp.json(), indent=2)}")

                if any(kw in query_lower for kw in ["wifi", "ssid", "wireless"]):
                    wifi_resp = await client.get(f"{FLEET_BASE}/api/fleet/unifi/wifi")
                    if wifi_resp.status_code == 200:
                        sections.append(f"WiFi Networks: {json.dumps(wifi_resp.json(), indent=2)}")

            # Sonos-specific queries
            sonos_keywords = [
                "sonos", "speaker", "music", "playing", "volume",
                "song", "track", "playlist", "favorite", "soundbar",
                "beam", "play", "pause", "mute",
            ]
            if any(kw in query_lower for kw in sonos_keywords):
                discover_resp = await client.get(f"{FLEET_BASE}/api/fleet/sonos/discover")
                if discover_resp.status_code == 200:
                    sections.append(f"Sonos Speakers: {json.dumps(discover_resp.json(), indent=2)}")

                if any(kw in query_lower for kw in ["favorite", "playlist"]):
                    favs_resp = await client.get(f"{FLEET_BASE}/api/fleet/sonos/favorites")
                    if favs_resp.status_code == 200:
                        sections.append(f"Sonos Favorites: {json.dumps(favs_resp.json(), indent=2)}")

            # Alexa-specific queries
            alexa_keywords = [
                "alexa", "echo", "amazon", "smart home", "routine",
                "fire tv", "do not disturb", "dnd", "announce", "announcement",
            ]
            if any(kw in query_lower for kw in alexa_keywords):
                devices_resp = await client.get(f"{FLEET_BASE}/api/fleet/alexa/devices")
                if devices_resp.status_code == 200:
                    sections.append(f"Alexa Devices: {json.dumps(devices_resp.json(), indent=2)}")

                # Tell the LLM what Alexa actions are available
                sections.append(
                    "Alexa Available Actions:\n"
                    "- ANNOUNCE to ALL devices: POST /api/fleet/alexa/announce {text: 'message'}\n"
                    "- ANNOUNCE to ONE device: POST /api/fleet/alexa/announce {text: 'message', serialNumber: 'DEVICE_SERIAL'}\n"
                    "- SPEAK on one device: POST /api/fleet/alexa/speak {serialNumber: 'DEVICE_SERIAL', text: 'message'}\n"
                    "- To announce, you only need the text. No tokens needed — use serialNumber from device list above.\n"
                    "- 'announce' broadcasts to ALL Alexa devices at once. 'speak' sends TTS to just one device."
                )

                if any(kw in query_lower for kw in ["smart home", "light", "plug", "thermostat"]):
                    sh_resp = await client.get(f"{FLEET_BASE}/api/fleet/alexa/smart-home")
                    if sh_resp.status_code == 200:
                        sections.append(f"Smart Home Devices: {json.dumps(sh_resp.json(), indent=2)}")

                if "routine" in query_lower:
                    routines_resp = await client.get(f"{FLEET_BASE}/api/fleet/alexa/routines")
                    if routines_resp.status_code == 200:
                        sections.append(f"Alexa Routines: {json.dumps(routines_resp.json(), indent=2)}")

            # Media Stack queries
            media_keywords = [
                "media", "plex", "sonarr", "radarr", "lidarr", "prowlarr",
                "nzbget", "seerr", "overseerr", "download", "torrent", "usenet",
                "movie", "movies", "tv show", "series", "episode", "season",
                "streaming", "stream", "watching", "library", "indexer",
                "media server", "media stack", "recently added", "calendar",
                "queue", "artist", "album", "request", "requested",
            ]
            if any(kw in query_lower for kw in media_keywords):
                media_resp = await client.get(f"{FLEET_BASE}/api/fleet/media/status")
                if media_resp.status_code == 200:
                    sections.append(f"Media Stack Status: {json.dumps(media_resp.json(), indent=2)}")

                # Plex queries
                if any(kw in query_lower for kw in ["plex", "streaming", "stream", "watching", "library", "recently added"]):
                    sessions_resp = await client.get(f"{FLEET_BASE}/api/fleet/media/plex/sessions")
                    if sessions_resp.status_code == 200:
                        sections.append(f"Plex Active Sessions: {json.dumps(sessions_resp.json(), indent=2)}")

                    libs_resp = await client.get(f"{FLEET_BASE}/api/fleet/media/plex/libraries")
                    if libs_resp.status_code == 200:
                        sections.append(f"Plex Libraries: {json.dumps(libs_resp.json(), indent=2)}")

                    if any(kw in query_lower for kw in ["recently added", "new", "latest"]):
                        recent_resp = await client.get(f"{FLEET_BASE}/api/fleet/media/plex/recent")
                        if recent_resp.status_code == 200:
                            sections.append(f"Plex Recently Added: {json.dumps(recent_resp.json(), indent=2)}")

                # Sonarr queries (TV shows)
                if any(kw in query_lower for kw in ["sonarr", "tv show", "series", "episode", "season"]):
                    sonarr_series = await client.get(f"{FLEET_BASE}/api/fleet/media/sonarr/series")
                    if sonarr_series.status_code == 200:
                        sections.append(f"Sonarr Series: {json.dumps(sonarr_series.json(), indent=2)}")

                    sonarr_queue = await client.get(f"{FLEET_BASE}/api/fleet/media/sonarr/queue")
                    if sonarr_queue.status_code == 200:
                        sections.append(f"Sonarr Queue: {json.dumps(sonarr_queue.json(), indent=2)}")

                    if any(kw in query_lower for kw in ["calendar", "upcoming", "next"]):
                        sonarr_cal = await client.get(f"{FLEET_BASE}/api/fleet/media/sonarr/calendar")
                        if sonarr_cal.status_code == 200:
                            sections.append(f"Sonarr Calendar: {json.dumps(sonarr_cal.json(), indent=2)}")

                # Radarr queries (Movies)
                if any(kw in query_lower for kw in ["radarr", "movie", "movies", "film"]):
                    radarr_movies = await client.get(f"{FLEET_BASE}/api/fleet/media/radarr/movies")
                    if radarr_movies.status_code == 200:
                        sections.append(f"Radarr Movies: {json.dumps(radarr_movies.json(), indent=2)}")

                    radarr_queue = await client.get(f"{FLEET_BASE}/api/fleet/media/radarr/queue")
                    if radarr_queue.status_code == 200:
                        sections.append(f"Radarr Queue: {json.dumps(radarr_queue.json(), indent=2)}")

                    if any(kw in query_lower for kw in ["calendar", "upcoming", "next"]):
                        radarr_cal = await client.get(f"{FLEET_BASE}/api/fleet/media/radarr/calendar")
                        if radarr_cal.status_code == 200:
                            sections.append(f"Radarr Calendar: {json.dumps(radarr_cal.json(), indent=2)}")

                # Lidarr queries (Music)
                if any(kw in query_lower for kw in ["lidarr", "artist", "album"]):
                    lidarr_artists = await client.get(f"{FLEET_BASE}/api/fleet/media/lidarr/artists")
                    if lidarr_artists.status_code == 200:
                        sections.append(f"Lidarr Artists: {json.dumps(lidarr_artists.json(), indent=2)}")

                    lidarr_queue = await client.get(f"{FLEET_BASE}/api/fleet/media/lidarr/queue")
                    if lidarr_queue.status_code == 200:
                        sections.append(f"Lidarr Queue: {json.dumps(lidarr_queue.json(), indent=2)}")

                # Download queries
                if any(kw in query_lower for kw in ["download", "queue", "torrent", "usenet", "nzbget"]):
                    dl_resp = await client.get(f"{FLEET_BASE}/api/fleet/media/downloads")
                    if dl_resp.status_code == 200:
                        sections.append(f"All Downloads: {json.dumps(dl_resp.json(), indent=2)}")

                    nzb_resp = await client.get(f"{FLEET_BASE}/api/fleet/media/nzbget/status")
                    if nzb_resp.status_code == 200:
                        sections.append(f"NZBGet Status: {json.dumps(nzb_resp.json(), indent=2)}")

                # Prowlarr / Indexer queries
                if any(kw in query_lower for kw in ["prowlarr", "indexer"]):
                    idx_resp = await client.get(f"{FLEET_BASE}/api/fleet/media/prowlarr/indexers")
                    if idx_resp.status_code == 200:
                        sections.append(f"Prowlarr Indexers: {json.dumps(idx_resp.json(), indent=2)}")

                # Seerr / Request queries
                if any(kw in query_lower for kw in ["seerr", "overseerr", "request", "requested"]):
                    seerr_resp = await client.get(f"{FLEET_BASE}/api/fleet/media/seerr/requests")
                    if seerr_resp.status_code == 200:
                        sections.append(f"Seerr Requests: {json.dumps(seerr_resp.json(), indent=2)}")

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
    # Sonos
    "sonos", "speaker", "music", "playing", "volume", "song", "track",
    "playlist", "favorite", "soundbar", "beam",
    # Alexa
    "alexa", "echo", "amazon", "smart home", "routine", "fire tv",
    "announce", "announcement",
    # Media Stack
    "media", "plex", "sonarr", "radarr", "lidarr", "prowlarr",
    "nzbget", "seerr", "overseerr", "download", "torrent", "usenet",
    "movie", "movies", "tv show", "series", "episode", "season",
    "streaming", "stream", "watching", "library", "indexer",
    "media server", "media stack", "recently added", "calendar",
    "queue", "artist", "album", "request", "requested",
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


# ── Sonos Speakers ────────────────────────────────────────────────────────────


@router.get("/sonos/discover")
async def sonos_discover():
    """Discover Sonos speakers and their current state."""
    return await _proxy_get("/api/fleet/sonos/discover")


@router.get("/sonos/favorites")
async def sonos_favorites():
    """List Sonos favorites."""
    return await _proxy_get("/api/fleet/sonos/favorites")


@router.post("/sonos/play")
async def sonos_play(body: dict):
    """Play/resume on a Sonos speaker. Body: {room, uri?}"""
    return await _proxy_post("/api/fleet/sonos/play", body)


@router.post("/sonos/pause")
async def sonos_pause(body: dict):
    """Pause a Sonos speaker. Body: {room}"""
    return await _proxy_post("/api/fleet/sonos/pause", body)


@router.post("/sonos/volume")
async def sonos_volume(body: dict):
    """Get/set Sonos volume. Body: {room, level?}"""
    return await _proxy_post("/api/fleet/sonos/volume", body)


@router.post("/sonos/play-favorite")
async def sonos_play_favorite(body: dict):
    """Play a Sonos favorite. Body: {room, favorite}"""
    return await _proxy_post("/api/fleet/sonos/play-favorite", body)


# ── Alexa Devices ─────────────────────────────────────────────────────────────


@router.get("/alexa/devices")
async def alexa_devices():
    """List Alexa devices."""
    return await _proxy_get("/api/fleet/alexa/devices")


@router.get("/alexa/smart-home")
async def alexa_smart_home():
    """List Alexa smart home devices."""
    return await _proxy_get("/api/fleet/alexa/smart-home")


@router.post("/alexa/speak")
async def alexa_speak(body: dict):
    """Make Alexa speak on one device. Body: {serialNumber, text}"""
    return await _proxy_post("/api/fleet/alexa/speak", body)


@router.post("/alexa/announce")
async def alexa_announce(body: dict):
    """Announce on ALL Alexa devices or a specific one. Body: {text, serialNumber?}"""
    return await _proxy_post("/api/fleet/alexa/announce", body)


@router.get("/alexa/routines")
async def alexa_routines():
    """List Alexa routines."""
    return await _proxy_get("/api/fleet/alexa/routines")


# ── Remote Devices ────────────────────────────────────────────────────────────


@router.post("/remote/exec")
async def remote_exec(body: dict):
    """Execute a command on a remote device (SSH)."""
    return await _proxy_post("/api/fleet/remote/exec", body)


# ── Media Stack (Rocky Linux – Sonarr/Radarr/Lidarr/Plex/etc.) ───────────────


@router.get("/media/status")
async def media_status():
    """Overview of all media stack services (online/offline)."""
    return await _proxy_get("/api/fleet/media/status")


@router.get("/media/downloads")
async def media_downloads():
    """Combined download queue across all *arr apps + NZBGet."""
    return await _proxy_get("/api/fleet/media/downloads")


@router.get("/media/plex/sessions")
async def media_plex_sessions():
    """Active Plex streaming sessions."""
    return await _proxy_get("/api/fleet/media/plex/sessions")


@router.get("/media/plex/libraries")
async def media_plex_libraries():
    """Plex library counts."""
    return await _proxy_get("/api/fleet/media/plex/libraries")


@router.get("/media/plex/recent")
async def media_plex_recent():
    """Recently added items in Plex."""
    return await _proxy_get("/api/fleet/media/plex/recent")


@router.get("/media/sonarr/series")
async def media_sonarr_series():
    """Sonarr series stats (total, monitored, unmonitored)."""
    return await _proxy_get("/api/fleet/media/sonarr/series")


@router.get("/media/sonarr/queue")
async def media_sonarr_queue():
    """Sonarr download queue."""
    return await _proxy_get("/api/fleet/media/sonarr/queue")


@router.get("/media/sonarr/calendar")
async def media_sonarr_calendar():
    """Upcoming episodes from Sonarr."""
    return await _proxy_get("/api/fleet/media/sonarr/calendar")


@router.get("/media/radarr/movies")
async def media_radarr_movies():
    """Radarr movie stats (total, monitored, downloaded)."""
    return await _proxy_get("/api/fleet/media/radarr/movies")


@router.get("/media/radarr/queue")
async def media_radarr_queue():
    """Radarr download queue."""
    return await _proxy_get("/api/fleet/media/radarr/queue")


@router.get("/media/radarr/calendar")
async def media_radarr_calendar():
    """Upcoming movies from Radarr."""
    return await _proxy_get("/api/fleet/media/radarr/calendar")


@router.get("/media/lidarr/artists")
async def media_lidarr_artists():
    """Lidarr artist stats."""
    return await _proxy_get("/api/fleet/media/lidarr/artists")


@router.get("/media/lidarr/queue")
async def media_lidarr_queue():
    """Lidarr download queue."""
    return await _proxy_get("/api/fleet/media/lidarr/queue")


@router.get("/media/prowlarr/indexers")
async def media_prowlarr_indexers():
    """Prowlarr indexer list."""
    return await _proxy_get("/api/fleet/media/prowlarr/indexers")


@router.get("/media/nzbget/status")
async def media_nzbget_status():
    """NZBGet download status."""
    return await _proxy_get("/api/fleet/media/nzbget/status")


@router.get("/media/seerr/requests")
async def media_seerr_requests():
    """Seerr/Overseerr media requests."""
    return await _proxy_get("/api/fleet/media/seerr/requests")
