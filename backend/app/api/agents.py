"""
Agent API endpoints — task submission, agent listing, executor status.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend.app.agents.executor import get_executor
from backend.app.agents.models import AgentInfo, AgentResult, AgentTask, ExecutorStatus
from backend.app.agents.registry import get_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("/task", response_model=AgentResult)
async def submit_task(task: AgentTask) -> AgentResult:
    """Submit a task to an agent for execution."""
    try:
        executor = get_executor()
        return await executor.submit(task)
    except Exception as exc:
        logger.error("Task submission error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/list", response_model=list[AgentInfo])
async def list_agents() -> list[AgentInfo]:
    """List all registered agents."""
    registry = get_registry()
    return registry.list_agents()


@router.get("/status", response_model=ExecutorStatus)
async def executor_status() -> ExecutorStatus:
    """Get agent executor status."""
    executor = get_executor()
    return executor.get_status()


@router.get("/{agent_name}", response_model=AgentInfo)
async def get_agent(agent_name: str) -> AgentInfo:
    """Get info about a specific agent."""
    registry = get_registry()
    agent = registry.get_agent(agent_name)
    if agent is None:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_name}' not found. Available: {registry.list_agent_names()}",
        )
    return AgentInfo(
        name=agent.name,
        agent_type=agent.config.agent_type.value,
        description=agent.config.description,
        system_prompt=agent.config.system_prompt,
        model=agent.config.model,
        provider=agent.config.provider,
    )
