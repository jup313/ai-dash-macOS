"""
Automation API endpoints — workflow CRUD, execution, scheduling.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend.app.automation.engine import get_engine
from backend.app.automation.models import (
    ScheduleConfig,
    ScheduleEntry,
    SchedulerStatus,
    TriggerType,
    WorkflowCreate,
    WorkflowDefinition,
    WorkflowInfo,
    WorkflowRun,
    WorkflowUpdate,
)
from backend.app.automation.scheduler import get_scheduler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/automation", tags=["automation"])


# ── Workflow CRUD ──────────────────────────────────────────────────────────────


@router.post("/workflows", response_model=WorkflowDefinition)
async def create_workflow(request: WorkflowCreate) -> WorkflowDefinition:
    """Create a new workflow definition."""
    try:
        engine = get_engine()
        definition = WorkflowDefinition(
            name=request.name,
            description=request.description,
            steps=request.steps,
            trigger_type=request.trigger_type,
            schedule=request.schedule,
        )
        return engine.create_workflow(definition)
    except Exception as exc:
        logger.error("Workflow creation error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/workflows", response_model=list[WorkflowInfo])
async def list_workflows() -> list[WorkflowInfo]:
    """List all workflow definitions."""
    engine = get_engine()
    return engine.list_workflows()


@router.get("/workflows/{workflow_id}", response_model=WorkflowDefinition)
async def get_workflow(workflow_id: str) -> WorkflowDefinition:
    """Get a specific workflow by ID."""
    engine = get_engine()
    wf = engine.get_workflow(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    return wf


@router.patch("/workflows/{workflow_id}", response_model=WorkflowDefinition)
async def update_workflow(
    workflow_id: str, request: WorkflowUpdate
) -> WorkflowDefinition:
    """Update a workflow definition."""
    engine = get_engine()
    updates = request.model_dump(exclude_none=True)
    updated = engine.update_workflow(workflow_id, **updates)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    return updated


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str) -> dict:
    """Delete a workflow and its run history."""
    engine = get_engine()
    # Also unschedule if scheduled
    scheduler = get_scheduler()
    await scheduler.unschedule_workflow(workflow_id)

    if not engine.delete_workflow(workflow_id):
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    return {"deleted": True, "workflow_id": workflow_id}


# ── Workflow Execution ─────────────────────────────────────────────────────────


@router.post("/workflows/{workflow_id}/run", response_model=WorkflowRun)
async def run_workflow(workflow_id: str) -> WorkflowRun:
    """Execute a workflow immediately (manual trigger)."""
    engine = get_engine()
    try:
        return await engine.execute_workflow(workflow_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Workflow execution error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/runs/{run_id}", response_model=WorkflowRun)
async def get_run(run_id: str) -> WorkflowRun:
    """Get details of a specific workflow run."""
    engine = get_engine()
    run = engine.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return run


@router.get("/workflows/{workflow_id}/runs", response_model=list[WorkflowRun])
async def get_workflow_runs(workflow_id: str) -> list[WorkflowRun]:
    """List all runs for a specific workflow."""
    engine = get_engine()
    if engine.get_workflow(workflow_id) is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    return engine.get_workflow_runs(workflow_id)


# ── Scheduling ─────────────────────────────────────────────────────────────────


@router.post("/workflows/{workflow_id}/schedule", response_model=ScheduleEntry)
async def schedule_workflow(
    workflow_id: str, config: ScheduleConfig
) -> ScheduleEntry:
    """Start a recurring schedule for a workflow."""
    engine = get_engine()
    wf = engine.get_workflow(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    scheduler = get_scheduler()
    return scheduler.schedule_workflow(
        workflow_id=workflow_id,
        workflow_name=wf.name,
        interval_seconds=config.interval_seconds,
        max_runs=config.max_runs,
    )


@router.delete("/workflows/{workflow_id}/schedule")
async def unschedule_workflow(workflow_id: str) -> dict:
    """Remove a workflow's recurring schedule."""
    scheduler = get_scheduler()
    removed = await scheduler.unschedule_workflow(workflow_id)
    if not removed:
        raise HTTPException(
            status_code=404,
            detail=f"No active schedule for workflow '{workflow_id}'",
        )
    return {"unscheduled": True, "workflow_id": workflow_id}


@router.get("/scheduler/status", response_model=SchedulerStatus)
async def scheduler_status() -> SchedulerStatus:
    """Get overall scheduler status."""
    scheduler = get_scheduler()
    return scheduler.get_status()
