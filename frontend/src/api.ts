/* ai-dash-macOS — API client for the FastAPI backend */

import type {
  AgentInfo,
  ChatMessageRequest,
  ChatMessageResponse,
  ConversationDetail,
  ConversationMessage,
  ConversationSummary,
  ExecutorStatus,
  FileInfo,
  HealthResponse,
  LLMConfig,
  LLMConfigUpdate,
  MemoryStats,
  ModelInfo,
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
export const fetchLLMConfig = () => get<LLMConfig>("/api/llm/config");
export const fetchModels = (provider?: string) =>
  get<ModelInfo[]>(provider ? `/api/llm/models?provider=${provider}` : "/api/llm/models");

export async function updateLLMConfig(update: LLMConfigUpdate): Promise<LLMConfig> {
  const res = await fetch(`${BASE}/api/llm/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(update),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`PUT /api/llm/config: ${res.status} ${detail}`);
  }
  return res.json() as Promise<LLMConfig>;
}

// ── Agents ────────────────────────────────────────────────────────────────────

export const fetchAgents = () => get<AgentInfo[]>("/api/agents/list");
export const fetchExecutorStatus = () => get<ExecutorStatus>("/api/agents/status");

// ── Conversations ─────────────────────────────────────────────────────────────

export const fetchConversations = () => get<ConversationSummary[]>("/api/conversations/");
export const fetchMemoryStats = () => get<MemoryStats>("/api/conversations/stats");
export const fetchConversation = (id: string) => get<ConversationDetail>(`/api/conversations/${id}`);
export const fetchMessages = (id: string, limit?: number) =>
  get<ConversationMessage[]>(`/api/conversations/${id}/messages${limit ? `?limit=${limit}` : ""}`);

export async function createConversation(title: string, agent_name = "chat"): Promise<ConversationDetail> {
  const res = await fetch(`${BASE}/api/conversations/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, agent_name }),
  });
  if (!res.ok) throw new Error(`Create conversation: ${res.status}`);
  return res.json() as Promise<ConversationDetail>;
}

export async function deleteConversation(id: string): Promise<void> {
  const res = await fetch(`${BASE}/api/conversations/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Delete conversation: ${res.status}`);
}

export async function sendChatMessage(
  conversationId: string,
  request: ChatMessageRequest,
): Promise<ChatMessageResponse> {
  const res = await fetch(`${BASE}/api/conversations/${conversationId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Chat error: ${res.status} ${detail}`);
  }
  return res.json() as Promise<ChatMessageResponse>;
}

export function streamChatMessage(
  conversationId: string,
  request: ChatMessageRequest,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: Error) => void,
): AbortController {
  const controller = new AbortController();
  const body = JSON.stringify({ ...request, stream: true });

  fetch(`${BASE}/api/conversations/${conversationId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(`Stream error: ${res.status} ${detail}`);
      }
      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6).trim();
            if (data === "[DONE]") {
              onDone();
              return;
            }
            try {
              const parsed = JSON.parse(data);
              if (parsed.content) onChunk(parsed.content);
              if (parsed.done) { onDone(); return; }
            } catch { /* skip parse errors */ }
          }
        }
      }
      onDone();
    })
    .catch((err) => {
      if (err.name !== "AbortError") onError(err);
    });

  return controller;
}

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
