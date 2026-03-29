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
  FleetDeviceList,
  FleetHealth,
  FleetLocalInfo,
  FleetStatus,
  HealthResponse,
  LLMConfig,
  LLMConfigUpdate,
  MemoryStats,
  ModelInfo,
  N8nConfig,
  N8nExecution,
  N8nStatus,
  N8nWorkflow,
  Personality,
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

// ── n8n Integration ──────────────────────────────────────────────────────────

export const fetchN8nStatus = () => get<N8nStatus>("/api/automation/n8n/status");
export const fetchN8nWorkflows = () => get<N8nWorkflow[]>("/api/automation/n8n/workflows");
export const fetchN8nExecutions = (limit = 20) =>
  get<N8nExecution[]>(`/api/automation/n8n/executions?limit=${limit}`);

export async function activateN8nWorkflow(id: string): Promise<{ status: string }> {
  const res = await fetch(`${BASE}/api/automation/n8n/workflows/${id}/activate`, { method: "POST" });
  if (!res.ok) throw new Error(`Activate n8n workflow: ${res.status}`);
  return res.json();
}

export async function deactivateN8nWorkflow(id: string): Promise<{ status: string }> {
  const res = await fetch(`${BASE}/api/automation/n8n/workflows/${id}/deactivate`, { method: "POST" });
  if (!res.ok) throw new Error(`Deactivate n8n workflow: ${res.status}`);
  return res.json();
}

export async function executeN8nWorkflow(id: string, data?: Record<string, unknown>): Promise<{ execution_id: string }> {
  const res = await fetch(`${BASE}/api/automation/n8n/workflows/${id}/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data ?? {}),
  });
  if (!res.ok) throw new Error(`Execute n8n workflow: ${res.status}`);
  return res.json();
}

export async function updateN8nConfig(config: {
  n8n_url?: string;
  n8n_api_key?: string;
  n8n_enabled?: boolean;
}): Promise<N8nConfig> {
  const res = await fetch(`${BASE}/api/automation/n8n/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error(`Update n8n config: ${res.status}`);
  return res.json();
}

// ── Personalities ─────────────────────────────────────────────────────────────

export const fetchPersonalities = () => get<Personality[]>("/api/personalities/");

// ── Knowledge Base ────────────────────────────────────────────────────────────

export async function learnTopic(
  topic: string,
  options?: { max_results?: number; include_news?: boolean; tags?: string[] }
): Promise<{ id: string; topic: string; sources_found: number; summary: string; tags: string[] }> {
  const res = await fetch(`${BASE}/api/knowledge/learn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, ...options }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Learn topic error: ${res.status} ${detail}`);
  }
  return res.json();
}

export async function fetchKnowledgeTopics(): Promise<{
  total_topics: number;
  total_sources: number;
  topics: Array<{ id: string; topic: string; sources: number; tags: string[]; learned_at: number; summary: string }>;
}> {
  return get("/api/knowledge/topics");
}

export async function deleteKnowledgeTopic(topicId: string): Promise<void> {
  const res = await fetch(`${BASE}/api/knowledge/topics/${topicId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Delete topic: ${res.status}`);
}

// ── Fleet ─────────────────────────────────────────────────────────────────────

export const fetchFleetStatus = () => get<FleetStatus>("/api/fleet/status");
export const fetchFleetDevices = () => get<FleetDeviceList>("/api/fleet/devices");
export const fetchFleetHealth = () => get<FleetHealth>("/api/fleet/health");
export const fetchFleetLocalInfo = () => get<FleetLocalInfo>("/api/fleet/local/info");

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
