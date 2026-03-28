"""
Workflow scheduler — interval-based recurring workflow execution.

Manages asyncio background tasks for scheduled workflows.
Respects max_runs limits and provides status reporting.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from backend.app.automation.engine import get_engine
from backend.app.automation.models import (
    ScheduleEntry,
    SchedulerStatus,
    TriggerType,
)

logger = logging.getLogger(__name__)


class _ScheduleHandle:
    """Internal handle for one active schedule."""

    def __init__(
        self,
        workflow_id: str,
        workflow_name: str,
        interval_seconds: int,
        max_runs: int | None,
    ):
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name
        self.interval_seconds = interval_seconds
        self.max_runs = max_runs
        self.total_runs = 0
        self.is_active = True
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        """Launch the background loop."""
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        """Cancel the background loop."""
        self.is_active = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        """Run the workflow on a fixed interval."""
        engine = get_engine()
        try:
            while self.is_active:
                await asyncio.sleep(self.interval_seconds)
                if not self.is_active:
                    break

                # Check max_runs
                if self.max_runs is not None and self.total_runs >= self.max_runs:
                    logger.info(
                        "Schedule for '%s' reached max_runs=%d, stopping",
                        self.workflow_name,
                        self.max_runs,
                    )
                    self.is_active = False
                    break

                try:
                    run = await engine.execute_workflow(self.workflow_id)
                    self.total_runs += 1
                    logger.info(
                        "Scheduled run #%d for '%s' → %s",
                        self.total_runs,
                        self.workflow_name,
                        run.status.value,
                    )
                except Exception as exc:
                    self.total_runs += 1
                    logger.error(
                        "Scheduled run for '%s' failed: %s",
                        self.workflow_name,
                        exc,
                    )
        except asyncio.CancelledError:
            logger.info("Schedule for '%s' cancelled", self.workflow_name)


class WorkflowScheduler:
    """
    Manages interval-based scheduled workflow execution.

    One schedule per workflow. Creating a new schedule for the same
    workflow replaces the previous one.
    """

    def __init__(self) -> None:
        self._schedules: dict[str, _ScheduleHandle] = {}  # workflow_id → handle

    def schedule_workflow(
        self,
        workflow_id: str,
        workflow_name: str,
        interval_seconds: int,
        max_runs: int | None = None,
    ) -> ScheduleEntry:
        """
        Start a recurring schedule for a workflow.

        Replaces any existing schedule for the same workflow.
        """
        # Remove existing schedule if present
        if workflow_id in self._schedules:
            existing = self._schedules[workflow_id]
            existing.is_active = False
            if existing._task and not existing._task.done():
                existing._task.cancel()

        handle = _ScheduleHandle(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            interval_seconds=interval_seconds,
            max_runs=max_runs,
        )
        handle.start()
        self._schedules[workflow_id] = handle

        logger.info(
            "Scheduled workflow '%s' every %ds (max_runs=%s)",
            workflow_name,
            interval_seconds,
            max_runs,
        )
        return ScheduleEntry(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            interval_seconds=interval_seconds,
            total_runs=0,
            is_active=True,
        )

    async def unschedule_workflow(self, workflow_id: str) -> bool:
        """Stop and remove a workflow schedule."""
        handle = self._schedules.pop(workflow_id, None)
        if handle is None:
            return False
        await handle.stop()
        logger.info("Unscheduled workflow %s", workflow_id[:8])
        return True

    def get_status(self) -> SchedulerStatus:
        """Get overall scheduler status."""
        entries = []
        total_runs = 0
        active_count = 0
        for handle in self._schedules.values():
            total_runs += handle.total_runs
            if handle.is_active:
                active_count += 1
            entries.append(
                ScheduleEntry(
                    workflow_id=handle.workflow_id,
                    workflow_name=handle.workflow_name,
                    interval_seconds=handle.interval_seconds,
                    total_runs=handle.total_runs,
                    is_active=handle.is_active,
                )
            )
        return SchedulerStatus(
            active_schedules=active_count,
            total_scheduled_runs=total_runs,
            schedules=entries,
        )

    def get_schedule(self, workflow_id: str) -> ScheduleEntry | None:
        """Get schedule entry for a specific workflow."""
        handle = self._schedules.get(workflow_id)
        if handle is None:
            return None
        return ScheduleEntry(
            workflow_id=handle.workflow_id,
            workflow_name=handle.workflow_name,
            interval_seconds=handle.interval_seconds,
            total_runs=handle.total_runs,
            is_active=handle.is_active,
        )

    async def shutdown(self) -> None:
        """Stop all schedules (called during app shutdown)."""
        for handle in self._schedules.values():
            await handle.stop()
        self._schedules.clear()
        logger.info("Scheduler shut down — all schedules cancelled")


# ── Singleton ──────────────────────────────────────────────────────────────────

_scheduler: WorkflowScheduler | None = None


def get_scheduler() -> WorkflowScheduler:
    """Get or create the scheduler singleton."""
    global _scheduler
    if _scheduler is None:
        _scheduler = WorkflowScheduler()
    return _scheduler


def reset_scheduler() -> None:
    """Reset the scheduler singleton (for testing)."""
    global _scheduler
    _scheduler = None
