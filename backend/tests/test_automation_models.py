"""Tests for automation data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.automation.models import (
    ErrorAction,
    RunStatus,
    ScheduleConfig,
    ScheduleEntry,
    SchedulerStatus,
    StepResult,
    StepType,
    TriggerType,
    WorkflowCreate,
    WorkflowDefinition,
    WorkflowInfo,
    WorkflowRun,
    WorkflowStep,
    WorkflowUpdate,
)


# ── StepType ───────────────────────────────────────────────────────────────────


class TestStepType:
    def test_all_step_types(self):
        assert StepType.LLM_CHAT == "llm_chat"
        assert StepType.AGENT_TASK == "agent_task"
        assert StepType.CODE_GENERATE == "code_generate"
        assert StepType.CODE_EXECUTE == "code_execute"
        assert StepType.CODE_ANALYZE == "code_analyze"
        assert StepType.DELAY == "delay"

    def test_step_type_count(self):
        assert len(StepType) == 6


# ── TriggerType ────────────────────────────────────────────────────────────────


class TestTriggerType:
    def test_trigger_types(self):
        assert TriggerType.MANUAL == "manual"
        assert TriggerType.SCHEDULE == "schedule"


# ── RunStatus ──────────────────────────────────────────────────────────────────


class TestRunStatus:
    def test_all_statuses(self):
        assert RunStatus.PENDING == "pending"
        assert RunStatus.RUNNING == "running"
        assert RunStatus.COMPLETED == "completed"
        assert RunStatus.FAILED == "failed"
        assert RunStatus.CANCELLED == "cancelled"
        assert RunStatus.SKIPPED == "skipped"

    def test_status_count(self):
        assert len(RunStatus) == 6


# ── ErrorAction ────────────────────────────────────────────────────────────────


class TestErrorAction:
    def test_all_actions(self):
        assert ErrorAction.STOP == "stop"
        assert ErrorAction.CONTINUE == "continue"
        assert ErrorAction.SKIP == "skip"


# ── WorkflowStep ──────────────────────────────────────────────────────────────


class TestWorkflowStep:
    def test_minimal_step(self):
        step = WorkflowStep(name="test", step_type=StepType.DELAY)
        assert step.name == "test"
        assert step.step_type == StepType.DELAY
        assert step.config == {}
        assert step.condition is None
        assert step.on_error == ErrorAction.STOP
        assert step.timeout_seconds == 60
        assert step.step_id  # auto-generated

    def test_full_step(self):
        step = WorkflowStep(
            name="chat-step",
            step_type=StepType.LLM_CHAT,
            config={"prompt": "hello"},
            condition="prev.success",
            on_error=ErrorAction.CONTINUE,
            timeout_seconds=120,
        )
        assert step.config["prompt"] == "hello"
        assert step.condition == "prev.success"
        assert step.on_error == ErrorAction.CONTINUE
        assert step.timeout_seconds == 120

    def test_step_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            WorkflowStep(name="", step_type=StepType.DELAY)

    def test_step_timeout_bounds(self):
        with pytest.raises(ValidationError):
            WorkflowStep(name="t", step_type=StepType.DELAY, timeout_seconds=0)
        with pytest.raises(ValidationError):
            WorkflowStep(name="t", step_type=StepType.DELAY, timeout_seconds=301)


# ── ScheduleConfig ─────────────────────────────────────────────────────────────


class TestScheduleConfig:
    def test_valid_config(self):
        sc = ScheduleConfig(interval_seconds=120)
        assert sc.interval_seconds == 120
        assert sc.max_runs is None

    def test_with_max_runs(self):
        sc = ScheduleConfig(interval_seconds=60, max_runs=5)
        assert sc.max_runs == 5

    def test_interval_too_low(self):
        with pytest.raises(ValidationError):
            ScheduleConfig(interval_seconds=30)

    def test_interval_too_high(self):
        with pytest.raises(ValidationError):
            ScheduleConfig(interval_seconds=100000)


# ── WorkflowDefinition ────────────────────────────────────────────────────────


class TestWorkflowDefinition:
    def test_minimal_definition(self):
        step = WorkflowStep(name="s1", step_type=StepType.DELAY)
        wf = WorkflowDefinition(name="wf1", steps=[step])
        assert wf.name == "wf1"
        assert wf.workflow_id
        assert len(wf.steps) == 1
        assert wf.trigger_type == TriggerType.MANUAL
        assert wf.enabled is True
        assert wf.created_at is not None

    def test_no_steps_rejected(self):
        with pytest.raises(ValidationError):
            WorkflowDefinition(name="wf", steps=[])


# ── WorkflowCreate ─────────────────────────────────────────────────────────────


class TestWorkflowCreate:
    def test_create_request(self):
        step = WorkflowStep(name="s", step_type=StepType.DELAY)
        req = WorkflowCreate(name="new-wf", steps=[step])
        assert req.name == "new-wf"
        assert req.trigger_type == TriggerType.MANUAL
        assert req.schedule is None


# ── WorkflowUpdate ─────────────────────────────────────────────────────────────


class TestWorkflowUpdate:
    def test_all_none(self):
        upd = WorkflowUpdate()
        assert upd.name is None
        assert upd.steps is None
        assert upd.enabled is None

    def test_partial_update(self):
        upd = WorkflowUpdate(name="renamed", enabled=False)
        assert upd.name == "renamed"
        assert upd.enabled is False


# ── StepResult ─────────────────────────────────────────────────────────────────


class TestStepResult:
    def test_completed_result(self):
        r = StepResult(
            step_id="s1",
            step_name="test",
            step_type=StepType.DELAY,
            status=RunStatus.COMPLETED,
            output="ok",
            duration_ms=42.5,
        )
        assert r.status == RunStatus.COMPLETED
        assert r.output == "ok"
        assert r.error is None

    def test_failed_result(self):
        r = StepResult(
            step_id="s1",
            step_name="test",
            step_type=StepType.LLM_CHAT,
            status=RunStatus.FAILED,
            error="timeout",
        )
        assert r.status == RunStatus.FAILED
        assert r.error == "timeout"


# ── WorkflowRun ───────────────────────────────────────────────────────────────


class TestWorkflowRun:
    def test_default_run(self):
        run = WorkflowRun(workflow_id="w1", workflow_name="test")
        assert run.run_id
        assert run.status == RunStatus.PENDING
        assert run.step_results == []
        assert run.trigger_type == TriggerType.MANUAL

    def test_run_with_steps(self):
        sr = StepResult(
            step_id="s1",
            step_name="step1",
            step_type=StepType.DELAY,
            status=RunStatus.COMPLETED,
        )
        run = WorkflowRun(
            workflow_id="w1",
            workflow_name="test",
            status=RunStatus.COMPLETED,
            step_results=[sr],
        )
        assert len(run.step_results) == 1


# ── WorkflowInfo ──────────────────────────────────────────────────────────────


class TestWorkflowInfo:
    def test_info(self):
        info = WorkflowInfo(
            workflow_id="w1",
            name="test",
            description="desc",
            step_count=3,
            trigger_type=TriggerType.MANUAL,
            enabled=True,
        )
        assert info.total_runs == 0
        assert info.step_count == 3


# ── ScheduleEntry & SchedulerStatus ──────────────────────────────────────────


class TestSchedulerModels:
    def test_schedule_entry(self):
        e = ScheduleEntry(
            workflow_id="w1",
            workflow_name="test",
            interval_seconds=120,
        )
        assert e.total_runs == 0
        assert e.is_active is True

    def test_scheduler_status(self):
        s = SchedulerStatus(active_schedules=0, total_scheduled_runs=0)
        assert s.schedules == []
