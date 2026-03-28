import { useCallback, useEffect, useState } from "react";
import { usePoll } from "../hooks/usePoll";
import {
  fetchWorkflows,
  fetchSchedulerStatus,
  fetchN8nStatus,
  fetchN8nWorkflows,
  fetchN8nExecutions,
  activateN8nWorkflow,
  deactivateN8nWorkflow,
  executeN8nWorkflow,
  updateN8nConfig,
} from "../api";
import type { N8nStatus, N8nWorkflow, N8nExecution } from "../types";
import Card, { Stat, Badge } from "../components/Card";

/* ─── Tab type ─────────────────────────────────────────────────────────────── */
type Tab = "custom" | "n8n";

export default function AutomationPage() {
  const [tab, setTab] = useState<Tab>("custom");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Automation</h2>
        {/* Tab switcher */}
        <div className="flex rounded-lg bg-dash-surface border border-dash-border overflow-hidden">
          <button
            onClick={() => setTab("custom")}
            className={`px-4 py-1.5 text-xs font-semibold transition-colors ${
              tab === "custom"
                ? "bg-dash-accent text-white"
                : "text-dash-muted hover:text-dash-text"
            }`}
          >
            Custom Engine
          </button>
          <button
            onClick={() => setTab("n8n")}
            className={`px-4 py-1.5 text-xs font-semibold transition-colors ${
              tab === "n8n"
                ? "bg-dash-accent text-white"
                : "text-dash-muted hover:text-dash-text"
            }`}
          >
            n8n Connector
          </button>
        </div>
      </div>

      {tab === "custom" ? <CustomAutomationTab /> : <N8nTab />}
    </div>
  );
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Custom Engine Tab (existing)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
function CustomAutomationTab() {
  const { data: workflows, loading: loadingWf, refresh: refreshWf } = usePoll(fetchWorkflows, 5000);
  const { data: scheduler, loading: loadingSch } = usePoll(fetchSchedulerStatus, 5000);

  const loading = (loadingWf || loadingSch) && !workflows && !scheduler;
  if (loading) return <Loading text="Loading custom workflows…" />;

  const enabledWf = workflows?.filter((w) => w.enabled) ?? [];
  const totalRuns = workflows?.reduce((sum, w) => sum + w.total_runs, 0) ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <RefreshBtn onClick={refreshWf} />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card title="Workflows">
          <Stat label="total" value={workflows?.length ?? 0} />
        </Card>
        <Card title="Enabled">
          <Stat label="active" value={enabledWf.length} color="text-dash-success" />
        </Card>
        <Card title="Total Runs">
          <Stat label="executions" value={totalRuns} />
        </Card>
        <Card title="Schedules">
          <Stat label="active" value={scheduler?.active_schedules ?? 0} color="text-dash-accent" />
        </Card>
      </div>

      {/* Workflows Table */}
      {workflows && workflows.length > 0 ? (
        <Card title={`Workflows (${workflows.length})`}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-dash-muted border-b border-dash-border">
                  <th className="pb-2 font-medium">Name</th>
                  <th className="pb-2 font-medium">Steps</th>
                  <th className="pb-2 font-medium">Trigger</th>
                  <th className="pb-2 font-medium">Runs</th>
                  <th className="pb-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {workflows.map((wf) => (
                  <tr key={wf.workflow_id} className="border-b border-dash-border/50 last:border-0">
                    <td className="py-2.5">
                      <div>
                        <span className="font-medium text-dash-text">{wf.name}</span>
                        {wf.description && (
                          <p className="text-xs text-dash-muted mt-0.5 truncate max-w-xs">{wf.description}</p>
                        )}
                      </div>
                    </td>
                    <td className="py-2.5 text-dash-muted">{wf.step_count}</td>
                    <td className="py-2.5"><Badge text={wf.trigger_type} /></td>
                    <td className="py-2.5 text-dash-muted">{wf.total_runs}</td>
                    <td className="py-2.5">
                      <Badge text={wf.enabled ? "Enabled" : "Disabled"} variant={wf.enabled ? "success" : "default"} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        <Card title="Workflows">
          <p className="text-dash-muted text-sm">No workflows defined yet. Use the API to create workflows.</p>
        </Card>
      )}

      {/* Scheduler Detail */}
      {scheduler && scheduler.schedules.length > 0 && (
        <Card title={`Scheduled Jobs (${scheduler.schedules.length})`}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-dash-muted border-b border-dash-border">
                  <th className="pb-2 font-medium">Workflow</th>
                  <th className="pb-2 font-medium">Interval</th>
                  <th className="pb-2 font-medium">Runs</th>
                  <th className="pb-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {scheduler.schedules.map((s) => (
                  <tr key={s.workflow_id} className="border-b border-dash-border/50 last:border-0">
                    <td className="py-2 font-medium text-dash-text">{s.workflow_name}</td>
                    <td className="py-2 text-dash-muted">{formatInterval(s.interval_seconds)}</td>
                    <td className="py-2 text-dash-muted">{s.total_runs}</td>
                    <td className="py-2">
                      <Badge text={s.is_active ? "Active" : "Paused"} variant={s.is_active ? "success" : "warning"} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Capabilities */}
      <Card title="Capabilities">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="p-3 bg-dash-bg rounded-lg">
            <h4 className="font-semibold text-dash-accent mb-1">Step Types</h4>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {["llm_query", "agent_task", "code_execute", "http_request", "condition", "transform"].map((t) => (
                <Badge key={t} text={t} />
              ))}
            </div>
          </div>
          <div className="p-3 bg-dash-bg rounded-lg">
            <h4 className="font-semibold text-dash-accent mb-1">Features</h4>
            <ul className="text-dash-muted space-y-1 mt-2">
              <li>• Sequential step execution with context passing</li>
              <li>• Conditional branching and error handling</li>
              <li>• Interval-based scheduling with max runs</li>
              <li>• Manual and scheduled trigger types</li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   n8n Connector Tab
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
function N8nTab() {
  const [status, setStatus] = useState<N8nStatus | null>(null);
  const [workflows, setWorkflows] = useState<N8nWorkflow[]>([]);
  const [executions, setExecutions] = useState<N8nExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Config form state
  const [cfgUrl, setCfgUrl] = useState("http://localhost:5678");
  const [cfgKey, setCfgKey] = useState("");
  const [cfgEnabled, setCfgEnabled] = useState(false);
  const [saving, setSaving] = useState(false);
  const [configMsg, setConfigMsg] = useState<string | null>(null);

  // Action state
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const s = await fetchN8nStatus();
      setStatus(s);
      setCfgUrl(s.url);
      setCfgEnabled(s.enabled);
      if (s.connected) {
        const [wf, ex] = await Promise.all([fetchN8nWorkflows(), fetchN8nExecutions()]);
        setWorkflows(wf);
        setExecutions(ex);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to fetch n8n status");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  // Save config
  const saveConfig = async () => {
    setSaving(true);
    setConfigMsg(null);
    try {
      const updated = await updateN8nConfig({
        n8n_url: cfgUrl,
        n8n_api_key: cfgKey || undefined,
        n8n_enabled: cfgEnabled,
      });
      setConfigMsg(`✓ Config saved — ${updated.n8n_enabled ? "enabled" : "disabled"}`);
      setCfgKey(""); // clear key field after save
      await refresh();
    } catch (e: unknown) {
      setConfigMsg(`✗ ${e instanceof Error ? e.message : "Save failed"}`);
    } finally {
      setSaving(false);
    }
  };

  // Workflow actions
  const handleToggle = async (wf: N8nWorkflow) => {
    setActionLoading(wf.id);
    try {
      if (wf.active) await deactivateN8nWorkflow(wf.id);
      else await activateN8nWorkflow(wf.id);
      await refresh();
    } catch { /* swallow */ }
    setActionLoading(null);
  };

  const handleExecute = async (wf: N8nWorkflow) => {
    setActionLoading(`exec-${wf.id}`);
    try {
      await executeN8nWorkflow(wf.id);
      await refresh();
    } catch { /* swallow */ }
    setActionLoading(null);
  };

  if (loading) return <Loading text="Connecting to n8n…" />;

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <RefreshBtn onClick={refresh} />
      </div>

      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 p-3 text-sm text-red-400">{error}</div>
      )}

      {/* ── Connection Settings ─────────────────────────────────────────── */}
      <Card title="n8n Connection Settings">
        <div className="space-y-4">
          {/* Status indicator */}
          <div className="flex items-center gap-3">
            <span
              className={`inline-block w-3 h-3 rounded-full ${
                status?.connected ? "bg-dash-success animate-pulse" : "bg-red-500"
              }`}
            />
            <span className="text-sm font-medium">
              {status?.connected
                ? `Connected — ${status.workflow_count ?? 0} workflows, ${status.active_workflows ?? 0} active`
                : status?.enabled
                  ? `Disconnected — ${status.detail}`
                  : "n8n integration is disabled"}
            </span>
          </div>

          {/* Config form */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-dash-muted mb-1 font-medium">n8n URL</label>
              <input
                type="text"
                value={cfgUrl}
                onChange={(e) => setCfgUrl(e.target.value)}
                placeholder="http://localhost:5678"
                className="w-full bg-dash-bg border border-dash-border rounded-lg px-3 py-2 text-sm text-dash-text placeholder-dash-muted/50 focus:outline-none focus:border-dash-accent"
              />
            </div>
            <div>
              <label className="block text-xs text-dash-muted mb-1 font-medium">API Key</label>
              <input
                type="password"
                value={cfgKey}
                onChange={(e) => setCfgKey(e.target.value)}
                placeholder={status?.connected ? "••••••• (saved)" : "Enter n8n API key"}
                className="w-full bg-dash-bg border border-dash-border rounded-lg px-3 py-2 text-sm text-dash-text placeholder-dash-muted/50 focus:outline-none focus:border-dash-accent"
              />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={cfgEnabled}
                onChange={(e) => setCfgEnabled(e.target.checked)}
                className="w-4 h-4 rounded border-dash-border bg-dash-bg text-dash-accent focus:ring-dash-accent focus:ring-offset-0"
              />
              <span className="text-sm font-medium">Enable n8n integration</span>
            </label>

            <div className="flex items-center gap-3">
              {configMsg && (
                <span className={`text-xs ${configMsg.startsWith("✓") ? "text-dash-success" : "text-red-400"}`}>
                  {configMsg}
                </span>
              )}
              <button
                onClick={saveConfig}
                disabled={saving}
                className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-dash-accent text-white hover:bg-dash-accent/80 disabled:opacity-50 transition-colors"
              >
                {saving ? "Saving…" : "Save & Reconnect"}
              </button>
            </div>
          </div>
        </div>
      </Card>

      {/* ── n8n Workflows ───────────────────────────────────────────────── */}
      {status?.connected && (
        <Card title={`n8n Workflows (${workflows.length})`}>
          {workflows.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-dash-muted border-b border-dash-border">
                    <th className="pb-2 font-medium">Name</th>
                    <th className="pb-2 font-medium">Nodes</th>
                    <th className="pb-2 font-medium">Tags</th>
                    <th className="pb-2 font-medium">Updated</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {workflows.map((wf) => (
                    <tr key={wf.id} className="border-b border-dash-border/50 last:border-0">
                      <td className="py-2.5">
                        <span className="font-medium text-dash-text">{wf.name}</span>
                        <span className="text-[10px] text-dash-muted ml-2">#{wf.id}</span>
                      </td>
                      <td className="py-2.5 text-dash-muted">{wf.nodes_count}</td>
                      <td className="py-2.5">
                        <div className="flex flex-wrap gap-1">
                          {wf.tags.length > 0
                            ? wf.tags.map((t) => <Badge key={t} text={t} />)
                            : <span className="text-dash-muted text-xs">—</span>}
                        </div>
                      </td>
                      <td className="py-2.5 text-dash-muted text-xs">{formatDate(wf.updated_at)}</td>
                      <td className="py-2.5">
                        <Badge text={wf.active ? "Active" : "Inactive"} variant={wf.active ? "success" : "default"} />
                      </td>
                      <td className="py-2.5 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => handleToggle(wf)}
                            disabled={actionLoading === wf.id}
                            className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-colors ${
                              wf.active
                                ? "bg-orange-500/15 text-orange-400 hover:bg-orange-500/25"
                                : "bg-dash-success/15 text-dash-success hover:bg-dash-success/25"
                            } disabled:opacity-40`}
                          >
                            {actionLoading === wf.id ? "…" : wf.active ? "Deactivate" : "Activate"}
                          </button>
                          <button
                            onClick={() => handleExecute(wf)}
                            disabled={actionLoading === `exec-${wf.id}`}
                            className="px-2.5 py-1 text-[11px] font-medium rounded-md bg-dash-accent/15 text-dash-accent hover:bg-dash-accent/25 disabled:opacity-40 transition-colors"
                          >
                            {actionLoading === `exec-${wf.id}` ? "Running…" : "▶ Execute"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-dash-muted text-sm">No workflows found in n8n. Create workflows in the n8n editor first.</p>
          )}
        </Card>
      )}

      {/* ── Execution History ───────────────────────────────────────────── */}
      {status?.connected && executions.length > 0 && (
        <Card title={`Recent Executions (${executions.length})`}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-dash-muted border-b border-dash-border">
                  <th className="pb-2 font-medium">Workflow</th>
                  <th className="pb-2 font-medium">Mode</th>
                  <th className="pb-2 font-medium">Started</th>
                  <th className="pb-2 font-medium">Finished</th>
                  <th className="pb-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {executions.map((ex) => (
                  <tr key={ex.id} className="border-b border-dash-border/50 last:border-0">
                    <td className="py-2">
                      <span className="font-medium text-dash-text">{ex.workflow_name}</span>
                    </td>
                    <td className="py-2"><Badge text={ex.mode} /></td>
                    <td className="py-2 text-dash-muted text-xs">{formatDate(ex.started_at)}</td>
                    <td className="py-2 text-dash-muted text-xs">{ex.finished_at ? formatDate(ex.finished_at) : "—"}</td>
                    <td className="py-2">
                      <Badge
                        text={ex.status}
                        variant={
                          ex.status === "success" ? "success" : ex.status === "error" ? "error" : "warning"
                        }
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ── n8n Info ─────────────────────────────────────────────────────── */}
      <Card title="n8n Integration Info">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="p-3 bg-dash-bg rounded-lg">
            <h4 className="font-semibold text-dash-accent mb-2">Supported Operations</h4>
            <div className="flex flex-wrap gap-1.5">
              {["List Workflows", "Activate/Deactivate", "Execute", "Webhook Trigger", "Execution History"].map((op) => (
                <Badge key={op} text={op} />
              ))}
            </div>
          </div>
          <div className="p-3 bg-dash-bg rounded-lg">
            <h4 className="font-semibold text-dash-accent mb-2">Setup Guide</h4>
            <ul className="text-dash-muted space-y-1">
              <li>1. Install n8n: <code className="text-dash-accent text-xs">npm install -g n8n</code></li>
              <li>2. Start n8n: <code className="text-dash-accent text-xs">n8n start</code></li>
              <li>3. Generate an API key in n8n Settings → API</li>
              <li>4. Enter your URL and key above, enable, and save</li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Shared helpers
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

function RefreshBtn({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="px-3 py-1.5 text-xs font-medium rounded-lg bg-dash-accent/20 text-dash-accent hover:bg-dash-accent/30 transition-colors"
    >
      Refresh
    </button>
  );
}

function formatInterval(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${(seconds / 3600).toFixed(1)}h`;
  return `${(seconds / 86400).toFixed(1)}d`;
}

function formatDate(iso: string): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function Loading({ text = "Loading…" }: { text?: string }) {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-dash-muted text-sm animate-pulse">{text}</div>
    </div>
  );
}
