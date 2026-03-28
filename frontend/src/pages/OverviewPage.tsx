import { useState, useEffect } from "react";
import { usePoll } from "../hooks/usePoll";
import { fetchAll, fetchLLMConfig, updateLLMConfig } from "../api";
import Card, { Stat, Badge } from "../components/Card";
import type { LLMConfig } from "../types";

export default function OverviewPage() {
  const { data, loading, error } = usePoll(fetchAll, 5000);

  // LLM Config state (separate from polling — user-driven)
  const [llmConfig, setLlmConfig] = useState<LLMConfig | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Form state
  const [selectedProvider, setSelectedProvider] = useState("");
  const [modelInput, setModelInput] = useState("");

  // Load LLM config on mount
  useEffect(() => {
    fetchLLMConfig()
      .then((cfg) => {
        setLlmConfig(cfg);
        setSelectedProvider(cfg.active_provider);
        setModelInput(
          cfg.active_provider === "ollama"
            ? cfg.ollama_model
            : cfg.openai_model
        );
      })
      .catch(() => setConfigError("Could not load LLM config"));
  }, []);

  // Sync model input when provider selection changes
  useEffect(() => {
    if (!llmConfig) return;
    if (selectedProvider === "ollama") setModelInput(llmConfig.ollama_model);
    else if (selectedProvider === "openai") setModelInput(llmConfig.openai_model);
    else setModelInput("");
  }, [selectedProvider, llmConfig]);

  const handleSaveConfig = async () => {
    setSaving(true);
    setConfigError(null);
    try {
      const updated = await updateLLMConfig({
        provider: selectedProvider !== llmConfig?.active_provider ? selectedProvider : undefined,
        model: modelInput || undefined,
      });
      setLlmConfig(updated);
      setSelectedProvider(updated.active_provider);
      setModelInput(
        updated.active_provider === "ollama"
          ? updated.ollama_model
          : updated.openai_model
      );
    } catch (err) {
      setConfigError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  if (loading && !data) return <LoadingState />;

  const health = data?.health;
  const router = data?.router;
  const executor = data?.executor;
  const workflows = data?.workflows;
  const scheduler = data?.scheduler;

  const memoryColor =
    health?.memory.status === "normal"
      ? "text-dash-success"
      : health?.memory.status === "warning"
        ? "text-dash-warning"
        : "text-dash-error";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Dashboard Overview</h2>
        {error && <Badge text="Backend offline" variant="error" />}
        {health && <Badge text={health.status} variant="success" />}
      </div>

      {/* System Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card title="Memory">
          {health ? (
            <div className="space-y-2">
              <Stat
                label={`${health.memory.available_gb.toFixed(1)} GB available`}
                value={`${health.memory.percent_used.toFixed(0)}%`}
                color={memoryColor}
              />
              <div className="w-full h-2 bg-dash-border rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    health.memory.status === "normal"
                      ? "bg-dash-success"
                      : health.memory.status === "warning"
                        ? "bg-dash-warning"
                        : "bg-dash-error"
                  }`}
                  style={{ width: `${health.memory.percent_used}%` }}
                />
              </div>
            </div>
          ) : (
            <p className="text-dash-muted text-sm">Unavailable</p>
          )}
        </Card>

        <Card title="LLM Provider">
          {router ? (
            <div className="space-y-1">
              <div className="text-xl font-bold capitalize">{router.active_provider}</div>
              <div className="text-xs text-dash-muted">
                {router.providers.filter((p) => p.available).length} provider(s) online
              </div>
              <Badge
                text={router.memory_ok ? "memory ok" : "memory critical"}
                variant={router.memory_ok ? "success" : "warning"}
              />
            </div>
          ) : (
            <p className="text-dash-muted text-sm">Unavailable</p>
          )}
        </Card>

        <Card title="Agents">
          {executor ? (
            <div className="flex gap-6">
              <Stat label="Registered" value={executor.registered_agents} />
              <Stat label="Completed" value={executor.total_completed} color="text-dash-success" />
              <Stat label="Failed" value={executor.total_failed} color="text-dash-error" />
            </div>
          ) : (
            <p className="text-dash-muted text-sm">Unavailable</p>
          )}
        </Card>

        <Card title="Automation">
          <div className="flex gap-6">
            <Stat label="Workflows" value={workflows?.length ?? 0} />
            <Stat label="Schedules" value={scheduler?.active_schedules ?? 0} />
          </div>
        </Card>
      </div>

      {/* LLM Configuration — Switch Provider & Model */}
      <Card title="LLM Configuration">
        {llmConfig ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Provider Selector */}
              <div>
                <label className="block text-xs text-dash-muted mb-1.5">Active Provider</label>
                <select
                  value={selectedProvider}
                  onChange={(e) => setSelectedProvider(e.target.value)}
                  className="w-full bg-dash-bg border border-dash-border rounded-lg px-3 py-2 text-sm text-dash-text focus:outline-none focus:border-dash-accent transition-colors"
                >
                  {llmConfig.available_providers.map((p) => (
                    <option key={p} value={p}>
                      {p.charAt(0).toUpperCase() + p.slice(1)}
                    </option>
                  ))}
                  {/* Show all known providers even if not yet initialized */}
                  {!llmConfig.available_providers.includes("openai") && (
                    <option value="openai">OpenAI</option>
                  )}
                  {!llmConfig.available_providers.includes("anthropic") && (
                    <option value="anthropic">Anthropic</option>
                  )}
                </select>
              </div>

              {/* Model Input */}
              <div>
                <label className="block text-xs text-dash-muted mb-1.5">Default Model</label>
                <input
                  type="text"
                  value={modelInput}
                  onChange={(e) => setModelInput(e.target.value)}
                  placeholder={
                    selectedProvider === "ollama"
                      ? "e.g. llama3:8b, mistral, codellama"
                      : selectedProvider === "openai"
                        ? "e.g. gpt-4o, gpt-4o-mini"
                        : "e.g. claude-3-sonnet"
                  }
                  className="w-full bg-dash-bg border border-dash-border rounded-lg px-3 py-2 text-sm text-dash-text placeholder:text-dash-muted/50 focus:outline-none focus:border-dash-accent transition-colors"
                />
              </div>

              {/* Save Button */}
              <div className="flex items-end">
                <button
                  onClick={handleSaveConfig}
                  disabled={saving}
                  className="w-full px-4 py-2 text-sm font-medium rounded-lg bg-dash-accent text-white hover:bg-dash-accent/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {saving ? "Saving…" : "Apply Changes"}
                </button>
              </div>
            </div>

            {/* Current config display */}
            <div className="flex flex-wrap gap-4 text-xs text-dash-muted pt-2 border-t border-dash-border">
              <span>
                Current: <strong className="text-dash-text capitalize">{llmConfig.active_provider}</strong>
              </span>
              {llmConfig.ollama_model && (
                <span>
                  Ollama model: <strong className="text-dash-text">{llmConfig.ollama_model}</strong>
                </span>
              )}
              {llmConfig.openai_model && (
                <span>
                  OpenAI model: <strong className="text-dash-text">{llmConfig.openai_model}</strong>
                </span>
              )}
            </div>

            {configError && (
              <p className="text-sm text-dash-error">{configError}</p>
            )}
          </div>
        ) : configError ? (
          <p className="text-sm text-dash-error">{configError}</p>
        ) : (
          <p className="text-dash-muted text-sm animate-pulse">Loading config…</p>
        )}
      </Card>

      {/* System Info */}
      {health && (
        <Card title="System">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-dash-muted">Platform</span>
              <p className="font-medium">{health.platform.os}</p>
            </div>
            <div>
              <span className="text-dash-muted">Architecture</span>
              <p className="font-medium">{health.platform.arch}</p>
            </div>
            <div>
              <span className="text-dash-muted">Python</span>
              <p className="font-medium">{health.platform.python}</p>
            </div>
            <div>
              <span className="text-dash-muted">Total Memory</span>
              <p className="font-medium">{health.memory.total_gb.toFixed(1)} GB</p>
            </div>
          </div>
        </Card>
      )}

      {/* Ollama Status */}
      {health && (
        <Card title="Ollama">
          <div className="flex items-center gap-3">
            <div className={`w-2.5 h-2.5 rounded-full ${health.ollama.reachable ? "bg-dash-success" : "bg-dash-error"}`} />
            <span className="font-medium">{health.ollama.reachable ? "Connected" : "Offline"}</span>
            <span className="text-sm text-dash-muted ml-2">{health.ollama.url}</span>
          </div>
          {!health.ollama.reachable && (
            <p className="text-sm text-dash-muted mt-2">{health.ollama.detail}</p>
          )}
        </Card>
      )}

      {/* LLM Providers Detail */}
      {router && router.providers.length > 0 && (
        <Card title="LLM Providers">
          <div className="space-y-3">
            {router.providers.map((p) => (
              <div key={p.name} className="flex items-center justify-between py-2 border-b border-dash-border last:border-0">
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${p.available ? "bg-dash-success" : "bg-dash-error"}`} />
                  <span className="font-medium capitalize">{p.name}</span>
                </div>
                <div className="text-sm text-dash-muted">
                  {p.available ? `${p.models_count} model(s)` : p.detail || "Offline"}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-dash-muted text-sm animate-pulse">Loading dashboard…</div>
    </div>
  );
}
