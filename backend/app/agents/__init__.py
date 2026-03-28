"""
Agents module — multi-agent orchestration system.

Provides:
- Agent registry with built-in agents (chat, summary, analysis)
- Concurrent task executor with semaphore-based gating
- Base agent interface for custom agents
"""

from backend.app.agents.base import BaseAgent
from backend.app.agents.executor import AgentExecutor, get_executor, reset_executor
from backend.app.agents.models import (
    AgentConfig,
    AgentInfo,
    AgentResult,
    AgentTask,
    AgentType,
    ExecutorStatus,
    TaskStatus,
)
from backend.app.agents.registry import AgentRegistry, get_registry, reset_registry

__all__ = [
    "AgentConfig",
    "AgentExecutor",
    "AgentInfo",
    "AgentRegistry",
    "AgentResult",
    "AgentTask",
    "AgentType",
    "BaseAgent",
    "ExecutorStatus",
    "TaskStatus",
    "get_executor",
    "get_registry",
    "reset_executor",
    "reset_registry",
]
