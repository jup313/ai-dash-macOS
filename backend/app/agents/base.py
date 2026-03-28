"""
Base agent — abstract interface for all agents.

Each agent wraps an LLM interaction pattern with:
- A system prompt defining behavior
- Optional pre/post processing
- Conversation context awareness
"""

from __future__ import annotations

import abc
import logging
import time
from datetime import datetime, timezone

from backend.app.agents.models import AgentConfig, AgentResult, AgentTask, TaskStatus
from backend.app.llm.models import ChatRequest, Message, Role
from backend.app.llm.router import get_router

logger = logging.getLogger(__name__)


class BaseAgent(abc.ABC):
    """Abstract base class for agents."""

    def __init__(self, config: AgentConfig):
        self._config = config

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def config(self) -> AgentConfig:
        return self._config

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Execute a task with error handling and timing.

        Subclasses should override `process()` for custom logic.
        """
        start = time.monotonic()
        try:
            result = await self.process(task)
            result.duration_ms = (time.monotonic() - start) * 1000
            result.completed_at = datetime.now(timezone.utc)
            return result
        except Exception as exc:
            duration = (time.monotonic() - start) * 1000
            logger.error("Agent %s failed: %s", self.name, exc)
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatus.FAILED,
                error=str(exc),
                duration_ms=duration,
                completed_at=datetime.now(timezone.utc),
            )

    @abc.abstractmethod
    async def process(self, task: AgentTask) -> AgentResult:
        """
        Process a task. Must be implemented by subclasses.

        Args:
            task: The agent task to process.

        Returns:
            AgentResult with output or error.
        """
        ...

    async def _call_llm(
        self,
        user_input: str,
        history: list[Message] | None = None,
    ) -> tuple[str, str, str, int | None]:
        """
        Call the LLM through the router.

        Args:
            user_input: The user's input text.
            history: Optional conversation history.

        Returns:
            Tuple of (content, model_used, provider_used, tokens_used).
        """
        messages: list[Message] = []

        # System prompt
        if self._config.system_prompt:
            messages.append(Message(role=Role.SYSTEM, content=self._config.system_prompt))

        # History
        if history:
            messages.extend(history)

        # Current input
        messages.append(Message(role=Role.USER, content=user_input))

        request = ChatRequest(
            messages=messages,
            model=self._config.model,
            provider=self._config.provider,
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
        )

        router = get_router()
        response = await router.chat(request)

        tokens = response.usage.total_tokens if response.usage else None
        return response.content, response.model, response.provider, tokens
