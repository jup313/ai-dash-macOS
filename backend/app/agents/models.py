"""
Agent data models — task definitions, results, and status tracking.

Provider-agnostic agent definitions used across the executor and registry.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Available agent types."""

    CHAT = "chat"
    SUMMARY = "summary"
    ANALYSIS = "analysis"
    CUSTOM = "custom"


class TaskStatus(str, Enum):
    """Agent task lifecycle status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentConfig(BaseModel):
    """Configuration for an agent instance."""

    name: str = Field(..., description="Agent name")
    agent_type: AgentType = Field(..., description="Agent type")
    description: str = Field(default="", description="Agent description")
    system_prompt: str = Field(
        default="You are a helpful AI assistant.",
        description="System prompt for the agent",
    )
    model: Optional[str] = Field(
        default=None,
        description="Model override (uses provider default if None)",
    )
    provider: Optional[str] = Field(
        default=None,
        description="Provider override",
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=32768)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentTask(BaseModel):
    """A task submitted to an agent."""

    task_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique task identifier",
    )
    agent_name: str = Field(..., description="Target agent name")
    input_text: str = Field(..., min_length=1, description="Task input text")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for the task",
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Link to conversation session",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class AgentResult(BaseModel):
    """Result of an agent task execution."""

    task_id: str
    agent_name: str
    status: TaskStatus
    output: str = ""
    error: Optional[str] = None
    model_used: str = ""
    provider_used: str = ""
    tokens_used: Optional[int] = None
    duration_ms: Optional[float] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    completed_at: Optional[datetime] = None


class AgentInfo(BaseModel):
    """Public info about a registered agent."""

    name: str
    agent_type: str
    description: str
    system_prompt: str
    model: Optional[str] = None
    provider: Optional[str] = None


class ExecutorStatus(BaseModel):
    """Agent executor status."""

    active_tasks: int
    max_concurrency: int
    registered_agents: int
    total_completed: int
    total_failed: int
