"""
Health check endpoint.

Returns system validation status including:
- ARM64 confirmation
- macOS platform check
- Python version
- Rosetta detection
- Ollama reachability
- Memory metrics
- Configuration status
"""

from __future__ import annotations

import platform
import sys

from fastapi import APIRouter

from backend.app.core.config import get_settings
from backend.app.core.memory import get_memory_metrics
from backend.app.core.validation import check_ollama, check_rosetta

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """
    Comprehensive health check endpoint.

    Returns system status, platform info, memory metrics,
    Ollama connectivity, and configuration status.
    """
    settings = get_settings()
    memory = get_memory_metrics()
    rosetta_check = check_rosetta()
    ollama_check = await check_ollama(settings.ollama_base_url)

    # Determine overall status
    is_healthy = (
        platform.machine() == "arm64"
        and sys.platform == "darwin"
        and not rosetta_check.passed is False
        and memory.percent_used < 90.0
    )

    return {
        "status": "healthy" if is_healthy else "degraded",
        "version": "0.1.0",
        "platform": {
            "arch": platform.machine(),
            "os": sys.platform,
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "rosetta": not rosetta_check.passed,
        },
        "memory": memory.as_dict,
        "ollama": {
            "reachable": ollama_check.passed,
            "url": settings.ollama_base_url,
            "detail": ollama_check.message,
        },
        "config": {
            "loaded": True,
            "provider": settings.llm_provider,
            "allow_remote": settings.allow_remote_models,
            "max_heavy_models": settings.max_heavy_models,
            "max_agent_concurrency": settings.max_agent_concurrency,
        },
    }
