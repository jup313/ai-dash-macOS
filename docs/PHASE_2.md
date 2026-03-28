# Phase 2 — Agents + Memory

## Overview

Phase 2 adds the **agent system** and **conversation memory** to ai-dash-macOS.
Agents are autonomous LLM interaction patterns (chat, summarize, analyze) managed
through a registry and executed with concurrency control. Conversations are stored
in-memory with automatic eviction when limits are reached.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   FastAPI App                    │
├──────────────┬──────────────────────────────────┤
│  /api/agents │       /api/conversations         │
├──────────────┴──────────────────────────────────┤
│  AgentExecutor  ←── Semaphore concurrency       │
│  AgentRegistry  ←── Built-in + custom agents    │
├─────────────────────────────────────────────────┤
│  ConversationStore  ←── In-memory + eviction    │
├─────────────────────────────────────────────────┤
│  LLM Router (Phase 1)                           │
│  Core: Config, Validation, Memory (Phase 0)     │
└─────────────────────────────────────────────────┘
```

## Components

### Agent System (`backend/app/agents/`)

| File | Purpose |
|------|---------|
| `models.py` | AgentType, TaskStatus, AgentConfig, AgentTask, AgentResult, AgentInfo, ExecutorStatus |
| `base.py` | BaseAgent ABC — execute() wrapper with timing/error handling, _call_llm() helper |
| `built_in.py` | ChatAgent, SummaryAgent, AnalysisAgent + BUILT_IN_AGENTS registry dict |
| `executor.py` | AgentExecutor — asyncio.Semaphore concurrency control, task tracking, singleton |
| `registry.py` | AgentRegistry — auto-init built-ins, CRUD, agent lookup, singleton |

### Conversation Memory (`backend/app/memory/`)

| File | Purpose |
|------|---------|
| `models.py` | ConversationMessage, Conversation, ConversationSummary, ConversationCreate, MemoryStats |
| `store.py` | ConversationStore — create, get, add_message, list, delete, clear, stats, eviction |

### API Endpoints

#### Agent Endpoints (`/api/agents`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/agents/task` | Submit a task to an agent |
| GET | `/api/agents/list` | List all registered agents |
| GET | `/api/agents/status` | Get executor status (active tasks, concurrency, counts) |
| GET | `/api/agents/{name}` | Get info about a specific agent |

#### Conversation Endpoints (`/api/conversations`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/conversations/` | Create a new conversation |
| GET | `/api/conversations/` | List all conversations (newest first) |
| GET | `/api/conversations/stats` | Get memory statistics |
| GET | `/api/conversations/{id}` | Get a conversation by ID |
| DELETE | `/api/conversations/{id}` | Delete a conversation |
| POST | `/api/conversations/{id}/messages` | Add a message |
| GET | `/api/conversations/{id}/messages` | Get messages (optional limit) |
| DELETE | `/api/conversations/` | Clear all conversations |

## Built-in Agents

| Agent | Type | System Prompt |
|-------|------|---------------|
| `chat` | CHAT | General-purpose conversational assistant |
| `summary` | SUMMARY | Summarization specialist (concise bullet points) |
| `analysis` | ANALYSIS | Code/text analysis expert (structured findings) |

## Key Design Decisions

1. **Semaphore-based concurrency**: `AgentExecutor` uses `asyncio.Semaphore` to limit
   concurrent agent executions (configurable via `MAX_AGENT_CONCURRENCY` env var).

2. **In-memory store with eviction**: `ConversationStore` keeps conversations in a dict
   with a configurable max limit. When exceeded, the oldest conversations are evicted.

3. **Singleton pattern with reset**: All singletons (registry, executor, store) have
   `reset_*()` functions for clean testing and graceful shutdown.

4. **BaseAgent execute() wrapper**: All agents inherit timing, error handling, and
   status tracking from `BaseAgent.execute()`. Subclasses only implement `process()`.

5. **LLM integration via _call_llm()**: Agents call the LLM through the Phase 1 router,
   maintaining provider abstraction and memory gating.

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `MAX_AGENT_CONCURRENCY` | `3` | Maximum concurrent agent tasks |

## Tests

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_agent_models.py` | 11 | Agent data models, validation, enums |
| `test_agents.py` | 20 | Registry, built-in agents, execution, executor |
| `test_conversation_store.py` | 20 | Store CRUD, limits, stats, eviction, singleton |
| `test_agent_api.py` | 11 | Agent + conversation API endpoints |
| **Total Phase 2** | **62** | |
| **Cumulative** | **191** | Phases 0 + 1 + 2 |

## Running Tests

```bash
# Phase 2 tests only
python -m pytest backend/tests/test_agent_models.py backend/tests/test_agents.py \
  backend/tests/test_conversation_store.py backend/tests/test_agent_api.py -v

# Full suite
python -m pytest -v
```

## Status

✅ **Phase 2 Complete** — 191/191 tests passing
