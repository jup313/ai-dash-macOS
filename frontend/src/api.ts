/* ai-dash-macOS — API client for the FastAPI backend */

import type {
  AgentInfo,
  ConversationSummary,
  ExecutorStatus,
  FileInfo,
  HealthResponse,
  MemoryStats,
  RouterStatus,
  SchedulerStatus,
  WorkflowInfo,
} from "./types";

const BASE = "";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path}: ${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

// ── Health ────────────────────────────────────────────────────────────────────

export const fetchHealth = () => get<HealthResponse>("/health");

// ── LLM ───────────────────────────────────────────────────────────────────────

export const fetchRouterStatus = () => get<RouterStatus>("/api/llm/status");

// ── Agents ────────────────────────────────────────────────────────────────────

export const fetchAgents = () => get<AgentInfo[]>("/api/agents/list");
export const fetchExecutorStatus = () => get<ExecutorStatus>("/api/agents/status");

// ── Conversations ─────────────────────────────────────────────────────────────

export const fetchConversations = () => get<ConversationSummary[]>("/api/conversations/");
export const fetchMemoryStats = () => get<MemoryStats>("/api/conversations/stats");

// ── Automation ────────────────────────────────────────────────────────────────

export const fetchWorkflows = () => get<WorkflowInfo[]>("/api/automation/workflows");
export const fetchSchedulerStatus = () => get<SchedulerStatus>("/api/automation/scheduler/status");

// ── Coding ────────────────────────────────────────────────────────────────────

export const fetchFiles = () => get<FileInfo[]>("/api/coding/files");

// ── Polling hook helper ──────────────────────────────────────────────────────

export async function fetchAll() {
  const [health, router, agents, executor, workflows, scheduler] =
    await Promise.allSettled([
      fetchHealth(),
      fetchRouterStatus(),
      fetchAgents(),
      fetchExecutorStatus(),
      fetchWorkflows(),
      fetchSchedulerStatus(),
    ]);

  return {
    health: health.status === "fulfilled" ? health.value : null,
    router: router.status === "fulfilled" ? router.value : null,
    agents: agents.status === "fulfilled" ? agents.value : null,
    executor: executor.status === "fulfilled" ? executor.value : null,
    workflows: workflows.status === "fulfilled" ? workflows.value : null,
    scheduler: scheduler.status === "fulfilled" ? scheduler.value : null,
  };
}
