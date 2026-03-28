/* ai-dash-macOS — shared TypeScript types matching backend models */

// ── Health ────────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  platform: string;
  architecture: string;
  python_version: string;
  provider: string;
  memory: MemoryInfo;
}

export interface MemoryInfo {
  total_gb: number;
  used_gb: number;
  available_gb: number;
  percent_used: number;
  status: string;
}

// ── LLM ───────────────────────────────────────────────────────────────────────

export interface ModelInfo {
  name: string;
  provider: string;
  size?: string;
  modified_at?: string;
}

export interface ProviderStatus {
  name: string;
  available: boolean;
  models: ModelInfo[];
  error?: string;
}

export interface RouterStatus {
  default_provider: string;
  providers: ProviderStatus[];
  memory_status: string;
}

// ── Agents ────────────────────────────────────────────────────────────────────

export interface AgentInfo {
  name: string;
  agent_type: string;
  description: string;
  system_prompt: string;
  model?: string;
  provider?: string;
}

export interface ExecutorStatus {
  active_tasks: number;
  max_concurrency: number;
  registered_agents: number;
  total_completed: number;
  total_failed: number;
}

// ── Conversations ─────────────────────────────────────────────────────────────

export interface ConversationSummary {
  conversation_id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

// ── Automation ────────────────────────────────────────────────────────────────

export interface WorkflowInfo {
  workflow_id: string;
  name: string;
  description: string;
  step_count: number;
  trigger_type: string;
  enabled: boolean;
  total_runs: number;
}

export interface SchedulerStatus {
  active_schedules: number;
  total_scheduled_runs: number;
  schedules: ScheduleEntry[];
}

export interface ScheduleEntry {
  workflow_id: string;
  workflow_name: string;
  interval_seconds: number;
  total_runs: number;
  is_active: boolean;
}

// ── Coding ────────────────────────────────────────────────────────────────────

export interface FileInfo {
  path: string;
  name: string;
  extension: string;
  size_bytes: number;
  is_directory: boolean;
  language: string;
}

// ── Memory Stats ──────────────────────────────────────────────────────────────

export interface MemoryStats {
  total_conversations: number;
  total_messages: number;
  max_conversations: number;
}
