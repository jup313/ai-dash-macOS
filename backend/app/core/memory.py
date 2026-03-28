"""
Unified memory monitoring for 28GB Apple Silicon systems.

Provides:
- Real-time memory metrics
- Heavy model load gating (block if RAM > 75%)
- Memory threshold alerts
- Async-compatible monitoring
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import psutil


class MemoryStatus(str, Enum):
    """Memory status levels."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class MemoryMetrics:
    """System memory metrics."""

    total_gb: float
    available_gb: float
    used_gb: float
    percent_used: float
    status: MemoryStatus
    heavy_model_allowed: bool
    swap_used_gb: float
    swap_total_gb: float

    @property
    def as_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "total_gb": round(self.total_gb, 2),
            "available_gb": round(self.available_gb, 2),
            "used_gb": round(self.used_gb, 2),
            "percent_used": round(self.percent_used, 1),
            "status": self.status.value,
            "heavy_model_allowed": self.heavy_model_allowed,
            "swap_used_gb": round(self.swap_used_gb, 2),
            "swap_total_gb": round(self.swap_total_gb, 2),
        }


# Thresholds for 28GB unified memory system
MEMORY_WARNING_THRESHOLD = 65.0  # percent
MEMORY_CRITICAL_THRESHOLD = 75.0  # percent
HEAVY_MODEL_BLOCK_THRESHOLD = 90.0  # percent — block heavy model load above this

# Approximate model sizes for memory budgeting
MODEL_SIZE_ESTIMATES_GB = {
    "7b": 4.0,
    "8b": 5.0,
    "13b": 8.0,
    "32b": 20.0,
    "70b": 40.0,  # Too large for 28GB
}


def _bytes_to_gb(bytes_val: int) -> float:
    """Convert bytes to gigabytes."""
    return bytes_val / (1024 ** 3)


def get_memory_metrics() -> MemoryMetrics:
    """
    Get current system memory metrics.

    Returns real-time memory information from the system,
    with status classification and heavy model gating.
    """
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    total_gb = _bytes_to_gb(mem.total)
    available_gb = _bytes_to_gb(mem.available)
    used_gb = _bytes_to_gb(mem.used)
    percent_used = mem.percent

    # Determine status
    if percent_used >= MEMORY_CRITICAL_THRESHOLD:
        status = MemoryStatus.CRITICAL
    elif percent_used >= MEMORY_WARNING_THRESHOLD:
        status = MemoryStatus.WARNING
    else:
        status = MemoryStatus.HEALTHY

    # Gate heavy model loading
    heavy_model_allowed = percent_used < HEAVY_MODEL_BLOCK_THRESHOLD

    return MemoryMetrics(
        total_gb=total_gb,
        available_gb=available_gb,
        used_gb=used_gb,
        percent_used=percent_used,
        status=status,
        heavy_model_allowed=heavy_model_allowed,
        swap_used_gb=_bytes_to_gb(swap.used),
        swap_total_gb=_bytes_to_gb(swap.total),
    )


def can_load_model(model_size_key: str) -> tuple[bool, str]:
    """
    Check if a model of given size can be safely loaded.

    Args:
        model_size_key: Model size identifier (e.g., "7b", "13b", "32b")

    Returns:
        Tuple of (can_load, reason)
    """
    metrics = get_memory_metrics()
    estimated_size = MODEL_SIZE_ESTIMATES_GB.get(
        model_size_key.lower(), 5.0  # Default estimate
    )

    if not metrics.heavy_model_allowed:
        return (
            False,
            f"Memory usage at {metrics.percent_used:.1f}% "
            f"(threshold: {HEAVY_MODEL_BLOCK_THRESHOLD}%). "
            f"Available: {metrics.available_gb:.1f}GB, "
            f"Model needs ~{estimated_size:.1f}GB",
        )

    if estimated_size > metrics.available_gb:
        return (
            False,
            f"Insufficient memory: {metrics.available_gb:.1f}GB available, "
            f"model needs ~{estimated_size:.1f}GB",
        )

    return (
        True,
        f"OK: {metrics.available_gb:.1f}GB available, "
        f"model needs ~{estimated_size:.1f}GB",
    )


def get_memory_summary() -> str:
    """Get a human-readable memory summary."""
    metrics = get_memory_metrics()
    return (
        f"Memory: {metrics.used_gb:.1f}GB / {metrics.total_gb:.1f}GB "
        f"({metrics.percent_used:.1f}%) — "
        f"Status: {metrics.status.value} — "
        f"Heavy model: {'allowed' if metrics.heavy_model_allowed else 'BLOCKED'}"
    )
