"""
Agent executor — manages concurrent agent task execution.

Features:
- Semaphore-based concurrency control (max_agent_concurrency)
- Task tracking (active, completed, failed)
- Async execution with timeout support
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from backend.app.agents.models import AgentResult, AgentTask, ExecutorStatus, TaskStatus
from backend.app.agents.registry import get_registry
from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)


class AgentExecutor:
    """
    Manages concurrent agent task execution.

    Uses asyncio.Semaphore to enforce max_agent_concurrency.
    Tracks task statistics for monitoring.
    """

    def __init__(self, max_concurrency: int | None = None):
        settings = get_settings()
        self._max_concurrency = max_concurrency or settings.max_agent_concurrency
        self._semaphore = asyncio.Semaphore(self._max_concurrency)
        self._active_tasks: dict[str, AgentTask] = {}
        self._total_completed = 0
        self._total_failed = 0

    async def submit(self, task: AgentTask) -> AgentResult:
        """
        Submit a task for execution with concurrency control.

        Blocks if max concurrency is reached until a slot opens.

        Args:
            task: The agent task to execute.

        Returns:
            AgentResult with output or error.
        """
        async with self._semaphore:
            self._active_tasks[task.task_id] = task
            try:
                result = await self._execute(task)
                if result.status == TaskStatus.COMPLETED:
                    self._total_completed += 1
                else:
                    self._total_failed += 1
                return result
            finally:
                self._active_tasks.pop(task.task_id, None)

    async def _execute(self, task: AgentTask) -> AgentResult:
        """Execute a single task."""
        registry = get_registry()

        agent = registry.get_agent(task.agent_name)
        if agent is None:
            return AgentResult(
                task_id=task.task_id,
                agent_name=task.agent_name,
                status=TaskStatus.FAILED,
                error=f"Agent '{task.agent_name}' not found. "
                f"Available: {registry.list_agent_names()}",
                completed_at=datetime.now(timezone.utc),
            )

        logger.info("Executing task %s on agent %s", task.task_id[:8], task.agent_name)
        return await agent.execute(task)

    def get_status(self) -> ExecutorStatus:
        """Get executor status."""
        registry = get_registry()
        return ExecutorStatus(
            active_tasks=len(self._active_tasks),
            max_concurrency=self._max_concurrency,
            registered_agents=len(registry.list_agent_names()),
            total_completed=self._total_completed,
            total_failed=self._total_failed,
        )

    @property
    def active_count(self) -> int:
        return len(self._active_tasks)

    @property
    def max_concurrency(self) -> int:
        return self._max_concurrency


# Singleton executor
_executor: AgentExecutor | None = None


def get_executor() -> AgentExecutor:
    """Get or create the executor singleton."""
    global _executor
    if _executor is None:
        _executor = AgentExecutor()
    return _executor


def reset_executor() -> None:
    """Reset the executor singleton (for testing)."""
    global _executor
    _executor = None
