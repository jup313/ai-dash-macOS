# ai-dash-macOS

**Universal LLM Control Center for macOS Apple Silicon**

A production-grade, local-first AI dashboard supporting Ollama, OpenAI-compatible APIs, and optional Anthropic integration — built exclusively for macOS ARM64.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Platform](https://img.shields.io/badge/platform-macOS%20ARM64-brightgreen)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![React](https://img.shields.io/badge/react-19-61dafb)

---

## ✨ Features

### 🧠 Universal LLM Router
- **Multi-provider support** — Ollama (local default), OpenAI-compatible, Anthropic (optional)
- **Runtime switching** — Change providers and models on-the-fly from the dashboard
- **Adapter pattern** — Clean abstraction over provider APIs with unified interface
- **SSE Streaming** — Real-time token streaming with Server-Sent Events

### 💬 Local ChatGPT Replacement
- **Full chat interface** — Conversation sidebar, message bubbles, streaming text with cursor animation
- **Agent selector** — Choose between chat, summary, and analysis agents
- **Model selector** — Auto-detects available Ollama models with dropdown selection
- **Stream toggle** — Switch between streaming SSE and standard request/response
- **Conversation management** — Create, delete, and switch between conversations
- **Persistent memory** — In-memory conversation store with message history

### 🤖 Multi-Agent System
- **3 built-in agents** — Chat (general), Summary (text summarization), Analysis (deep analysis)
- **Agent orchestration** — Concurrent execution with configurable limits
- **Task executor** — Async task queue with completion/failure tracking
- **Custom agents** — Extensible registry for adding new agent types

### 💻 Coding Engine
- **AI code generation** — Generate code in any language via LLM
- **Code analysis** — Static analysis and AI-powered code review
- **Code execution** — Sandboxed code execution with output capture
- **File management** — Browse, read, and manage project files

### 🔄 Dual Automation System
- **Custom Workflow Engine** — 6 step types (llm_query, agent_task, code_execute, http_request, condition, transform), sequential execution with context passing, conditional branching
- **n8n Connector** — Full integration with n8n workflow automation:
  - Connection settings UI (URL, API key, enable/disable)
  - List, activate, deactivate, and execute n8n workflows
  - Webhook triggering
  - Execution history viewer
  - Runtime configuration without restart
- **Scheduler** — Interval-based recurring job execution with max runs

### 📊 Unified Dashboard
- **React 19 + TypeScript + Vite** — Modern, fast frontend
- **Tailwind CSS** — Ultra-modern dark theme UI
- **Real-time polling** — Auto-refreshing system metrics
- **Multi-page layout** — Overview, Chat, LLM, Agents, Coding, Automation pages
- **Responsive design** — Clean layout on all screen sizes

### 🍎 Apple Silicon Optimized
- **ARM64 native** — No Rosetta, optimized for unified memory architecture
- **Memory-aware** — Intelligent model gating based on available RAM (configurable threshold)
- **System monitoring** — Real-time CPU, memory, swap, and GPU metrics
- **Auto-detection** — Platform validation at startup

---

## 📋 Requirements

| Requirement | Version |
|-------------|---------|
| macOS | Apple Silicon (M1/M2/M3/M4) |
| Python | 3.11+ |
| Node.js | 18+ (ARM64) |
| Ollama | Latest ([install](https://ollama.ai)) |
| RAM | 16GB+ unified memory (28GB recommended) |

---

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/edlaracuente/ai-dash-macOS.git
cd ai-dash-macOS

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..

# Copy environment config
cp .env.example .env

# Make sure Ollama is running with a model
ollama pull llama3.1:latest
ollama serve  # if not already running

# Start backend (terminal 1)
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

# Start frontend (terminal 2)
cd frontend && npm run dev

# Open dashboard
open http://localhost:3000
```

### Health Check

```bash
curl http://localhost:8000/health | jq
```

---

## 🏗 Project Structure

```
ai-dash-macOS/
├── backend/
│   └── app/
│       ├── api/              # REST endpoints
│       │   ├── health.py     # Health check & system info
│       │   ├── llm.py        # LLM config, models, status
│       │   ├── agents.py     # Agent list, task execution
│       │   ├── conversations.py  # Chat, messages, streaming
│       │   ├── automation.py # Workflows, scheduler, n8n
│       │   └── coding.py     # File management, code ops
│       ├── core/             # Config, validation, memory monitor
│       │   ├── config.py     # Pydantic Settings (.env)
│       │   ├── validation.py # ARM64 & Ollama checks
│       │   └── memory.py     # Memory monitoring & gating
│       ├── llm/              # LLM provider system
│       │   ├── router.py     # Multi-provider router
│       │   ├── adapters/     # Ollama, OpenAI, Anthropic
│       │   └── streaming.py  # SSE streaming
│       ├── agents/           # Agent system
│       │   ├── registry.py   # Agent registration
│       │   ├── executor.py   # Async task executor
│       │   └── builtins.py   # Chat, Summary, Analysis agents
│       ├── automation/       # Automation system
│       │   ├── engine.py     # Custom workflow engine
│       │   ├── scheduler.py  # Interval-based scheduler
│       │   ├── n8n.py        # n8n connector service
│       │   └── models.py     # Workflow/step models
│       ├── coding/           # Coding engine
│       │   ├── generator.py  # AI code generation
│       │   ├── analyzer.py   # Code analysis
│       │   ├── executor.py   # Sandboxed execution
│       │   └── files.py      # File management
│       ├── memory/           # Memory & knowledge
│       │   └── store.py      # Conversation store
│       └── monitoring/       # System monitoring
│           └── system.py     # CPU, RAM, GPU metrics
├── frontend/
│   └── src/
│       ├── App.tsx           # Router & layout
│       ├── api.ts            # API client (all endpoints)
│       ├── types.ts          # TypeScript interfaces
│       ├── components/       # Reusable UI components
│       │   ├── Layout.tsx    # Sidebar navigation
│       │   └── Card.tsx      # Card, Stat, Badge components
│       ├── hooks/
│       │   └── usePoll.ts    # Auto-polling hook
│       └── pages/
│           ├── OverviewPage.tsx   # System dashboard
│           ├── ChatPage.tsx       # Chat interface
│           ├── LLMPage.tsx        # LLM management
│           ├── AgentsPage.tsx     # Agent management
│           ├── CodingPage.tsx     # Coding tools
│           └── AutomationPage.tsx # Workflows + n8n
├── docs/               # Phase documentation
├── scripts/            # Utility scripts
├── docker/             # Docker configs (ARM64)
├── .github/workflows/  # CI pipeline
├── .env.example        # Environment template
├── requirements.txt    # Python dependencies
└── package.json        # Root package.json
```

---

## 🔌 API Endpoints

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | System health, platform, memory, Ollama status |

### LLM
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/llm/status` | Router status, active provider, model counts |
| GET | `/api/llm/config` | Current LLM configuration |
| PUT | `/api/llm/config` | Update provider/model at runtime |
| GET | `/api/llm/models` | List all available models |

### Chat / Conversations
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/conversations/` | List all conversations |
| POST | `/api/conversations/` | Create new conversation |
| GET | `/api/conversations/{id}` | Get conversation with messages |
| DELETE | `/api/conversations/{id}` | Delete conversation |
| GET | `/api/conversations/{id}/messages` | Get message history |
| POST | `/api/conversations/{id}/chat` | Send message (supports SSE streaming) |
| GET | `/api/conversations/stats` | Memory usage statistics |

### Agents
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/agents/list` | List registered agents |
| GET | `/api/agents/status` | Executor status & metrics |

### Automation
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/automation/workflows` | List custom workflows |
| GET | `/api/automation/scheduler/status` | Scheduler status |

### n8n Integration
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/automation/n8n/status` | n8n connection status |
| GET | `/api/automation/n8n/workflows` | List n8n workflows |
| POST | `/api/automation/n8n/workflows/{id}/activate` | Activate workflow |
| POST | `/api/automation/n8n/workflows/{id}/deactivate` | Deactivate workflow |
| POST | `/api/automation/n8n/workflows/{id}/execute` | Execute workflow |
| POST | `/api/automation/n8n/webhook/{path}` | Trigger webhook |
| GET | `/api/automation/n8n/executions` | Execution history |
| PUT | `/api/automation/n8n/config` | Update n8n config at runtime |

### Coding
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/coding/files` | List project files |

---

## ⚙️ Environment Variables

All configuration is managed via `.env`. See [`.env.example`](.env.example) for the complete list.

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `llama3.1:latest` | Default Ollama model |
| `DEFAULT_PROVIDER` | `ollama` | Active LLM provider |
| `ALLOW_REMOTE_PROVIDERS` | `false` | Allow OpenAI/Anthropic |
| `OPENAI_API_KEY` | — | OpenAI API key (optional) |
| `ANTHROPIC_API_KEY` | — | Anthropic API key (optional) |
| `N8N_URL` | `http://localhost:5678` | n8n instance URL |
| `N8N_API_KEY` | — | n8n API key |
| `N8N_ENABLED` | `false` | Enable n8n integration |
| `MEMORY_THRESHOLD_PERCENT` | `90` | Memory gating threshold |
| `MAX_HEAVY_MODELS` | `2` | Concurrent model limit |
| `MAX_AGENT_CONCURRENCY` | `3` | Parallel agent limit |

---

## 🧪 Testing

```bash
# Run all tests
pytest backend/tests/ -v

# Run with coverage
pytest backend/tests/ --cov=backend/app -v
```

---

## 🐳 Docker (ARM64)

```bash
docker-compose up --build
```

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture & design decisions |
| [ENVIRONMENT.md](docs/ENVIRONMENT.md) | Environment setup guide |
| [PHASE_0.md](docs/PHASE_0.md) | Local Validation — ARM64, Ollama, health |
| [PHASE_1.md](docs/PHASE_1.md) | LLM Router Core — Adapters, streaming |
| [PHASE_2.md](docs/PHASE_2.md) | Agents + Memory — Registry, executor, store |
| [PHASE_3.md](docs/PHASE_3.md) | Coding Engine — Generator, analyzer, executor |
| [PHASE_4.md](docs/PHASE_4.md) | Automation — Workflows, scheduler |
| [PHASE_5.md](docs/PHASE_5.md) | Unified Dashboard — React UI |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines |

---

## 📦 Build Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Local Validation — ARM64, memory monitoring, Ollama check | ✅ |
| 1 | LLM Router Core — Provider adapters, SSE streaming, 130 tests | ✅ |
| 2 | Agents + Memory — Registry, executor, conversation store | ✅ |
| 3 | Coding Engine — Generator, analyzer, executor, file manager | ✅ |
| 4 | Automation — Workflow engine, scheduler, n8n connector | ✅ |
| 5 | Unified Dashboard — React 19, Chat UI, real-time monitoring | ✅ |

---

## 📸 Screenshots

### Dashboard Overview
System health, LLM status, agent metrics, and conversation stats at a glance.

### Chat Interface
Full ChatGPT-like experience with streaming responses, agent selection, and model switching.

### Automation
Dual automation system with custom workflow engine and n8n connector integration.

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Pydantic v2, uvicorn, httpx |
| Frontend | React 19, TypeScript, Vite 6, Tailwind CSS |
| LLM | Ollama (local), OpenAI API, Anthropic API |
| Automation | Custom engine + n8n integration |
| Database | In-memory (conversation store) |
| Streaming | Server-Sent Events (SSE) |
| Testing | pytest, 170+ tests |
| CI/CD | GitHub Actions |

---

## 📄 License

[MIT](LICENSE)

---

**Built with ❤️ for Apple Silicon by Ed Laracuente**
