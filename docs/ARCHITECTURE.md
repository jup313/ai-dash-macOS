# Architecture

## System Overview

ai-dash-macOS is a Universal LLM Control Center built exclusively for macOS Apple Silicon. It follows a local-first, async-first architecture optimized for 28GB unified memory systems.

## Design Principles

1. **Local-First** — Everything runs locally by default. Cloud is opt-in.
2. **Async-First** — All I/O operations use asyncio. No blocking calls.
3. **Memory-Aware** — Intelligent model loading within 28GB constraints.
4. **Secure by Default** — localhost-only, no personal data, env-var config.
5. **Provider-Agnostic** — Universal LLM router with adapter pattern.

## Architecture Diagram

```
┌─────────────────────────────────────────────┐
│              Frontend (React)                │
│  ┌─────┐ ┌──────┐ ┌──────┐ ┌───────────┐   │
│  │Chat │ │Models│ │Agents│ │Monitoring  │   │
│  └──┬──┘ └──┬───┘ └──┬───┘ └─────┬─────┘   │
│     └────────┴────────┴───────────┘         │
│              API Calls Only                  │
└─────────────────┬───────────────────────────┘
                  │ HTTP/SSE
┌─────────────────┴───────────────────────────┐
│              FastAPI Backend                  │
│  ┌──────────────────────────────────────┐   │
│  │           API Routes                  │   │
│  │  /health  /chat  /models  /agents    │   │
│  └──────────────┬───────────────────────┘   │
│  ┌──────────────┴───────────────────────┐   │
│  │           LLM Router                  │   │
│  │  ┌─────────┐ ┌────────┐ ┌─────────┐ │   │
│  │  │ Ollama  │ │OpenAI  │ │Anthropic│ │   │
│  │  │ Adapter │ │Adapter │ │Adapter  │ │   │
│  │  └────┬────┘ └───┬────┘ └────┬────┘ │   │
│  └───────┴──────────┴───────────┘       │   │
│  ┌──────────────────────────────────────┐   │
│  │         Core Services                 │   │
│  │  Config │ Memory │ Validation         │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────┐
│           Ollama (localhost:11434)            │
│           Models: llama3:8b, etc.            │
└─────────────────────────────────────────────┘
```

## Module Structure

### Backend Modules

| Module | Purpose | Phase |
|--------|---------|-------|
| `core` | Config, validation, memory monitoring | 0 |
| `api` | HTTP route handlers | 0+ |
| `llm` | Provider adapters and router | 1 |
| `agents` | Multi-agent orchestration | 2 |
| `memory` | Knowledge store and retrieval | 2 |
| `coding` | Code generation and analysis | 3 |
| `automation` | Task automation and scheduling | 4 |
| `monitoring` | System and model metrics | 0+ |

### Data Flow

```
User Request → API Route → LLM Router → Provider Adapter → Model → Response
                                ↑
                        Memory Monitor (gate)
                        Config (settings)
                        Semaphore (concurrency)
```

## Memory Management

### Constraints
- **Total**: 28GB unified memory (shared CPU/GPU/Neural Engine)
- **Max heavy models**: 1 at a time
- **Warning threshold**: 65% usage
- **Critical threshold**: 75% usage (blocks heavy model load)
- **Auto-unload**: After 5 minutes of inactivity (configurable)

### Model Size Budget
| Model Size | Estimated RAM | Loadable |
|-----------|---------------|----------|
| 7B | ~4GB | ✅ |
| 8B | ~5GB | ✅ |
| 13B | ~8GB | ✅ (with care) |
| 32B | ~20GB | ⚠️ (tight) |
| 70B | ~40GB | ❌ (exceeds 28GB) |

## Concurrency Model

- **Max 2 concurrent agent tasks** (semaphore-controlled)
- **Non-blocking streaming** via SSE
- **Backpressure** on all queues
- **No uncontrolled threads**
- **uvloop** for high-performance async event loop

## Security Model

- Localhost-only binding (127.0.0.1)
- No personal data in codebase
- All secrets via environment variables
- Remote model access disabled by default
- CORS restricted to localhost origins
- No authentication needed (single-user, local)
