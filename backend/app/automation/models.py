"""
Automation data models — workflows, steps, runs, schedules.

Provider-agnostic workflow definitions for the automation engine.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class StepType(str, Enum):
    """Workflow step types — each maps to a backend action."""

    LLM_CHAT = "llm_chat"
    AGENT_TASK = "agent_task"
    CODE_GENERATE = "code_generate"
    CODE_EXECUTE = "code_execute"
    CODE_ANALYZE = "code_analyze"
    DELAY = "delay"


class TriggerType(str, Enum):
    """How a workflow can be triggered."""

    MANUAL = "manual"
    SCHEDULE = "schedule"


class RunStatus(str, Enum):
    """Workflow / step execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class ErrorAction(str, Enum):
    """What to do when a step fails."""

    STOP = "stop"
    CONTINUE = "continue"
    SKIP = "skip"


# ── Step & Schedule ────────────────────────────────────────────────────────────


class WorkflowStep(BaseModel):
    """A single step within a workflow."""

    step_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique step identifier",
    )
    name: str = Field(..., min_length=1, description="Step name")
    step_type: StepType = Field(..., description="Step action type")
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific configuration",
    )
    condition: Optional[str] = Field(
        default=None,
        description="Optional condition expression (e.g. 'step_0.success')",
    )
    on_error: ErrorAction = Field(
        default=ErrorAction.STOP,
        description="Behaviour when this step fails",
    )
    timeout_seconds: int = Field(
        default=60,
        ge=1,
        le=300,
        description="Step execution timeout",
    )


class ScheduleConfig(BaseModel):
    """Interval-based schedule configuration."""

    interval_seconds: int = Field(
        ...,
        ge=60,
        le=86400,
        description="Seconds between runs (min 60)",
    )
    max_runs: Optional[int] = Field(
        default=None,
        ge=1,
        description="Max scheduled runs (None = unlimited)",
    )


# ── Workflow Definition ────────────────────────────────────────────────────────


class WorkflowDefinition(BaseModel):
    """Complete workflow definition stored by the engine."""

    workflow_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique workflow identifier",
    )
    name: str = Field(..., min_length=1, description="Workflow name")
    description: str = Field(default="", description="Workflow description")
    steps: list[WorkflowStep] = Field(
        ..., min_length=1, description="Ordered list of steps"
    )
    trigger_type: TriggerType = Field(
        default=TriggerType.MANUAL,
        description="Trigger mechanism",
    )
    schedule: Optional[ScheduleConfig] = Field(
        default=None,
        description="Schedule config (required when trigger_type=schedule)",
    )
    enabled: bool = Field(default=True, description="Is this workflow active?")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class WorkflowCreate(BaseModel):
    """API request to create a workflow."""

    name: str = Field(..., min_length=1)
    description: str = Field(default="")
    steps: list[WorkflowStep] = Field(..., min_length=1)
    trigger_type: TriggerType = Field(default=TriggerType.MANUAL)
    schedule: Optional[ScheduleConfig] = None


class WorkflowUpdate(BaseModel):
    """API request to update a workflow (all fields optional)."""

    name: Optional[str] = Field(default=None, min_length=1)
    description: Optional[str] = None
    steps: Optional[list[WorkflowStep]] = Field(default=None, min_length=1)
    trigger_type: Optional[TriggerType] = None
    schedule: Optional[ScheduleConfig] = None
    enabled: Optional[bool] = None


# ── Execution Results ──────────────────────────────────────────────────────────


class StepResult(BaseModel):
    """Result of executing a single workflow step."""

    step_id: str
    step_name: str
    step_type: StepType
    status: RunStatus
    output: str = ""
    error: Optional[str] = None
    duration_ms: float = 0.0
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    completed_at: Optional[datetime] = None


class WorkflowRun(BaseModel):
    """Record of a single workflow execution."""

    run_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique run identifier",
    )
    workflow_id: str
    workflow_name: str
    status: RunStatus = RunStatus.PENDING
    step_results: list[StepResult] = Field(default_factory=list)
    trigger_type: TriggerType = TriggerType.MANUAL
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    error: Optional[str] = None


# ── Info / Status ──────────────────────────────────────────────────────────────


class WorkflowInfo(BaseModel):
    """Summary info about a workflow."""

    workflow_id: str
    name: str
    description: str
    step_count: int
    trigger_type: TriggerType
    enabled: bool
    total_runs: int = 0


class ScheduleEntry(BaseModel):
    """Info about a single active schedule."""

    workflow_id: str
    workflow_name: str
    interval_seconds: int
    total_runs: int = 0
    is_active: bool = True


class SchedulerStatus(BaseModel):
    """Overall scheduler status."""

    active_schedules: int
    total_scheduled_runs: int
    schedules: list[ScheduleEntry] = Field(default_factory=list)
