"""
Workflow engine — executes workflow steps sequentially with error handling.

Integrates with LLM router, agent executor, and coding engine.
Supports conditional steps, configurable error actions, and timeout.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from backend.app.automation.models import (
    ErrorAction,
    RunStatus,
    StepResult,
    StepType,
    WorkflowDefinition,
    WorkflowInfo,
    WorkflowRun,
    WorkflowStep,
)

logger = logging.getLogger(__name__)


# ── Step executors ─────────────────────────────────────────────────────────────


async def _exec_llm_chat(config: dict[str, Any]) -> str:
    """Execute an LLM chat step."""
    from backend.app.llm.models import ChatRequest, Message, Role
    from backend.app.llm.router import get_router

    prompt = config.get("prompt", "")
    model = config.get("model")
    provider = config.get("provider")
    system_prompt = config.get("system_prompt", "")

    messages = []
    if system_prompt:
        messages.append(Message(role=Role.SYSTEM, content=system_prompt))
    messages.append(Message(role=Role.USER, content=prompt))

    request = ChatRequest(
        messages=messages,
        model=model,
        provider=provider,
    )
    router = get_router()
    response = await router.chat(request)
    return response.content


async def _exec_agent_task(config: dict[str, Any]) -> str:
    """Execute an agent task step."""
    from backend.app.agents.executor import get_executor
    from backend.app.agents.models import AgentTask

    task = AgentTask(
        agent_name=config.get("agent_name", "chat"),
        input_text=config.get("input_text", ""),
    )
    executor = get_executor()
    result = await executor.submit(task)
    if result.error:
        raise RuntimeError(result.error)
    return result.output


async def _exec_code_generate(config: dict[str, Any]) -> str:
    """Execute a code generation step."""
    from backend.app.coding.generator import generate_code
    from backend.app.coding.models import CodeAction, CodeLanguage, CodeRequest

    request = CodeRequest(
        action=CodeAction(config.get("action", "generate")),
        prompt=config.get("prompt", ""),
        code=config.get("code", ""),
        language=CodeLanguage(config.get("language", "python")),
    )
    result = await generate_code(request)
    return result.code or result.explanation


async def _exec_code_execute(config: dict[str, Any]) -> str:
    """Execute a code execution step."""
    from backend.app.coding.executor import execute_code
    from backend.app.coding.models import CodeLanguage, ExecutionRequest

    request = ExecutionRequest(
        code=config.get("code", ""),
        language=CodeLanguage(config.get("language", "python")),
        timeout_seconds=config.get("timeout_seconds", 30),
    )
    result = await execute_code(request)
    if result.exit_code != 0:
        raise RuntimeError(f"exit {result.exit_code}: {result.stderr}")
    return result.stdout


async def _exec_code_analyze(config: dict[str, Any]) -> str:
    """Execute a code analysis step."""
    from backend.app.coding.analyzer import analyze_code
    from backend.app.coding.models import CodeLanguage

    code = config.get("code", "")
    lang = CodeLanguage(config.get("language", "python"))
    result = analyze_code(code, lang)
    parts = [f"syntax_valid={result.syntax_valid}"]
    if result.issues:
        parts.append(f"issues={len(result.issues)}")
    parts.append(f"lines={result.metrics.total_lines}")
    return ", ".join(parts)


async def _exec_delay(config: dict[str, Any]) -> str:
    """Execute a delay step."""
    seconds = min(config.get("seconds", 1), 60)  # cap at 60s
    await asyncio.sleep(seconds)
    return f"delayed {seconds}s"


_STEP_EXECUTORS: dict[StepType, Any] = {
    StepType.LLM_CHAT: _exec_llm_chat,
    StepType.AGENT_TASK: _exec_agent_task,
    StepType.CODE_GENERATE: _exec_code_generate,
    StepType.CODE_EXECUTE: _exec_code_execute,
    StepType.CODE_ANALYZE: _exec_code_analyze,
    StepType.DELAY: _exec_delay,
}


# ── Condition evaluator ───────────────────────────────────────────────────────


def _evaluate_condition(
    condition: str | None,
    step_results: dict[str, StepResult],
) -> bool:
    """
    Evaluate a step condition against previous results.

    Supported patterns:
    - None / "" → always True
    - "<step_name>.success" → True if that step completed
    - "<step_name>.failed" → True if that step failed
    """
    if not condition:
        return True

    parts = condition.strip().split(".")
    if len(parts) != 2:
        logger.warning("Invalid condition '%s', treating as True", condition)
        return True

    ref_name, check = parts
    ref = step_results.get(ref_name)
    if ref is None:
        logger.warning("Condition ref '%s' not found, treating as False", ref_name)
        return False

    if check == "success":
        return ref.status == RunStatus.COMPLETED
    if check == "failed":
        return ref.status == RunStatus.FAILED
    logger.warning("Unknown condition check '%s', treating as True", check)
    return True


# ── Workflow Engine ────────────────────────────────────────────────────────────


class WorkflowEngine:
    """
    In-memory workflow store + execution engine.

    Stores workflow definitions, executes them step-by-step,
    and keeps a history of runs.
    """

    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowDefinition] = {}
        self._runs: dict[str, WorkflowRun] = {}  # run_id → run
        self._workflow_runs: dict[str, list[str]] = {}  # workflow_id → [run_ids]

    # ── CRUD ───────────────────────────────────────────────────────────────

    def create_workflow(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        """Store a new workflow definition."""
        self._workflows[definition.workflow_id] = definition
        self._workflow_runs.setdefault(definition.workflow_id, [])
        logger.info(
            "Created workflow '%s' (%s)", definition.name, definition.workflow_id[:8]
        )
        return definition

    def get_workflow(self, workflow_id: str) -> WorkflowDefinition | None:
        return self._workflows.get(workflow_id)

    def update_workflow(
        self, workflow_id: str, **updates: Any
    ) -> WorkflowDefinition | None:
        wf = self._workflows.get(workflow_id)
        if wf is None:
            return None

        data = wf.model_dump()
        for key, value in updates.items():
            if value is not None and key in data:
                data[key] = value
        data["updated_at"] = datetime.now(timezone.utc)

        updated = WorkflowDefinition(**data)
        self._workflows[workflow_id] = updated
        return updated

    def delete_workflow(self, workflow_id: str) -> bool:
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            # Clean up runs
            run_ids = self._workflow_runs.pop(workflow_id, [])
            for rid in run_ids:
                self._runs.pop(rid, None)
            logger.info("Deleted workflow %s", workflow_id[:8])
            return True
        return False

    def list_workflows(self) -> list[WorkflowInfo]:
        infos = []
        for wf in self._workflows.values():
            run_count = len(self._workflow_runs.get(wf.workflow_id, []))
            infos.append(
                WorkflowInfo(
                    workflow_id=wf.workflow_id,
                    name=wf.name,
                    description=wf.description,
                    step_count=len(wf.steps),
                    trigger_type=wf.trigger_type,
                    enabled=wf.enabled,
                    total_runs=run_count,
                )
            )
        return infos

    # ── Run history ────────────────────────────────────────────────────────

    def get_run(self, run_id: str) -> WorkflowRun | None:
        return self._runs.get(run_id)

    def get_workflow_runs(self, workflow_id: str) -> list[WorkflowRun]:
        run_ids = self._workflow_runs.get(workflow_id, [])
        return [self._runs[rid] for rid in run_ids if rid in self._runs]

    # ── Execution ──────────────────────────────────────────────────────────

    async def execute_workflow(self, workflow_id: str) -> WorkflowRun:
        """
        Execute all steps of a workflow sequentially.

        Returns a WorkflowRun with per-step results.
        """
        wf = self._workflows.get(workflow_id)
        if wf is None:
            raise ValueError(f"Workflow '{workflow_id}' not found")
        if not wf.enabled:
            raise ValueError(f"Workflow '{wf.name}' is disabled")

        run = WorkflowRun(
            workflow_id=wf.workflow_id,
            workflow_name=wf.name,
            status=RunStatus.RUNNING,
        )
        self._runs[run.run_id] = run
        self._workflow_runs.setdefault(wf.workflow_id, []).append(run.run_id)

        start = time.monotonic()
        step_result_map: dict[str, StepResult] = {}
        failed = False

        for step in wf.steps:
            step_result = await self._execute_step(step, step_result_map)
            run.step_results.append(step_result)
            step_result_map[step.name] = step_result

            if step_result.status == RunStatus.FAILED:
                if step.on_error == ErrorAction.STOP:
                    failed = True
                    run.error = step_result.error
                    break
                elif step.on_error == ErrorAction.SKIP:
                    continue
                # ErrorAction.CONTINUE → just keep going

        elapsed = (time.monotonic() - start) * 1000
        run.duration_ms = round(elapsed, 2)
        run.completed_at = datetime.now(timezone.utc)
        run.status = RunStatus.FAILED if failed else RunStatus.COMPLETED

        logger.info(
            "Workflow '%s' run %s → %s (%.0fms)",
            wf.name,
            run.run_id[:8],
            run.status.value,
            elapsed,
        )
        return run

    async def _execute_step(
        self,
        step: WorkflowStep,
        previous_results: dict[str, StepResult],
    ) -> StepResult:
        """Execute a single workflow step with timeout and condition check."""
        # Check condition
        if not _evaluate_condition(step.condition, previous_results):
            return StepResult(
                step_id=step.step_id,
                step_name=step.name,
                step_type=step.step_type,
                status=RunStatus.SKIPPED,
                output="condition not met",
            )

        executor_fn = _STEP_EXECUTORS.get(step.step_type)
        if executor_fn is None:
            return StepResult(
                step_id=step.step_id,
                step_name=step.name,
                step_type=step.step_type,
                status=RunStatus.FAILED,
                error=f"Unknown step type: {step.step_type}",
            )

        start = time.monotonic()
        try:
            output = await asyncio.wait_for(
                executor_fn(step.config),
                timeout=step.timeout_seconds,
            )
            elapsed = (time.monotonic() - start) * 1000
            return StepResult(
                step_id=step.step_id,
                step_name=step.name,
                step_type=step.step_type,
                status=RunStatus.COMPLETED,
                output=str(output),
                duration_ms=round(elapsed, 2),
                completed_at=datetime.now(timezone.utc),
            )
        except asyncio.TimeoutError:
            elapsed = (time.monotonic() - start) * 1000
            return StepResult(
                step_id=step.step_id,
                step_name=step.name,
                step_type=step.step_type,
                status=RunStatus.FAILED,
                error=f"Step timed out after {step.timeout_seconds}s",
                duration_ms=round(elapsed, 2),
                completed_at=datetime.now(timezone.utc),
            )
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            return StepResult(
                step_id=step.step_id,
                step_name=step.name,
                step_type=step.step_type,
                status=RunStatus.FAILED,
                error=str(exc),
                duration_ms=round(elapsed, 2),
                completed_at=datetime.now(timezone.utc),
            )


# ── Singleton ──────────────────────────────────────────────────────────────────

_engine: WorkflowEngine | None = None


def get_engine() -> WorkflowEngine:
    """Get or create the workflow engine singleton."""
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine


def reset_engine() -> None:
    """Reset the engine singleton (for testing)."""
    global _engine
    _engine = None
