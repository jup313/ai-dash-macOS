/* ai-dash-macOS — shared TypeScript types matching backend models */

// ── Health ────────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  version: string;
  platform: PlatformInfo;
  memory: MemoryInfo;
  ollama: OllamaInfo;
  config: ConfigInfo;
}

export interface PlatformInfo {
  arch: string;
  os: string;
  python: string;
  rosetta: boolean;
}

export interface MemoryInfo {
  total_gb: number;
  used_gb: number;
  available_gb: number;
  percent_used: number;
  status: string;
  heavy_model_allowed: boolean;
  swap_used_gb: number;
  swap_total_gb: number;
}

export interface OllamaInfo {
  reachable: boolean;
  url: string;
  detail: string;
}

export interface ConfigInfo {
  loaded: boolean;
  provider: string;
  allow_remote: boolean;
  max_heavy_models: number;
  max_agent_concurrency: number;
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
  models_count: number;
  default_model: string;
  detail?: string;
}

export interface RouterStatus {
  active_provider: string;
  providers: ProviderStatus[];
  memory_ok: boolean;
  total_models: number;
}

export interface LLMConfigUpdate {
  provider?: string;
  model?: string;
}

export interface LLMConfig {
  active_provider: string;
  ollama_model: string;
  openai_model: string;
  available_providers: string[];
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
  modified_at?: string;
}

// ── n8n ───────────────────────────────────────────────────────────────────────

export interface N8nStatus {
  enabled: boolean;
  connected: boolean;
  url: string;
  workflow_count?: number;
  active_workflows?: number;
  detail: string;
}

export interface N8nWorkflow {
  id: string;
  name: string;
  active: boolean;
  tags: string[];
  nodes_count: number;
  created_at: string;
  updated_at: string;
}

export interface N8nExecution {
  id: string;
  workflow_id: string;
  workflow_name: string;
  status: string;
  started_at: string;
  finished_at: string;
  mode: string;
}

export interface N8nConfig {
  n8n_url: string;
  n8n_enabled: boolean;
  has_api_key: boolean;
}

// ── Memory Stats ──────────────────────────────────────────────────────────────

export interface MemoryStats {
  total_conversations: number;
  total_messages: number;
  total_tokens: number;
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export interface ChatMessageRequest {
  content: string;
  agent?: string;
  model?: string;
  provider?: string;
  stream?: boolean;
}

export interface ChatMessageResponse {
  content: string;
  model: string;
  provider: string;
  usage?: { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number };
  conversation_id: string;
}

export interface ConversationMessage {
  message_id: string;
  role: string;
  content: string;
  timestamp: string;
  tokens_used?: number;
}

export interface ConversationDetail {
  conversation_id: string;
  title: string;
  agent_name: string;
  messages: ConversationMessage[];
  created_at: string;
  updated_at: string;
}

// ── Fleet ─────────────────────────────────────────────────────────────────────

export interface FleetDevice {
  name: string;
  type: string;
  host: string;
  status: "online" | "offline" | "unconfigured";
  detail?: string;
}

export interface FleetStatus {
  status: string;
  summary: string;
  online: number;
  total: number;
  devices: FleetDevice[];
}

export interface FleetDeviceList {
  devices: Array<{
    name: string;
    type: string;
    host: string;
    configured: boolean;
  }>;
}

export interface FleetLocalInfo {
  hostname: string;
  software: string;
  uptime: string;
  chip: string;
}

export interface FleetHealth {
  status: string;
  server: string;
  version: string;
  activeSessions: number;
}
