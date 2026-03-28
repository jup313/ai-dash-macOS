# Phase 4: Automation — Workflow Engine & Scheduler

## Overview

Phase 4 adds a workflow automation system that chains together LLM calls, agent tasks, code operations, and delays into composable, repeatable workflows with scheduling support.

## Architecture

```
automation/
├── models.py      — Data models (steps, workflows, runs, schedules)
├── engine.py      — Workflow engine (CRUD, sequential execution, conditions)
└── scheduler.py   — Interval-based recurring execution

api/
└── automation.py  — REST endpoints (/api/automation/*)
```

## Components

### Automation Models (`automation/models.py`)

**Enums:**
- `StepType` — 6 step types: `llm_chat`, `agent_task`, `code_generate`, `code_execute`, `code_analyze`, `delay`
- `TriggerType` — `manual`, `schedule`
- `RunStatus` — `pending`, `running`, `completed`, `failed`, `cancelled`, `skipped`
- `ErrorAction` — `stop`, `continue`, `skip`

**Core Models:**
- `WorkflowStep` — Single step with type, config, condition, error action, timeout
- `ScheduleConfig` — Interval-based schedule (60s–86400s, optional max_runs)
- `WorkflowDefinition` — Complete workflow with ordered steps, trigger type, enabled flag
- `WorkflowCreate` / `WorkflowUpdate` — API request models
- `StepResult` — Per-step execution result with status, output, timing
- `WorkflowRun` — Full execution record with all step results
- `WorkflowInfo` — Summary for listing
- `ScheduleEntry` / `SchedulerStatus` — Scheduler reporting

### Workflow Engine (`automation/engine.py`)

**Step Executors:**
Each `StepType` maps to an async executor function:

| Step Type | Executor | Integration |
|-----------|----------|-------------|
| `llm_chat` | `_exec_llm_chat` | LLM Router (`router.chat()`) |
| `agent_task` | `_exec_agent_task` | Agent Executor (`executor.submit()`) |
| `code_generate` | `_exec_code_generate` | Code Generator (`generate_code()`) |
| `code_execute` | `_exec_code_execute` | Code Executor (`execute_code()`) |
| `code_analyze` | `_exec_code_analyze` | Code Analyzer (`analyze_code()`) |
| `delay` | `_exec_delay` | `asyncio.sleep()` (capped at 60s) |

**Condition Evaluator:**
- Steps can have conditions referencing previous steps
- Format: `<step_name>.success` or `<step_name>.failed`
- Unmet conditions → step is `SKIPPED`

**Error Handling:**
- `ErrorAction.STOP` — Halt workflow on failure (default)
- `ErrorAction.CONTINUE` — Log failure, keep going
- `ErrorAction.SKIP` — Skip to next step

**WorkflowEngine Class:**
- In-memory workflow store (CRUD)
- Sequential step execution with `asyncio.wait_for` timeout
- Run history tracking per workflow
- Singleton with `get_engine()` / `reset_engine()`

### Scheduler (`automation/scheduler.py`)

- `WorkflowScheduler` — Manages `asyncio.Task` background loops
- One schedule per workflow (replaces on re-schedule)
- Respects `max_runs` limit
- `shutdown()` cancels all active tasks (called during app lifespan)
- Singleton with `get_scheduler()` / `reset_scheduler()`

## API Endpoints

### Workflow CRUD

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/automation/workflows` | Create workflow |
| `GET` | `/api/automation/workflows` | List all workflows |
| `GET` | `/api/automation/workflows/{id}` | Get workflow by ID |
| `PATCH` | `/api/automation/workflows/{id}` | Update workflow |
| `DELETE` | `/api/automation/workflows/{id}` | Delete workflow + runs |

### Execution

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/automation/workflows/{id}/run` | Execute workflow now |
| `GET` | `/api/automation/runs/{run_id}` | Get run details |
| `GET` | `/api/automation/workflows/{id}/runs` | List workflow runs |

### Scheduling

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/automation/workflows/{id}/schedule` | Start schedule |
| `DELETE` | `/api/automation/workflows/{id}/schedule` | Stop schedule |
| `GET` | `/api/automation/scheduler/status` | Scheduler status |

## Example: Create and Run a Workflow

```json
POST /api/automation/workflows
{
  "name": "analyze-and-report",
  "steps": [
    {
      "name": "analyze",
      "step_type": "code_analyze",
      "config": {
        "code": "def add(a, b):\n    return a + b\n",
        "language": "python"
      }
    },
    {
      "name": "summarize",
      "step_type": "llm_chat",
      "config": {
        "prompt": "Summarize the analysis results",
        "system_prompt": "You are a code review assistant"
      },
      "condition": "analyze.success"
    }
  ]
}
```

```json
POST /api/automation/workflows/{workflow_id}/run
→ Returns WorkflowRun with per-step results
```

## Example: Schedule a Workflow

```json
POST /api/automation/workflows/{workflow_id}/schedule
{
  "interval_seconds": 3600,
  "max_runs": 10
}
```

## Integration with main.py

- `automation_router` registered at app startup
- Scheduler `shutdown()` called during lifespan teardown
- Engine and scheduler singletons reset on shutdown

## Tests

**84 new tests (379 total):**

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_automation_models.py` | 26 | Enums, models, validation, bounds |
| `test_engine.py` | 30 | CRUD, execution, conditions, errors, timeouts, singleton |
| `test_scheduler.py` | 11 | Schedule/unschedule, status, replace, shutdown, singleton |
| `test_automation_api.py` | 17 | All API endpoints, CRUD, run, schedule |

## Step Config Reference

### `llm_chat`
```json
{"prompt": "...", "system_prompt": "...", "model": null, "provider": null}
```

### `agent_task`
```json
{"agent_name": "chat", "input_text": "..."}
```

### `code_generate`
```json
{"action": "generate", "prompt": "...", "code": "", "language": "python"}
```

### `code_execute`
```json
{"code": "print('hello')", "language": "python", "timeout_seconds": 30}
```

### `code_analyze`
```json
{"code": "x = 1", "language": "python"}
```

### `delay`
```json
{"seconds": 5}
```
