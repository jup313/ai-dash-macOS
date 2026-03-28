# Environment Setup Guide

## Prerequisites

### Required
- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.11+ (ARM64 native)
- Ollama installed and running

### Optional
- Node.js 18+ (ARM64, for Phase 5 frontend)
- Docker Desktop for Mac (ARM64)

## Installation

### 1. Install Ollama

```bash
# Download from https://ollama.ai
# Or via Homebrew:
brew install ollama

# Start Ollama
ollama serve

# Pull a default model
ollama pull llama3:8b
```

### 2. Install Python 3.11+

```bash
# Via Homebrew
brew install python@3.11

# Verify
python3 --version  # Should be 3.11+
python3 -c "import platform; print(platform.machine())"  # Should be arm64
```

### 3. Clone and Setup

```bash
git clone https://github.com/YOUR_USERNAME/ai-dash-macOS.git
cd ai-dash-macOS

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
```

### 4. Configure Environment

Edit `.env` as needed. Key settings:

```bash
# Default: local Ollama only
LLM_PROVIDER=ollama
ALLOW_REMOTE_MODELS=false
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3:8b
```

### 5. Validate

```bash
bash scripts/validate_environment.sh
```

### 6. Run

```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

### 7. Verify

```bash
curl http://localhost:8000/health | python3 -m json.tool
```

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | Provider: ollama, openai, anthropic |
| `ALLOW_REMOTE_MODELS` | `false` | Enable cloud model access |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `llama3:8b` | Default Ollama model |
| `LLM_BASE_URL` | _(empty)_ | OpenAI-compatible API URL |
| `LLM_API_KEY` | _(empty)_ | OpenAI-compatible API key |
| `LLM_MODEL` | _(empty)_ | OpenAI-compatible model |
| `ANTHROPIC_API_KEY` | _(empty)_ | Anthropic API key |
| `MAX_HEAVY_MODELS` | `1` | Max heavy models loaded |
| `MAX_AGENT_CONCURRENCY` | `2` | Max concurrent agent tasks |
| `AUTO_UNLOAD_MINUTES` | `5` | Auto-unload timeout |
| `REQUEST_TIMEOUT_SECONDS` | `60` | Request timeout |
| `MAX_REQUEST_TOKENS` | `8192` | Max tokens per request |
| `HOST` | `127.0.0.1` | Server bind host |
| `PORT` | `8000` | Server bind port |
| `LOG_LEVEL` | `info` | Logging level |

## Troubleshooting

### Ollama not reachable
```bash
# Start Ollama
ollama serve

# Check if running
curl http://localhost:11434/api/tags
```

### Wrong architecture
```bash
# Verify ARM64
uname -m  # Should be arm64

# Check Python
python3 -c "import platform; print(platform.machine())"  # arm64

# Check Node (if installed)
node -p "process.arch"  # arm64
```

### Memory issues
```bash
bash scripts/check_memory.sh
```

### Permission denied on scripts
```bash
chmod +x scripts/*.sh
```
