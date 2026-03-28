# Phase 0 — Local Validation

## Overview

Phase 0 establishes the repository structure, validates the target environment (macOS ARM64), checks Ollama availability, verifies environment configuration, and confirms memory constraints.

## What Was Built

### Core Modules
- **`backend/app/core/config.py`** — Pydantic-based settings from environment variables
- **`backend/app/core/validation.py`** — ARM64, macOS, Python, Rosetta, Ollama checks
- **`backend/app/core/memory.py`** — 28GB-aware memory monitoring with model gating

### API
- **`backend/app/api/health.py`** — `/health` endpoint with full system status
- **`backend/app/main.py`** — FastAPI application entry point

### Tests
- **`backend/tests/test_validation.py`** — Architecture, platform, Ollama tests
- **`backend/tests/test_health.py`** — Health endpoint response validation
- **`backend/tests/test_memory.py`** — Memory metrics and threshold tests

### Scripts
- **`scripts/validate_environment.sh`** — Full environment validation
- **`scripts/check_arm64.sh`** — Quick ARM64 check
- **`scripts/check_ollama.sh`** — Ollama connectivity check
- **`scripts/check_memory.sh`** — Memory availability report

## How to Run

```bash
# Setup
cd utuado-ai
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Validate environment
bash scripts/validate_environment.sh

# Start server
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

# Health check
curl http://localhost:8000/health | python3 -m json.tool

# Run tests
pytest backend/tests/ -v
```

## Expected Health Response

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "platform": {
    "arch": "arm64",
    "os": "darwin",
    "python": "3.11.x",
    "rosetta": false
  },
  "memory": {
    "total_gb": 28.0,
    "available_gb": 18.5,
    "percent_used": 33.9,
    "status": "healthy",
    "heavy_model_allowed": true,
    "swap_used_gb": 0.0,
    "swap_total_gb": 4.0
  },
  "ollama": {
    "reachable": true,
    "url": "http://localhost:11434",
    "detail": "Ollama reachable at http://localhost:11434 (3 models available)"
  },
  "config": {
    "loaded": true,
    "provider": "ollama",
    "allow_remote": false,
    "max_heavy_models": 1,
    "max_agent_concurrency": 2
  }
}
```

## Memory Impact

- **Phase 0 backend RSS**: ~30-50MB
- **No models loaded**: Zero GPU/Neural Engine usage
- **psutil overhead**: Negligible (~1MB)
- **Total Phase 0 footprint**: <100MB

## Validation Checks

| Check | Description | Required |
|-------|-------------|----------|
| Architecture | ARM64 (Apple Silicon) | ✅ |
| Platform | macOS (darwin) | ✅ |
| Python | 3.11+ | ✅ |
| Rosetta | Not translated | ✅ |
| Memory | Available for operation | ✅ |
| Ollama | Reachable at configured URL | ⚠️ Warning only |
| Node.js | ARM64 native (Phase 5) | ℹ️ Info only |
| .env | Configuration file exists | ⚠️ Warning only |
