"""Tests for automation API endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.automation.engine import get_engine, reset_engine
from backend.app.automation.models import StepType, WorkflowDefinition, WorkflowStep
from backend.app.automation.scheduler import reset_scheduler
from backend.app.main import app


@pytest.fixture(autouse=True)
def _clean():
    reset_engine()
    reset_scheduler()
    yield
    reset_scheduler()
    reset_engine()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _step_payload(name: str = "s1", step_type: str = "delay", config: dict | None = None):
    return {
        "name": name,
        "step_type": step_type,
        "config": config or {"seconds": 0.01},
    }


def _workflow_payload(name: str = "test-wf"):
    return {
        "name": name,
        "steps": [_step_payload()],
    }


class TestWorkflowCRUDAPI:
    @pytest.mark.asyncio
    async def test_create_workflow(self, client):
        resp = await client.post("/api/automation/workflows", json=_workflow_payload("new"))
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "new"
        assert data["workflow_id"]
        assert len(data["steps"]) == 1

    @pytest.mark.asyncio
    async def test_list_workflows(self, client):
        await client.post("/api/automation/workflows", json=_workflow_payload("a"))
        await client.post("/api/automation/workflows", json=_workflow_payload("b"))
        resp = await client.get("/api/automation/workflows")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @pytest.mark.asyncio
    async def test_get_workflow(self, client):
        create = await client.post("/api/automation/workflows", json=_workflow_payload("get-me"))
        wf_id = create.json()["workflow_id"]
        resp = await client.get(f"/api/automation/workflows/{wf_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "get-me"

    @pytest.mark.asyncio
    async def test_get_workflow_not_found(self, client):
        resp = await client.get("/api/automation/workflows/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_workflow(self, client):
        create = await client.post("/api/automation/workflows", json=_workflow_payload("orig"))
        wf_id = create.json()["workflow_id"]
        resp = await client.patch(
            f"/api/automation/workflows/{wf_id}",
            json={"name": "updated"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "updated"

    @pytest.mark.asyncio
    async def test_update_workflow_not_found(self, client):
        resp = await client.patch(
            "/api/automation/workflows/nope",
            json={"name": "x"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_workflow(self, client):
        create = await client.post("/api/automation/workflows", json=_workflow_payload("del"))
        wf_id = create.json()["workflow_id"]
        resp = await client.delete(f"/api/automation/workflows/{wf_id}")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    @pytest.mark.asyncio
    async def test_delete_workflow_not_found(self, client):
        resp = await client.delete("/api/automation/workflows/nope")
        assert resp.status_code == 404


class TestWorkflowExecutionAPI:
    @pytest.mark.asyncio
    async def test_run_workflow(self, client):
        create = await client.post("/api/automation/workflows", json=_workflow_payload("run-me"))
        wf_id = create.json()["workflow_id"]
        resp = await client.post(f"/api/automation/workflows/{wf_id}/run")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert len(data["step_results"]) == 1

    @pytest.mark.asyncio
    async def test_run_workflow_not_found(self, client):
        resp = await client.post("/api/automation/workflows/nope/run")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_run(self, client):
        create = await client.post("/api/automation/workflows", json=_workflow_payload("run"))
        wf_id = create.json()["workflow_id"]
        run_resp = await client.post(f"/api/automation/workflows/{wf_id}/run")
        run_id = run_resp.json()["run_id"]
        resp = await client.get(f"/api/automation/runs/{run_id}")
        assert resp.status_code == 200
        assert resp.json()["run_id"] == run_id

    @pytest.mark.asyncio
    async def test_get_run_not_found(self, client):
        resp = await client.get("/api/automation/runs/nope")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_workflow_runs(self, client):
        create = await client.post("/api/automation/workflows", json=_workflow_payload("runs"))
        wf_id = create.json()["workflow_id"]
        await client.post(f"/api/automation/workflows/{wf_id}/run")
        await client.post(f"/api/automation/workflows/{wf_id}/run")
        resp = await client.get(f"/api/automation/workflows/{wf_id}/runs")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestSchedulingAPI:
    @pytest.mark.asyncio
    async def test_schedule_workflow(self, client):
        create = await client.post("/api/automation/workflows", json=_workflow_payload("sched"))
        wf_id = create.json()["workflow_id"]
        resp = await client.post(
            f"/api/automation/workflows/{wf_id}/schedule",
            json={"interval_seconds": 120},
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True

    @pytest.mark.asyncio
    async def test_schedule_workflow_not_found(self, client):
        resp = await client.post(
            "/api/automation/workflows/nope/schedule",
            json={"interval_seconds": 120},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_unschedule_workflow(self, client):
        create = await client.post("/api/automation/workflows", json=_workflow_payload("unsched"))
        wf_id = create.json()["workflow_id"]
        await client.post(
            f"/api/automation/workflows/{wf_id}/schedule",
            json={"interval_seconds": 120},
        )
        resp = await client.delete(f"/api/automation/workflows/{wf_id}/schedule")
        assert resp.status_code == 200
        assert resp.json()["unscheduled"] is True

    @pytest.mark.asyncio
    async def test_unschedule_not_found(self, client):
        resp = await client.delete("/api/automation/workflows/nope/schedule")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_scheduler_status(self, client):
        resp = await client.get("/api/automation/scheduler/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "active_schedules" in data
        assert "schedules" in data
