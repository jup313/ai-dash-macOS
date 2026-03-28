"""
Tests for agent data models.
"""

from __future__ import annotations

import pytest

from backend.app.agents.models import (
    AgentConfig,
    AgentInfo,
    AgentResult,
    AgentTask,
    AgentType,
    ExecutorStatus,
    TaskStatus,
)


class TestAgentType:
    def test_values(self):
        assert AgentType.CHAT == "chat"
        assert AgentType.SUMMARY == "summary"
        assert AgentType.ANALYSIS == "analysis"
        assert AgentType.CUSTOM == "custom"


class TestTaskStatus:
    def test_values(self):
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"


class TestAgentConfig:
    def test_create(self):
        cfg = AgentConfig(name="test", agent_type=AgentType.CHAT)
        assert cfg.name == "test"
        assert cfg.temperature == 0.7

    def test_with_overrides(self):
        cfg = AgentConfig(
            name="custom",
            agent_type=AgentType.CUSTOM,
            model="llama3:8b",
            provider="ollama",
            temperature=0.3,
            max_tokens=1024,
        )
        assert cfg.model == "llama3:8b"
        assert cfg.max_tokens == 1024


class TestAgentTask:
    def test_create(self):
        task = AgentTask(agent_name="chat", input_text="Hello")
        assert task.agent_name == "chat"
        assert task.input_text == "Hello"
        assert task.task_id  # auto-generated

    def test_with_context(self):
        task = AgentTask(
            agent_name="analysis",
            input_text="code here",
            context={"type": "code", "language": "python"},
        )
        assert task.context["type"] == "code"

    def test_empty_input_rejected(self):
        with pytest.raises(Exception):
            AgentTask(agent_name="chat", input_text="")


class TestAgentResult:
    def test_success(self):
        result = AgentResult(
            task_id="test-id",
            agent_name="chat",
            status=TaskStatus.COMPLETED,
            output="Hello!",
            model_used="llama3:8b",
            tokens_used=15,
        )
        assert result.status == TaskStatus.COMPLETED
        assert result.output == "Hello!"

    def test_failure(self):
        result = AgentResult(
            task_id="test-id",
            agent_name="chat",
            status=TaskStatus.FAILED,
            error="Connection refused",
        )
        assert result.status == TaskStatus.FAILED
        assert result.error is not None


class TestAgentInfo:
    def test_create(self):
        info = AgentInfo(
            name="chat",
            agent_type="chat",
            description="Test agent",
            system_prompt="Be helpful",
        )
        assert info.name == "chat"


class TestExecutorStatus:
    def test_create(self):
        status = ExecutorStatus(
            active_tasks=1,
            max_concurrency=2,
            registered_agents=3,
            total_completed=10,
            total_failed=1,
        )
        assert status.active_tasks == 1
        assert status.max_concurrency == 2
