"""
Tests for memory monitoring module.

Tests:
- Memory metrics retrieval
- Threshold logic
- Model load gating
- Memory summary
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.app.core.memory import (
    HEAVY_MODEL_BLOCK_THRESHOLD,
    MEMORY_CRITICAL_THRESHOLD,
    MEMORY_WARNING_THRESHOLD,
    MemoryMetrics,
    MemoryStatus,
    can_load_model,
    get_memory_metrics,
    get_memory_summary,
)


class TestMemoryMetrics:
    """Tests for memory metrics retrieval."""

    def test_get_memory_metrics_returns_metrics(self):
        """Verify get_memory_metrics returns MemoryMetrics."""
        metrics = get_memory_metrics()
        assert isinstance(metrics, MemoryMetrics)

    def test_memory_total_positive(self):
        """Total memory must be positive."""
        metrics = get_memory_metrics()
        assert metrics.total_gb > 0

    def test_memory_available_positive(self):
        """Available memory must be positive."""
        metrics = get_memory_metrics()
        assert metrics.available_gb > 0

    def test_memory_used_positive(self):
        """Used memory must be positive."""
        metrics = get_memory_metrics()
        assert metrics.used_gb > 0

    def test_memory_percent_in_range(self):
        """Memory percent must be 0-100."""
        metrics = get_memory_metrics()
        assert 0 <= metrics.percent_used <= 100

    def test_memory_available_less_than_total(self):
        """Available memory must be less than or equal to total."""
        metrics = get_memory_metrics()
        assert metrics.available_gb <= metrics.total_gb

    def test_memory_status_is_valid(self):
        """Memory status must be a valid MemoryStatus."""
        metrics = get_memory_metrics()
        assert metrics.status in (
            MemoryStatus.HEALTHY,
            MemoryStatus.WARNING,
            MemoryStatus.CRITICAL,
        )


class TestMemoryThresholds:
    """Tests for memory threshold logic."""

    def test_healthy_status_below_warning(self):
        """Status should be HEALTHY below warning threshold."""
        mock_mem = type("MockMem", (), {
            "total": int(28 * 1024**3),
            "available": int(20 * 1024**3),
            "used": int(8 * 1024**3),
            "percent": 28.6,
        })()
        mock_swap = type("MockSwap", (), {
            "used": 0,
            "total": int(4 * 1024**3),
        })()

        with patch("backend.app.core.memory.psutil.virtual_memory", return_value=mock_mem), \
             patch("backend.app.core.memory.psutil.swap_memory", return_value=mock_swap):
            metrics = get_memory_metrics()
            assert metrics.status == MemoryStatus.HEALTHY
            assert metrics.heavy_model_allowed is True

    def test_warning_status_at_threshold(self):
        """Status should be WARNING at warning threshold."""
        mock_mem = type("MockMem", (), {
            "total": int(28 * 1024**3),
            "available": int(9.8 * 1024**3),
            "used": int(18.2 * 1024**3),
            "percent": 67.0,
        })()
        mock_swap = type("MockSwap", (), {
            "used": 0,
            "total": int(4 * 1024**3),
        })()

        with patch("backend.app.core.memory.psutil.virtual_memory", return_value=mock_mem), \
             patch("backend.app.core.memory.psutil.swap_memory", return_value=mock_swap):
            metrics = get_memory_metrics()
            assert metrics.status == MemoryStatus.WARNING

    def test_critical_status_at_threshold(self):
        """Status should be CRITICAL at critical threshold."""
        mock_mem = type("MockMem", (), {
            "total": int(28 * 1024**3),
            "available": int(7 * 1024**3),
            "used": int(21 * 1024**3),
            "percent": 76.0,
        })()
        mock_swap = type("MockSwap", (), {
            "used": 0,
            "total": int(4 * 1024**3),
        })()

        with patch("backend.app.core.memory.psutil.virtual_memory", return_value=mock_mem), \
             patch("backend.app.core.memory.psutil.swap_memory", return_value=mock_swap):
            metrics = get_memory_metrics()
            assert metrics.status == MemoryStatus.CRITICAL
            assert metrics.heavy_model_allowed is False


class TestModelLoadGating:
    """Tests for model load gating logic."""

    def test_can_load_small_model_with_memory(self):
        """Should allow loading small model when memory available."""
        mock_mem = type("MockMem", (), {
            "total": int(28 * 1024**3),
            "available": int(20 * 1024**3),
            "used": int(8 * 1024**3),
            "percent": 28.6,
        })()
        mock_swap = type("MockSwap", (), {
            "used": 0,
            "total": int(4 * 1024**3),
        })()

        with patch("backend.app.core.memory.psutil.virtual_memory", return_value=mock_mem), \
             patch("backend.app.core.memory.psutil.swap_memory", return_value=mock_swap):
            can_load, reason = can_load_model("7b")
            assert can_load is True
            assert "OK" in reason

    def test_cannot_load_huge_model(self):
        """Should block loading 70B model on 28GB system."""
        mock_mem = type("MockMem", (), {
            "total": int(28 * 1024**3),
            "available": int(20 * 1024**3),
            "used": int(8 * 1024**3),
            "percent": 28.6,
        })()
        mock_swap = type("MockSwap", (), {
            "used": 0,
            "total": int(4 * 1024**3),
        })()

        with patch("backend.app.core.memory.psutil.virtual_memory", return_value=mock_mem), \
             patch("backend.app.core.memory.psutil.swap_memory", return_value=mock_swap):
            can_load, reason = can_load_model("70b")
            assert can_load is False
            assert "Insufficient memory" in reason

    def test_block_load_when_memory_critical(self):
        """Should block any model load when memory is critical."""
        mock_mem = type("MockMem", (), {
            "total": int(28 * 1024**3),
            "available": int(5 * 1024**3),
            "used": int(23 * 1024**3),
            "percent": 82.0,
        })()
        mock_swap = type("MockSwap", (), {
            "used": 0,
            "total": int(4 * 1024**3),
        })()

        with patch("backend.app.core.memory.psutil.virtual_memory", return_value=mock_mem), \
             patch("backend.app.core.memory.psutil.swap_memory", return_value=mock_swap):
            can_load, reason = can_load_model("7b")
            assert can_load is False
            assert "Memory usage at" in reason


class TestMemoryAsDict:
    """Tests for memory metrics serialization."""

    def test_as_dict_has_required_fields(self):
        """Verify as_dict includes all required fields."""
        metrics = get_memory_metrics()
        d = metrics.as_dict
        required_fields = [
            "total_gb", "available_gb", "used_gb", "percent_used",
            "status", "heavy_model_allowed", "swap_used_gb", "swap_total_gb",
        ]
        for field in required_fields:
            assert field in d, f"Missing field: {field}"

    def test_as_dict_values_are_rounded(self):
        """Verify GB values are properly rounded."""
        metrics = get_memory_metrics()
        d = metrics.as_dict
        # Check that percent_used has at most 1 decimal
        assert d["percent_used"] == round(d["percent_used"], 1)


class TestMemorySummary:
    """Tests for human-readable memory summary."""

    def test_summary_is_string(self):
        """Summary should be a string."""
        summary = get_memory_summary()
        assert isinstance(summary, str)

    def test_summary_contains_key_info(self):
        """Summary should contain key memory information."""
        summary = get_memory_summary()
        assert "Memory:" in summary
        assert "Status:" in summary
        assert "Heavy model:" in summary


class TestThresholdConstants:
    """Tests for threshold constant values."""

    def test_warning_threshold_value(self):
        """Warning threshold should be 65%."""
        assert MEMORY_WARNING_THRESHOLD == 65.0

    def test_critical_threshold_value(self):
        """Critical threshold should be 75%."""
        assert MEMORY_CRITICAL_THRESHOLD == 75.0

    def test_block_threshold_value(self):
        """Block threshold should be 75%."""
        assert HEAVY_MODEL_BLOCK_THRESHOLD == 75.0

    def test_warning_less_than_critical(self):
        """Warning threshold must be less than critical."""
        assert MEMORY_WARNING_THRESHOLD < MEMORY_CRITICAL_THRESHOLD
