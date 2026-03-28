"""Tests for the workflow engine — CRUD, execution, conditions, error handling."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.automation.engine import (
    WorkflowEngine,
    _evaluate_condition,
    get_engine,
    reset_engine,
)
from backend.app.automation.models import (
    ErrorAction,
    RunStatus,
    StepResult,
    StepType,
    WorkflowDefinition,
    WorkflowStep,
)


@pytest.fixture(autouse=True)
def _clean_engine():
    """Reset engine singleton before each test."""
    reset_engine()
    yield
    reset_engine()


def _step(name: str, stype: StepType = StepType.DELAY, **kwargs) -> WorkflowStep:
    """Helper to build a step quickly."""
    return WorkflowStep(name=name, step_type=stype, **kwargs)


def _wf(name: str = "test-wf", steps: list[WorkflowStep] | None = None) -> WorkflowDefinition:
    """Helper to build a workflow quickly."""
    if steps is None:
        steps = [_step("s1")]
    return WorkflowDefinition(name=name, steps=steps)


# ── CRUD ───────────────────────────────────────────────────────────────────────


class TestWorkflowCRUD:
    def test_create_and_get(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow(_wf("alpha"))
        assert wf.name == "alpha"
        assert engine.get_workflow(wf.workflow_id) is not None

    def test_get_missing(self):
        engine = WorkflowEngine()
        assert engine.get_workflow("nonexistent") is None

    def test_list_workflows(self):
        engine = WorkflowEngine()
        engine.create_workflow(_wf("a"))
        engine.create_workflow(_wf("b"))
        infos = engine.list_workflows()
        assert len(infos) == 2
        names = {i.name for i in infos}
        assert names == {"a", "b"}

    def test_update_workflow(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow(_wf("original"))
        updated = engine.update_workflow(wf.workflow_id, name="renamed")
        assert updated is not None
        assert updated.name == "renamed"
        assert engine.get_workflow(wf.workflow_id).name == "renamed"

    def test_update_missing(self):
        engine = WorkflowEngine()
        assert engine.update_workflow("nope", name="x") is None

    def test_delete_workflow(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow(_wf("doomed"))
        assert engine.delete_workflow(wf.workflow_id) is True
        assert engine.get_workflow(wf.workflow_id) is None

    def test_delete_missing(self):
        engine = WorkflowEngine()
        assert engine.delete_workflow("nope") is False

    def test_delete_cleans_runs(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow(_wf("temp"))
        # Manually add a fake run_id to workflow_runs
        engine._workflow_runs[wf.workflow_id] = ["r1"]
        engine._runs["r1"] = "placeholder"
        engine.delete_workflow(wf.workflow_id)
        assert "r1" not in engine._runs


# ── Condition evaluator ───────────────────────────────────────────────────────


class TestConditionEvaluator:
    def test_none_is_true(self):
        assert _evaluate_condition(None, {}) is True

    def test_empty_string_is_true(self):
        assert _evaluate_condition("", {}) is True

    def test_success_condition_met(self):
        results = {
            "step1": StepResult(
                step_id="s", step_name="step1",
                step_type=StepType.DELAY, status=RunStatus.COMPLETED,
            )
        }
        assert _evaluate_condition("step1.success", results) is True

    def test_success_condition_not_met(self):
        results = {
            "step1": StepResult(
                step_id="s", step_name="step1",
                step_type=StepType.DELAY, status=RunStatus.FAILED,
            )
        }
        assert _evaluate_condition("step1.success", results) is False

    def test_failed_condition_met(self):
        results = {
            "step1": StepResult(
                step_id="s", step_name="step1",
                step_type=StepType.DELAY, status=RunStatus.FAILED,
            )
        }
        assert _evaluate_condition("step1.failed", results) is True

    def test_missing_ref_is_false(self):
        assert _evaluate_condition("missing.success", {}) is False

    def test_invalid_format_is_true(self):
        assert _evaluate_condition("no_dot_here", {}) is True

    def test_unknown_check_is_true(self):
        results = {
            "s": StepResult(
                step_id="s", step_name="s",
                step_type=StepType.DELAY, status=RunStatus.COMPLETED,
            )
        }
        assert _evaluate_condition("s.unknown", results) is True


# ── Execution — delay steps (no mocking needed) ──────────────────────────────


class TestEngineExecution:
    @pytest.mark.asyncio
    async def test_execute_delay_workflow(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow(
            _wf("delay-wf", steps=[
                _step("wait1", StepType.DELAY, config={"seconds": 0.01}),
                _step("wait2", StepType.DELAY, config={"seconds": 0.01}),
            ])
        )
        run = await engine.execute_workflow(wf.workflow_id)
        assert run.status == RunStatus.COMPLETED
        assert len(run.step_results) == 2
        assert all(r.status == RunStatus.COMPLETED for r in run.step_results)
        assert run.duration_ms > 0
        assert run.completed_at is not None

    @pytest.mark.asyncio
    async def test_execute_missing_workflow(self):
        engine = WorkflowEngine()
        with pytest.raises(ValueError, match="not found"):
            await engine.execute_workflow("nope")

    @pytest.mark.asyncio
    async def test_execute_disabled_workflow(self):
        engine = WorkflowEngine()
        wf = _wf("disabled")
        wf.enabled = False
        engine.create_workflow(wf)
        with pytest.raises(ValueError, match="disabled"):
            await engine.execute_workflow(wf.workflow_id)

    @pytest.mark.asyncio
    async def test_run_history_stored(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow(
            _wf("hist", steps=[_step("d", StepType.DELAY, config={"seconds": 0.01})])
        )
        run = await engine.execute_workflow(wf.workflow_id)
        assert engine.get_run(run.run_id) is not None
        runs = engine.get_workflow_runs(wf.workflow_id)
        assert len(runs) == 1

    @pytest.mark.asyncio
    async def test_multiple_runs(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow(
            _wf("multi", steps=[_step("d", StepType.DELAY, config={"seconds": 0.01})])
        )
        await engine.execute_workflow(wf.workflow_id)
        await engine.execute_workflow(wf.workflow_id)
        assert len(engine.get_workflow_runs(wf.workflow_id)) == 2


# ── Error handling ─────────────────────────────────────────────────────────────


class TestEngineErrorHandling:
    @pytest.mark.asyncio
    async def test_step_failure_stops_by_default(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow(
            _wf("fail-stop", steps=[
                _step("bad", StepType.CODE_EXECUTE, config={"code": "exit 1", "language": "bash"}),
                _step("never", StepType.DELAY, config={"seconds": 0.01}),
            ])
        )
        run = await engine.execute_workflow(wf.workflow_id)
        assert run.status == RunStatus.FAILED
        assert len(run.step_results) == 1  # stopped after first
        assert run.error is not None

    @pytest.mark.asyncio
    async def test_on_error_continue(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow(
            _wf("fail-continue", steps=[
                _step(
                    "bad", StepType.CODE_EXECUTE,
                    config={"code": "exit 1", "language": "bash"},
                    on_error=ErrorAction.CONTINUE,
                ),
                _step("ok", StepType.DELAY, config={"seconds": 0.01}),
            ])
        )
        run = await engine.execute_workflow(wf.workflow_id)
        assert run.status == RunStatus.COMPLETED  # continued past failure
        assert len(run.step_results) == 2
        assert run.step_results[0].status == RunStatus.FAILED
        assert run.step_results[1].status == RunStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_step_timeout(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow(
            _wf("timeout", steps=[
                _step(
                    "slow", StepType.DELAY,
                    config={"seconds": 10},
                    timeout_seconds=1,
                ),
            ])
        )
        run = await engine.execute_workflow(wf.workflow_id)
        assert run.status == RunStatus.FAILED
        assert "timed out" in run.step_results[0].error


# ── Conditional steps ─────────────────────────────────────────────────────────


class TestConditionalSteps:
    @pytest.mark.asyncio
    async def test_condition_success_passes(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow(
            _wf("cond-pass", steps=[
                _step("first", StepType.DELAY, config={"seconds": 0.01}),
                _step("second", StepType.DELAY, config={"seconds": 0.01}, condition="first.success"),
            ])
        )
        run = await engine.execute_workflow(wf.workflow_id)
        assert run.status == RunStatus.COMPLETED
        assert len(run.step_results) == 2
        assert run.step_results[1].status == RunStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_condition_skips_when_not_met(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow(
            _wf("cond-skip", steps=[
                _step(
                    "first", StepType.CODE_EXECUTE,
                    config={"code": "exit 1", "language": "bash"},
                    on_error=ErrorAction.CONTINUE,
                ),
                _step(
                    "second", StepType.DELAY,
                    config={"seconds": 0.01},
                    condition="first.success",
                ),
            ])
        )
        run = await engine.execute_workflow(wf.workflow_id)
        assert run.status == RunStatus.COMPLETED
        assert run.step_results[1].status == RunStatus.SKIPPED


# ── Code analysis step (no LLM needed) ───────────────────────────────────────


class TestCodeAnalysisStep:
    @pytest.mark.asyncio
    async def test_analyze_step(self):
        engine = WorkflowEngine()
        wf = engine.create_workflow(
            _wf("analyze", steps=[
                _step(
                    "analyze", StepType.CODE_ANALYZE,
                    config={"code": "x = 1\ny = 2\n", "language": "python"},
                ),
            ])
        )
        run = await engine.execute_workflow(wf.workflow_id)
        assert run.status == RunStatus.COMPLETED
        assert "syntax_valid=True" in run.step_results[0].output


# ── Singleton ──────────────────────────────────────────────────────────────────


class TestEngineSingleton:
    def test_get_engine_returns_same_instance(self):
        e1 = get_engine()
        e2 = get_engine()
        assert e1 is e2

    def test_reset_engine_creates_new(self):
        e1 = get_engine()
        reset_engine()
        e2 = get_engine()
        assert e1 is not e2
