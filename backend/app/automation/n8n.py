"""
n8n Connector — Bridge between ai-dash and n8n automation platform.

Provides:
- Connection health check
- List/activate/deactivate n8n workflows
- Execute workflows via webhook or API
- Retrieve execution history
- WebSocket event bridge (future)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class N8nWorkflow:
    """Represents an n8n workflow."""

    id: str
    name: str
    active: bool
    tags: list[str] = field(default_factory=list)
    nodes_count: int = 0
    created_at: str = ""
    updated_at: str = ""


@dataclass
class N8nExecution:
    """Represents an n8n execution result."""

    id: str
    workflow_id: str
    workflow_name: str
    status: str  # "success", "error", "running", "waiting"
    started_at: str = ""
    finished_at: str = ""
    mode: str = ""  # "manual", "trigger", "webhook"
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class N8nStatus:
    """n8n connection status."""

    connected: bool
    url: str
    version: str = ""
    workflow_count: int = 0
    active_workflows: int = 0
    detail: str = ""


class N8nConnector:
    """
    Client for the n8n REST API.

    n8n API docs: https://docs.n8n.io/api/
    Supports both n8n Cloud and self-hosted instances.
    """

    def __init__(self, base_url: str, api_key: str = "", timeout: float = 15.0):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def base_url(self) -> str:
        return self._base_url

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            headers: dict[str, str] = {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            if self._api_key:
                headers["X-N8N-API-KEY"] = self._api_key
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=headers,
                timeout=self._timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ── Health / Status ────────────────────────────────────────────────────

    async def check_connection(self) -> N8nStatus:
        """Check if n8n is reachable and return status."""
        if not self._base_url:
            return N8nStatus(
                connected=False,
                url="",
                detail="n8n URL not configured",
            )
        try:
            client = self._get_client()
            # Try the workflows endpoint to verify connectivity + auth
            resp = await client.get("/api/v1/workflows", params={"limit": 1})
            resp.raise_for_status()

            # Get workflow counts
            all_wf = await self.list_workflows()
            active = sum(1 for w in all_wf if w.active)

            return N8nStatus(
                connected=True,
                url=self._base_url,
                workflow_count=len(all_wf),
                active_workflows=active,
                detail="Connected",
            )
        except httpx.ConnectError:
            return N8nStatus(
                connected=False,
                url=self._base_url,
                detail=f"Cannot connect to {self._base_url}",
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                return N8nStatus(
                    connected=False,
                    url=self._base_url,
                    detail="Authentication failed — check API key",
                )
            return N8nStatus(
                connected=False,
                url=self._base_url,
                detail=f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
            )
        except Exception as exc:
            return N8nStatus(
                connected=False,
                url=self._base_url,
                detail=str(exc)[:200],
            )

    # ── Workflows ──────────────────────────────────────────────────────────

    async def list_workflows(self) -> list[N8nWorkflow]:
        """List all n8n workflows."""
        try:
            client = self._get_client()
            resp = await client.get("/api/v1/workflows")
            resp.raise_for_status()
            data = resp.json()

            workflows: list[N8nWorkflow] = []
            items = data.get("data", data) if isinstance(data, dict) else data
            if isinstance(items, list):
                for wf in items:
                    workflows.append(
                        N8nWorkflow(
                            id=str(wf.get("id", "")),
                            name=wf.get("name", "Untitled"),
                            active=wf.get("active", False),
                            tags=[t.get("name", "") for t in wf.get("tags", [])],
                            nodes_count=len(wf.get("nodes", [])),
                            created_at=wf.get("createdAt", ""),
                            updated_at=wf.get("updatedAt", ""),
                        )
                    )
            return workflows
        except Exception as exc:
            logger.error("n8n list workflows error: %s", exc)
            return []

    async def get_workflow(self, workflow_id: str) -> Optional[N8nWorkflow]:
        """Get a specific n8n workflow."""
        try:
            client = self._get_client()
            resp = await client.get(f"/api/v1/workflows/{workflow_id}")
            resp.raise_for_status()
            wf = resp.json()
            return N8nWorkflow(
                id=str(wf.get("id", "")),
                name=wf.get("name", "Untitled"),
                active=wf.get("active", False),
                tags=[t.get("name", "") for t in wf.get("tags", [])],
                nodes_count=len(wf.get("nodes", [])),
                created_at=wf.get("createdAt", ""),
                updated_at=wf.get("updatedAt", ""),
            )
        except Exception as exc:
            logger.error("n8n get workflow error: %s", exc)
            return None

    async def activate_workflow(self, workflow_id: str) -> bool:
        """Activate an n8n workflow."""
        try:
            client = self._get_client()
            resp = await client.patch(
                f"/api/v1/workflows/{workflow_id}",
                json={"active": True},
            )
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error("n8n activate error: %s", exc)
            return False

    async def deactivate_workflow(self, workflow_id: str) -> bool:
        """Deactivate an n8n workflow."""
        try:
            client = self._get_client()
            resp = await client.patch(
                f"/api/v1/workflows/{workflow_id}",
                json={"active": False},
            )
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error("n8n deactivate error: %s", exc)
            return False

    # ── Execution ──────────────────────────────────────────────────────────

    async def execute_workflow(
        self, workflow_id: str, data: dict[str, Any] | None = None
    ) -> Optional[N8nExecution]:
        """
        Execute an n8n workflow via the API.

        For webhook-triggered workflows, use trigger_webhook() instead.
        """
        try:
            client = self._get_client()
            payload: dict[str, Any] = {}
            if data:
                payload["data"] = data

            # n8n API v1 execution endpoint
            resp = await client.post(
                f"/api/v1/workflows/{workflow_id}/run",
                json=payload,
            )
            resp.raise_for_status()
            result = resp.json()
            data_result = result.get("data", result)

            return N8nExecution(
                id=str(data_result.get("id", "")),
                workflow_id=workflow_id,
                workflow_name=data_result.get("workflowData", {}).get("name", ""),
                status="success" if data_result.get("finished") else "running",
                started_at=data_result.get("startedAt", ""),
                finished_at=data_result.get("stoppedAt", ""),
                mode=data_result.get("mode", "manual"),
                data=data_result.get("data", {}),
            )
        except Exception as exc:
            logger.error("n8n execute error: %s", exc)
            return None

    async def trigger_webhook(
        self,
        webhook_path: str,
        data: dict[str, Any] | None = None,
        method: str = "POST",
    ) -> dict[str, Any]:
        """
        Trigger an n8n workflow via its webhook URL.

        Args:
            webhook_path: The webhook path (e.g., "my-webhook" or full URL)
            data: JSON payload to send
            method: HTTP method (POST, GET)
        """
        try:
            client = self._get_client()
            url = webhook_path if webhook_path.startswith("http") else f"/webhook/{webhook_path}"

            if method.upper() == "GET":
                resp = await client.get(url, params=data or {})
            else:
                resp = await client.post(url, json=data or {})

            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.error("n8n webhook trigger error: %s", exc)
            return {"error": str(exc)}

    # ── Executions History ─────────────────────────────────────────────────

    async def list_executions(
        self,
        workflow_id: str | None = None,
        limit: int = 20,
        status: str | None = None,
    ) -> list[N8nExecution]:
        """List recent n8n executions."""
        try:
            client = self._get_client()
            params: dict[str, Any] = {"limit": limit}
            if workflow_id:
                params["workflowId"] = workflow_id
            if status:
                params["status"] = status

            resp = await client.get("/api/v1/executions", params=params)
            resp.raise_for_status()
            data = resp.json()

            executions: list[N8nExecution] = []
            items = data.get("data", data) if isinstance(data, dict) else data
            if isinstance(items, list):
                for ex in items:
                    executions.append(
                        N8nExecution(
                            id=str(ex.get("id", "")),
                            workflow_id=str(ex.get("workflowId", "")),
                            workflow_name=ex.get("workflowData", {}).get("name", ""),
                            status=ex.get("status", "unknown"),
                            started_at=ex.get("startedAt", ""),
                            finished_at=ex.get("stoppedAt", ""),
                            mode=ex.get("mode", ""),
                        )
                    )
            return executions
        except Exception as exc:
            logger.error("n8n list executions error: %s", exc)
            return []


# ── Singleton ──────────────────────────────────────────────────────────────────

_connector: N8nConnector | None = None


def get_n8n_connector() -> N8nConnector:
    """Get or create the n8n connector singleton."""
    global _connector
    if _connector is None:
        from backend.app.core.config import get_settings

        settings = get_settings()
        _connector = N8nConnector(
            base_url=settings.n8n_url,
            api_key=settings.n8n_api_key,
        )
    return _connector


def reset_n8n_connector() -> None:
    """Reset the n8n connector (for config changes)."""
    global _connector
    if _connector is not None:
        # Note: can't await close() here, but the client will be garbage collected
        _connector = None
