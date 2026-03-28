"""
Built-in agents — pre-configured agents for common tasks.

Agents:
- ChatAgent: General conversation
- SummaryAgent: Text summarization
- AnalysisAgent: Code/text analysis
"""

from __future__ import annotations

from backend.app.agents.base import BaseAgent
from backend.app.agents.models import (
    AgentConfig,
    AgentResult,
    AgentTask,
    AgentType,
    TaskStatus,
)


class ChatAgent(BaseAgent):
    """General-purpose conversational agent."""

    def __init__(self, config: AgentConfig | None = None):
        if config is None:
            config = AgentConfig(
                name="chat",
                agent_type=AgentType.CHAT,
                description="General-purpose conversational assistant",
                system_prompt=(
                    "You are a helpful AI assistant running locally on macOS Apple Silicon. "
                    "Provide clear, concise, and accurate responses."
                ),
            )
        super().__init__(config)

    async def process(self, task: AgentTask) -> AgentResult:
        content, model, provider, tokens = await self._call_llm(task.input_text)
        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatus.COMPLETED,
            output=content,
            model_used=model,
            provider_used=provider,
            tokens_used=tokens,
        )


class SummaryAgent(BaseAgent):
    """Text summarization agent."""

    def __init__(self, config: AgentConfig | None = None):
        if config is None:
            config = AgentConfig(
                name="summary",
                agent_type=AgentType.SUMMARY,
                description="Summarizes text into concise key points",
                system_prompt=(
                    "You are a summarization expert. Given text, provide a clear, "
                    "concise summary highlighting the key points. Use bullet points "
                    "for multiple items. Keep summaries under 200 words unless "
                    "the input is very long."
                ),
                temperature=0.3,
            )
        super().__init__(config)

    async def process(self, task: AgentTask) -> AgentResult:
        prompt = f"Summarize the following:\n\n{task.input_text}"
        content, model, provider, tokens = await self._call_llm(prompt)
        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatus.COMPLETED,
            output=content,
            model_used=model,
            provider_used=provider,
            tokens_used=tokens,
        )


class AnalysisAgent(BaseAgent):
    """Code and text analysis agent."""

    def __init__(self, config: AgentConfig | None = None):
        if config is None:
            config = AgentConfig(
                name="analysis",
                agent_type=AgentType.ANALYSIS,
                description="Analyzes code or text for patterns, issues, and suggestions",
                system_prompt=(
                    "You are an expert code and text analyst. When given code, "
                    "analyze it for: correctness, potential bugs, performance issues, "
                    "security concerns, and style improvements. When given text, "
                    "analyze structure, clarity, and completeness. "
                    "Always provide actionable suggestions."
                ),
                temperature=0.2,
            )
        super().__init__(config)

    async def process(self, task: AgentTask) -> AgentResult:
        context_type = task.context.get("type", "general")
        if context_type == "code":
            language = task.context.get("language", "")
            prompt = f"Analyze this {language} code:\n\n```{language}\n{task.input_text}\n```"
        else:
            prompt = f"Analyze the following:\n\n{task.input_text}"

        content, model, provider, tokens = await self._call_llm(prompt)
        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatus.COMPLETED,
            output=content,
            model_used=model,
            provider_used=provider,
            tokens_used=tokens,
        )


# Registry of built-in agent factories
BUILT_IN_AGENTS: dict[str, type[BaseAgent]] = {
    "chat": ChatAgent,
    "summary": SummaryAgent,
    "analysis": AnalysisAgent,
}
