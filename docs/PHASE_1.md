# Phase 1 — LLM Router Core

## Overview

Phase 1 implements the Universal LLM Router — the central hub that dispatches
chat requests to provider adapters (Ollama, OpenAI-compatible, Anthropic).

## Architecture

```
                    ┌─────────────────┐
                    │   API Endpoints  │
                    │  /api/llm/chat   │
                    │  /api/llm/models │
                    │  /api/llm/status │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   LLM Router    │
                    │  Memory Gating  │
                    │ Provider Select │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼──────┐ ┌────▼─────┐ ┌─────▼───────┐
     │ OllamaAdapter │ │ OpenAI   │ │  Anthropic  │
     │ localhost:11434│ │ Compat   │ │  (optional) │
     └───────────────┘ └──────────┘ └─────────────┘
```

## Components

### Data Models (`backend/app/llm/models.py`)
- `Message` — Chat message with role (system/user/assistant)
- `ChatRequest` — Universal request with provider/model override, temperature, max_tokens, streaming
- `ChatResponse` — Universal response with content, usage, finish_reason
- `StreamChunk` — Single chunk in streaming response
- `ModelInfo` — Model metadata (name, size, parameters, quantization)
- `TokenUsage` — Token consumption stats
- `ProviderStatus` / `RouterStatus` — Health reporting

### Base Adapter (`backend/app/llm/base.py`)
- `BaseLLMAdapter` — Abstract interface all providers implement
- `ProviderError` / `ProviderUnavailableError` — Typed errors

### Ollama Adapter (`backend/app/llm/ollama.py`)
- Default local provider at `localhost:11434`
- Chat via `/api/chat`, models via `/api/tags`
- Streaming via NDJSON line parsing
- Maps Ollama-specific fields (prompt_eval_count → prompt_tokens)

### OpenAI Adapter (`backend/app/llm/openai_adapter.py`)
- Works with any OpenAI-compatible API (OpenAI, LM Studio, vLLM, LocalAI)
- Chat via `/v1/chat/completions`, models via `/v1/models`
- SSE streaming with `data: ` prefix parsing
- Bearer token auth

### Anthropic Adapter (`backend/app/llm/anthropic_adapter.py`)
- Optional Claude integration (requires ALLOW_REMOTE_MODELS=true + API key)
- Anthropic Messages API with system prompt separation
- SSE streaming with event type parsing
- Static model list (no list endpoint)

### Router (`backend/app/llm/router.py`)
- Central dispatch: routes to correct adapter by provider name
- Memory gating: blocks requests when RAM > 75%
- Auto-initializes configured providers on first request
- Singleton pattern with `get_router()` / `reset_router()`

### Streaming (`backend/app/llm/streaming.py`)
- `stream_to_sse()` — Converts StreamChunk iterator to SSE strings
- `collect_stream()` — Collects stream into single string (testing)

### API Endpoints (`backend/app/api/llm.py`)
- `POST /api/llm/chat` — Chat completion
- `POST /api/llm/chat/stream` — Streaming chat (SSE)
- `GET /api/llm/models` — List models (optional provider filter)
- `GET /api/llm/status` — Router status
- `GET /api/llm/providers` — Provider availability

## Test Coverage

| File | Tests | Coverage |
|------|-------|----------|
| `test_models.py` | 20 | Data model validation, serialization |
| `test_adapters.py` | 32 | All 3 adapters: chat, errors, availability |
| `test_router.py` | 12 | Init, selection, memory gating, listing |
| `test_streaming.py` | 6 | SSE format, collection, empty streams |
| `test_llm_api.py` | 8 | All API endpoints, error codes |
| **Phase 1 Total** | **87** | |
| **Cumulative** | **130** | Phase 0 (43) + Phase 1 (87) |

## Run Instructions

```bash
cd /Users/edlaracuente/Desktop/utuado-ai
source venv/bin/activate

# Run all tests
python -m pytest -v

# Run Phase 1 tests only
python -m pytest backend/tests/test_models.py backend/tests/test_adapters.py \
  backend/tests/test_router.py backend/tests/test_streaming.py \
  backend/tests/test_llm_api.py -v

# Start server
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

# Test endpoints (requires Ollama running)
curl http://localhost:8000/api/llm/status | python -m json.tool
curl http://localhost:8000/api/llm/providers | python -m json.tool
curl http://localhost:8000/api/llm/models | python -m json.tool

# Chat (requires Ollama with model loaded)
curl -X POST http://localhost:8000/api/llm/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello!"}]}'
```

## Memory Impact

- **Router idle:** ~2MB additional (adapter instances, no models loaded)
- **Per chat request:** Depends on model + context size
- **Memory gating:** Requests blocked when system RAM > 75%
- **No models loaded by router** — Ollama manages model lifecycle

## Configuration

All via environment variables (`.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | Default provider |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `llama3:8b` | Default Ollama model |
| `LLM_BASE_URL` | *(empty)* | OpenAI-compatible URL |
| `LLM_API_KEY` | *(empty)* | OpenAI-compatible key |
| `LLM_MODEL` | *(empty)* | OpenAI-compatible model |
| `ANTHROPIC_API_KEY` | *(empty)* | Anthropic API key |
| `ALLOW_REMOTE_MODELS` | `false` | Enable cloud providers |
| `REQUEST_TIMEOUT_SECONDS` | `60` | Request timeout |
| `MAX_REQUEST_TOKENS` | `8192` | Max tokens per request |
