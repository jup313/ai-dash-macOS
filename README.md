# ai-dash-macOS

**Universal LLM Control Center for macOS Apple Silicon**

A production-grade, local-first AI dashboard supporting Ollama, OpenAI-compatible APIs, and optional Anthropic integration — built exclusively for macOS ARM64.

---

## Features

- 🧠 **Universal LLM Router** — Ollama (local default), OpenAI-compatible, Anthropic (optional)
- 🍎 **Apple Silicon Native** — ARM64 only, no Rosetta, optimized for unified memory
- 🔒 **Secure by Default** — Local-first, no cloud required, no personal data
- 📊 **28GB Memory Aware** — Intelligent model loading, auto-unload, memory metrics
- ⚡ **Async-First** — uvloop, orjson, non-blocking streaming
- 🤖 **Agent System** — Multi-agent orchestration with concurrency limits
- 💻 **Coding Engine** — AI-powered code generation and analysis
- 🔄 **Automation** — Task automation with scheduling
- 📈 **Monitoring** — Real-time system and model metrics

## Requirements

- macOS (Apple Silicon / ARM64)
- Python 3.11+
- Node 18+ (ARM64)
- Ollama installed and running at `http://localhost:11434`
- 28GB unified memory (recommended)

## Quick Start

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/ai-dash-macOS.git
cd ai-dash-macOS

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env

# Validate environment
bash scripts/validate_environment.sh

# Run backend
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

# Health check
curl http://localhost:8000/health
```

## Project Structure

```
ai-dash-macOS/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/       # Route handlers
│   │   ├── core/      # Config, validation, memory
│   │   ├── llm/       # LLM providers and router
│   │   ├── agents/    # Agent system
│   │   ├── coding/    # Coding engine
│   │   ├── memory/    # Memory/knowledge store
│   │   ├── automation/# Automation engine
│   │   └── monitoring/# System monitoring
│   └── tests/         # Test suite
├── frontend/          # Dashboard UI
├── docker/            # Docker configs (ARM64)
├── docs/              # Documentation
└── scripts/           # Utility scripts
```

## Environment Variables

All configuration via environment variables. See `.env.example` for the complete list.

## Testing

```bash
pytest backend/tests/ -v
```

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed system architecture.

## Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Local Validation | ✅ |
| 1 | LLM Router Core | ⬜ |
| 2 | Agents + Memory | ⬜ |
| 3 | Coding Engine | ⬜ |
| 4 | Automation | ⬜ |
| 5 | Unified Dashboard | ⬜ |

## License

[MIT](LICENSE)
