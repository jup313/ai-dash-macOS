# Phase 3 — Coding Engine

## Overview

Phase 3 adds the **coding engine** to ai-dash-macOS — AI-powered code generation,
static analysis, sandboxed execution, and safe file management within a sandbox directory.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   FastAPI App                    │
├─────────────────────────────────────────────────┤
│              /api/coding                         │
│  ┌──────────┬──────────┬──────────┬───────────┐ │
│  │ generate │ analyze  │ execute  │   files   │ │
│  └────┬─────┴────┬─────┴────┬─────┴─────┬─────┘ │
│       │          │          │           │        │
│  Generator   Analyzer   Executor   FileManager  │
│  (LLM-based) (AST/heur) (subprocess)(sandboxed) │
├─────────────────────────────────────────────────┤
│  LLM Router (Phase 1) │ Agents (Phase 2)        │
│  Core: Config, Validation, Memory (Phase 0)     │
└─────────────────────────────────────────────────┘
```

## Components

### Coding Engine (`backend/app/coding/`)

| File | Purpose |
|------|---------|
| `models.py` | CodeLanguage, CodeAction, CodeRequest, CodeResult, AnalysisResult, ExecutionRequest/Result, FileInfo, FileRead/WriteResult |
| `analyzer.py` | Python AST analysis, generic heuristics, language detection, metrics, issue detection |
| `generator.py` | LLM-powered code generation/refactor/explain/fix/test/document with response parsing |
| `executor.py` | Sandboxed subprocess execution (Python, Bash) with timeout and resource limits |
| `file_manager.py` | Safe file ops within sandbox directory, path traversal protection, size limits |

### API Endpoints (`/api/coding`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/coding/generate` | Generate/refactor/explain/fix/test/document code via LLM |
| POST | `/api/coding/analyze` | Static code analysis (AST for Python, heuristics for others) |
| POST | `/api/coding/execute` | Execute code in sandboxed subprocess |
| GET | `/api/coding/files` | List files in sandbox directory |
| GET | `/api/coding/files/read` | Read a file from sandbox |
| POST | `/api/coding/files/write` | Write a file to sandbox |
| DELETE | `/api/coding/files` | Delete a file from sandbox |

## Supported Languages

| Language | Analysis | Execution | Detection |
|----------|----------|-----------|-----------|
| Python | AST + patterns | ✅ subprocess | .py |
| JavaScript | Heuristics | ❌ | .js, .jsx |
| TypeScript | Heuristics | ❌ | .ts, .tsx |
| Bash | Heuristics | ✅ subprocess | .sh, .bash |
| HTML | Heuristics | ❌ | .html, .htm |
| CSS | Heuristics | ❌ | .css |
| JSON | JSON parse | ❌ | .json |
| YAML | Heuristics | ❌ | .yaml, .yml |
| Markdown | Heuristics | ❌ | .md |
| SQL | Heuristics | ❌ | .sql |

## Code Actions

| Action | Description |
|--------|-------------|
| `generate` | Create new code from a description |
| `refactor` | Improve existing code structure |
| `explain` | Explain what code does |
| `fix` | Fix bugs in code |
| `test` | Generate tests for code |
| `document` | Add docstrings and comments |

## Python Analysis Features

- **Syntax validation** via `ast.parse()`
- **Metrics**: lines (total/code/comment/blank), functions, classes, imports, complexity score
- **Issue detection**: bare except, mutable defaults, global statements, TODO/FIXME comments
- **Suggestions**: missing comments, missing functions, high complexity

## Security

- **Sandbox isolation**: All file operations confined to `/tmp/ai-dash-sandbox`
- **Path traversal protection**: Resolved paths checked against sandbox root
- **File size limits**: 1 MB max per file
- **Execution timeout**: Configurable (default 30s, max 120s)
- **Subprocess isolation**: Code runs in separate process with no inherited state

## Key Design Decisions

1. **AST-based Python analysis**: Uses `ast.parse()` and `ast.walk()` for accurate metrics
   and pattern detection rather than regex-only approaches.

2. **Response parsing**: Generator extracts code blocks from LLM markdown output,
   separating code from explanation text.

3. **Temp file execution**: Code is written to a temp file and executed via subprocess
   rather than `exec()` for isolation.

4. **Singleton FileManager with reset**: Allows test isolation via `tmp_path` injection.

5. **Lower default temperature (0.3)**: Code generation uses lower temperature than
   chat (0.7) for more deterministic output.

## Tests

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_coding_models.py` | 20 | All data models, enums, validation |
| `test_analyzer.py` | 34 | Language detection, Python AST analysis, generic analysis |
| `test_file_manager.py` | 20 | CRUD, path traversal, sandbox isolation, singleton |
| `test_generator.py` | 12 | Message building, response parsing, LLM integration |
| `test_code_executor.py` | 10 | Python/Bash execution, timeout, unsupported languages |
| `test_coding_api.py` | 8 | All API endpoints via httpx |
| **Total Phase 3** | **104** | |
| **Cumulative** | **295** | Phases 0 + 1 + 2 + 3 |

## Running Tests

```bash
# Phase 3 tests only
python -m pytest backend/tests/test_coding_models.py backend/tests/test_analyzer.py \
  backend/tests/test_file_manager.py backend/tests/test_generator.py \
  backend/tests/test_code_executor.py backend/tests/test_coding_api.py -v

# Full suite
python -m pytest -v
```

## Status

✅ **Phase 3 Complete** — 295/295 tests passing
