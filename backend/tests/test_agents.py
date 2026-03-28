"""
Tests for agent system — registry, executor, built-in agents.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.app.agents.built_in import ChatAgent, SummaryAgent, AnalysisAgent
from backend.app.agents.executor import AgentExecutor, get_executor, reset_executor
from backend.app.agents.models import AgentResult, AgentTask, AgentType, TaskStatus
from backend.app.agents.registry import AgentRegistry, get_registry, reset_registry


@pytest.fixture(autouse=True)
def _reset():
    reset_registry()
    reset_executor()
    yield
    reset_registry()
    reset_executor()


class TestAgentRegistry:
    def test_initialize_registers_built_in(self):
        registry = AgentRegistry()
        registry.initialize()
        names = registry.list_agent_names()
        assert "chat" in names
        assert "summary" in names
        assert "analysis" in names

    def test_get_agent(self):
        registry = AgentRegistry()
        registry.initialize()
        agent = registry.get_agent("chat")
        assert agent is not None
        assert agent.name == "chat"

    def test_get_nonexistent(self):
        registry = AgentRegistry()
        registry.initialize()
        assert registry.get_agent("nonexistent") is None

    def test_list_agents(self):
        registry = AgentRegistry()
        registry.initialize()
        agents = registry.list_agents()
        assert len(agents) == 3

    def test_remove(self):
        registry = AgentRegistry()
        registry.initialize()
        assert registry.remove("chat") is True
        assert registry.get_agent("chat") is None

    def test_remove_nonexistent(self):
        registry = AgentRegistry()
        registry.initialize()
        assert registry.remove("nonexistent") is False

    def test_singleton(self):
        reset_registry()
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_reset(self):
        reset_registry()
        r1 = get_registry()
        reset_registry()
        r2 = get_registry()
        assert r1 is not r2


class TestBuiltInAgents:
    def test_chat_agent_config(self):
        agent = ChatAgent()
        assert agent.name == "chat"
        assert agent.config.agent_type == AgentType.CHAT

    def test_summary_agent_config(self):
        agent = SummaryAgent()
        assert agent.name == "summary"
        assert agent.config.temperature == 0.3

    def test_analysis_agent_config(self):
        agent = AnalysisAgent()
        assert agent.name == "analysis"
        assert agent.config.temperature == 0.2


class TestAgentExecution:
    @pytest.mark.asyncio
    async def test_chat_agent_success(self):
        agent = ChatAgent()
        task = AgentTask(agent_name="chat", input_text="Hello")

        with patch.object(agent, "_call_llm", return_value=("Hi!", "llama3:8b", "ollama", 10)):
            result = await agent.execute(task)

        assert result.status == TaskStatus.COMPLETED
        assert result.output == "Hi!"
        assert result.duration_ms is not None
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_summary_agent_success(self):
        agent = SummaryAgent()
        task = AgentTask(agent_name="summary", input_text="Long text here...")

        with patch.object(agent, "_call_llm", return_value=("Summary: ...", "llama3:8b", "ollama", 20)):
            result = await agent.execute(task)

        assert result.status == TaskStatus.COMPLETED
        assert "Summary" in result.output

    @pytest.mark.asyncio
    async def test_analysis_agent_code(self):
        agent = AnalysisAgent()
        task = AgentTask(
            agent_name="analysis",
            input_text="def hello(): pass",
            context={"type": "code", "language": "python"},
        )

        with patch.object(agent, "_call_llm", return_value=("Analysis: ...", "llama3:8b", "ollama", 15)):
            result = await agent.execute(task)

        assert result.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_agent_handles_error(self):
        agent = ChatAgent()
        task = AgentTask(agent_name="chat", input_text="Hello")

        with patch.object(agent, "_call_llm", side_effect=Exception("LLM error")):
            result = await agent.execute(task)

        assert result.status == TaskStatus.FAILED
        assert "LLM error" in result.error


class TestAgentExecutor:
    @pytest.mark.asyncio
    async def test_submit_success(self):
        executor = AgentExecutor(max_concurrency=2)
        task = AgentTask(agent_name="chat", input_text="Hello")

        mock_result = AgentResult(
            task_id=task.task_id,
            agent_name="chat",
            status=TaskStatus.COMPLETED,
            output="Hi!",
        )

        with patch(
            "backend.app.agents.executor.get_registry"
        ) as mock_reg:
            mock_agent = AsyncMock()
            mock_agent.execute.return_value = mock_result
            mock_reg.return_value.get_agent.return_value = mock_agent
            mock_reg.return_value.list_agent_names.return_value = ["chat"]

            result = await executor.submit(task)

        assert result.status == TaskStatus.COMPLETED
        assert executor._total_completed == 1

    @pytest.mark.asyncio
    async def test_submit_agent_not_found(self):
        executor = AgentExecutor(max_concurrency=2)
        task = AgentTask(agent_name="nonexistent", input_text="Hello")

        with patch(
            "backend.app.agents.executor.get_registry"
        ) as mock_reg:
            mock_reg.return_value.get_agent.return_value = None
            mock_reg.return_value.list_agent_names.return_value = ["chat"]

            result = await executor.submit(task)

        assert result.status == TaskStatus.FAILED
        assert "not found" in result.error

    def test_get_status(self):
        executor = AgentExecutor(max_concurrency=2)
        status = executor.get_status()
        assert status.max_concurrency == 2
        assert status.active_tasks == 0

    def test_singleton(self):
        reset_executor()
        e1 = get_executor()
        e2 = get_executor()
        assert e1 is e2
