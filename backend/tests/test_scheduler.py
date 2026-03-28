"""Tests for the workflow scheduler."""

from __future__ import annotations

import asyncio

import pytest

from backend.app.automation.engine import WorkflowEngine, reset_engine
from backend.app.automation.models import StepType, WorkflowDefinition, WorkflowStep
from backend.app.automation.scheduler import (
    WorkflowScheduler,
    get_scheduler,
    reset_scheduler,
)


@pytest.fixture(autouse=True)
def _clean():
    reset_engine()
    reset_scheduler()
    yield
    reset_scheduler()
    reset_engine()


def _delay_step(name: str = "d", seconds: float = 0.01) -> WorkflowStep:
    return WorkflowStep(name=name, step_type=StepType.DELAY, config={"seconds": seconds})


def _make_wf(engine: WorkflowEngine, name: str = "sched-wf") -> WorkflowDefinition:
    wf = WorkflowDefinition(name=name, steps=[_delay_step()])
    return engine.create_workflow(wf)


class TestSchedulerBasics:
    @pytest.mark.asyncio
    async def test_schedule_workflow(self):
        scheduler = WorkflowScheduler()
        entry = scheduler.schedule_workflow(
            workflow_id="w1",
            workflow_name="test",
            interval_seconds=120,
        )
        assert entry.workflow_id == "w1"
        assert entry.is_active is True
        assert entry.interval_seconds == 120
        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_get_status(self):
        scheduler = WorkflowScheduler()
        scheduler.schedule_workflow("w1", "test", 120)
        status = scheduler.get_status()
        assert status.active_schedules == 1
        assert len(status.schedules) == 1
        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_get_schedule(self):
        scheduler = WorkflowScheduler()
        scheduler.schedule_workflow("w1", "test", 120)
        entry = scheduler.get_schedule("w1")
        assert entry is not None
        assert entry.workflow_name == "test"
        await scheduler.shutdown()

    def test_get_schedule_missing(self):
        scheduler = WorkflowScheduler()
        assert scheduler.get_schedule("nope") is None

    @pytest.mark.asyncio
    async def test_unschedule(self):
        scheduler = WorkflowScheduler()
        scheduler.schedule_workflow("w1", "test", 120)
        removed = await scheduler.unschedule_workflow("w1")
        assert removed is True
        assert scheduler.get_schedule("w1") is None

    @pytest.mark.asyncio
    async def test_unschedule_missing(self):
        scheduler = WorkflowScheduler()
        removed = await scheduler.unschedule_workflow("nope")
        assert removed is False

    @pytest.mark.asyncio
    async def test_shutdown_clears_all(self):
        scheduler = WorkflowScheduler()
        scheduler.schedule_workflow("w1", "a", 120)
        scheduler.schedule_workflow("w2", "b", 120)
        await scheduler.shutdown()
        status = scheduler.get_status()
        assert status.active_schedules == 0
        assert len(status.schedules) == 0

    @pytest.mark.asyncio
    async def test_replace_existing_schedule(self):
        scheduler = WorkflowScheduler()
        scheduler.schedule_workflow("w1", "test", 120)
        scheduler.schedule_workflow("w1", "test", 300)
        entry = scheduler.get_schedule("w1")
        assert entry.interval_seconds == 300
        # Should still be just one schedule
        assert scheduler.get_status().active_schedules == 1
        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_schedule_with_max_runs(self):
        scheduler = WorkflowScheduler()
        entry = scheduler.schedule_workflow("w1", "test", 120, max_runs=5)
        assert entry.is_active is True
        await scheduler.shutdown()


class TestSchedulerSingleton:
    def test_get_scheduler_same_instance(self):
        s1 = get_scheduler()
        s2 = get_scheduler()
        assert s1 is s2

    def test_reset_scheduler(self):
        s1 = get_scheduler()
        reset_scheduler()
        s2 = get_scheduler()
        assert s1 is not s2
