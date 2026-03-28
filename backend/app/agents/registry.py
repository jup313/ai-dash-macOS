"""
Agent registry — discovers and manages available agents.

Handles:
- Registration of built-in and custom agents
- Agent lookup by name
- Agent listing for API responses
"""

from __future__ import annotations

import logging

from backend.app.agents.base import BaseAgent
from backend.app.agents.built_in import BUILT_IN_AGENTS
from backend.app.agents.models import AgentConfig, AgentInfo

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Manages registered agent instances."""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}
        self._initialized = False

    def initialize(self) -> None:
        """Register built-in agents."""
        if self._initialized:
            return

        for name, agent_cls in BUILT_IN_AGENTS.items():
            agent = agent_cls()
            self._agents[name] = agent
            logger.info("Registered built-in agent: %s", name)

        self._initialized = True

    def register(self, agent: BaseAgent) -> None:
        """Register a custom agent."""
        self._agents[agent.name] = agent
        logger.info("Registered agent: %s", agent.name)

    def get_agent(self, name: str) -> BaseAgent | None:
        """Get an agent by name."""
        self.initialize()
        return self._agents.get(name)

    def list_agent_names(self) -> list[str]:
        """List all registered agent names."""
        self.initialize()
        return list(self._agents.keys())

    def list_agents(self) -> list[AgentInfo]:
        """List all agents with their info."""
        self.initialize()
        return [
            AgentInfo(
                name=agent.name,
                agent_type=agent.config.agent_type.value,
                description=agent.config.description,
                system_prompt=agent.config.system_prompt,
                model=agent.config.model,
                provider=agent.config.provider,
            )
            for agent in self._agents.values()
        ]

    def remove(self, name: str) -> bool:
        """Remove an agent. Returns True if found and removed."""
        return self._agents.pop(name, None) is not None


# Singleton registry
_registry: AgentRegistry | None = None


def get_registry() -> AgentRegistry:
    """Get or create the registry singleton."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
        _registry.initialize()
    return _registry


def reset_registry() -> None:
    """Reset the registry singleton (for testing)."""
    global _registry
    _registry = None
