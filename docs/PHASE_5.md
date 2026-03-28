# Phase 5 — Unified Dashboard

## Overview

Phase 5 delivers a **React 19 + TypeScript + Vite + Tailwind CSS** single-page dashboard that
provides real-time visibility into every subsystem built in Phases 0–4. The frontend polls the
FastAPI backend and renders system health, LLM router status, agent metrics, coding engine files,
and automation workflows in a dark-themed, responsive UI designed for macOS Apple Silicon.

## Stack

| Layer       | Technology                       |
|-------------|----------------------------------|
| Framework   | React 19 with react-router-dom 7 |
| Language    | TypeScript 5.7 (strict mode)     |
| Build       | Vite 6                           |
| Styling     | Tailwind CSS 3.4 (custom theme)  |
| Dev proxy   | Vite → localhost:8000            |

## Architecture

```
frontend/
├── index.html                  # Entry HTML
├── package.json                # Dependencies & scripts
├── tsconfig.json               # Strict TS config with @/* alias
├── vite.config.ts              # Port 3000, proxy to backend :8000
├── tailwind.config.js          # Custom "dash" dark palette
├── postcss.config.js           # Tailwind + Autoprefixer
└── src/
    ├── main.tsx                # React root with BrowserRouter
    ├── index.css               # Tailwind directives + custom scrollbar
    ├── App.tsx                 # Route definitions with Layout wrapper
    ├── types.ts                # TS interfaces matching backend models
    ├── api.ts                  # Typed fetch client for all endpoints
    ├── hooks/
    │   └── usePoll.ts          # Generic polling hook (interval + refresh)
    ├── components/
    │   ├── Layout.tsx          # Sidebar navigation + Outlet
    │   └── Card.tsx            # Card, Stat, Badge reusable components
    └── pages/
        ├── OverviewPage.tsx    # Dashboard overview — all subsystems
        ├── LLMPage.tsx         # LLM router, providers, model list
        ├── AgentsPage.tsx      # Agent registry, executor, conversations
        ├── CodingPage.tsx      # File browser, languages, capabilities
        └── AutomationPage.tsx  # Workflows, scheduler, step types
```

## Pages

### Overview (`/`)
- System health with memory usage bar and status badge
- LLM provider summary with online count and memory gate
- Agent executor stats (registered, completed, failed)
- Automation summary (workflows, schedules)
- Platform info (arch, Python version, total memory)
- Provider detail cards with availability indicators

### LLM (`/llm`)
- Default provider display
- Memory gate status with explanatory text
- Online provider count
- Per-provider detail cards with model tables (name, size, modified)

### Agents (`/agents`)
- Executor status grid (registered, active, completed, failed, conversations)
- Clickable agent list with type badges
- Agent detail panel (type, description, model, provider, system prompt)
- Conversation table (title, message count, updated)
- Memory store stats (conversations, messages, capacity)

### Coding (`/coding`)
- File/directory/language/size stat cards
- Language detection badges
- Workspace file browser table with icons
- Capabilities info (Analyze, Generate, Execute)

### Automation (`/automation`)
- Workflow/enabled/runs/schedule stat cards
- Workflow table (name, steps, trigger, runs, status)
- Scheduler detail table (interval, runs, active status)
- Step type badges and feature list

## Design System

Custom Tailwind theme (`dash-*` tokens):

| Token           | Value     | Usage              |
|----------------|-----------|--------------------|
| `dash-bg`      | `#0f1117` | Page background    |
| `dash-surface` | `#1a1d27` | Cards, sidebar     |
| `dash-border`  | `#2a2d3a` | Borders, dividers  |
| `dash-accent`  | `#6366f1` | Active/accent      |
| `dash-success` | `#22c55e` | Normal/online      |
| `dash-warning` | `#f59e0b` | Warning states     |
| `dash-error`   | `#ef4444` | Errors/offline     |
| `dash-text`    | `#e2e8f0` | Primary text       |
| `dash-text-dim`| `#94a3b8` | Secondary text     |
| `dash-muted`   | `#64748b` | Tertiary text      |

## API Client

All API calls use typed fetch functions with proper error handling:

- `fetchHealth()` → `GET /health`
- `fetchRouterStatus()` → `GET /api/llm/status`
- `fetchAgents()` → `GET /api/agents/list`
- `fetchExecutorStatus()` → `GET /api/agents/status`
- `fetchConversations()` → `GET /api/conversations/`
- `fetchMemoryStats()` → `GET /api/conversations/stats`
- `fetchWorkflows()` → `GET /api/automation/workflows`
- `fetchSchedulerStatus()` → `GET /api/automation/scheduler/status`
- `fetchFiles()` → `GET /api/coding/files`
- `fetchAll()` → Parallel `Promise.allSettled` for overview page

## Polling

The `usePoll<T>` hook provides:
- Automatic interval-based refresh (configurable, default 5s)
- Manual `refresh()` trigger
- Loading, error, and data state management
- Graceful error handling (stale data preserved on transient failures)

## Development

```bash
# Install dependencies
cd frontend && npm install

# Dev server (port 3000, proxies to backend at :8000)
npm run dev

# Production build
npm run build

# Preview production build
npm run preview
```

## Production Build

```
dist/index.html                   0.43 kB │ gzip:  0.29 kB
dist/assets/index-*.css          11.77 kB │ gzip:  3.10 kB
dist/assets/index-*.js          256.03 kB │ gzip: 78.97 kB
```

Total gzipped: **~82 KB** — lightweight enough for local-first deployment.

## Test Coverage

Phase 5 is a frontend-only phase. Verification:
- ✅ TypeScript strict mode — zero errors (`tsc -b`)
- ✅ Vite production build — zero warnings
- ✅ All backend tests still passing (379 tests)

## What's Next

The dashboard is read-only in v0.1.0. Future enhancements:
- Interactive chat interface (SSE streaming)
- Agent execution from UI
- Code editor with syntax highlighting
- Workflow builder (drag-and-drop)
- Real-time WebSocket updates
- Dark/light theme toggle
