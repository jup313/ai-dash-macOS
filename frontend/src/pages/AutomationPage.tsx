import { usePoll } from "../hooks/usePoll";
import { fetchWorkflows, fetchSchedulerStatus } from "../api";
import Card, { Stat, Badge } from "../components/Card";

export default function AutomationPage() {
  const { data: workflows, loading: loadingWf, refresh: refreshWf } = usePoll(fetchWorkflows, 5000);
  const { data: scheduler, loading: loadingSch } = usePoll(fetchSchedulerStatus, 5000);

  const loading = (loadingWf || loadingSch) && !workflows && !scheduler;
  if (loading) return <Loading />;

  const enabledWf = workflows?.filter((w) => w.enabled) ?? [];
  const totalRuns = workflows?.reduce((sum, w) => sum + w.total_runs, 0) ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Automation</h2>
        <button
          onClick={refreshWf}
          className="px-3 py-1.5 text-xs font-medium rounded-lg bg-dash-accent/20 text-dash-accent hover:bg-dash-accent/30 transition-colors"
        >
          Refresh
        </button>
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
          <Stat
            label="active"
            value={scheduler?.active_schedules ?? 0}
            color="text-dash-accent"
          />
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
                  <tr
                    key={wf.workflow_id}
                    className="border-b border-dash-border/50 last:border-0"
                  >
                    <td className="py-2.5">
                      <div>
                        <span className="font-medium text-dash-text">{wf.name}</span>
                        {wf.description && (
                          <p className="text-xs text-dash-muted mt-0.5 truncate max-w-xs">
                            {wf.description}
                          </p>
                        )}
                      </div>
                    </td>
                    <td className="py-2.5 text-dash-muted">{wf.step_count}</td>
                    <td className="py-2.5">
                      <Badge text={wf.trigger_type} />
                    </td>
                    <td className="py-2.5 text-dash-muted">{wf.total_runs}</td>
                    <td className="py-2.5">
                      <Badge
                        text={wf.enabled ? "Enabled" : "Disabled"}
                        variant={wf.enabled ? "success" : "default"}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : !loading ? (
        <Card title="Workflows">
          <p className="text-dash-muted text-sm">
            No workflows defined yet. Use the API to create workflows.
          </p>
        </Card>
      ) : null}

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
                  <tr
                    key={s.workflow_id}
                    className="border-b border-dash-border/50 last:border-0"
                  >
                    <td className="py-2 font-medium text-dash-text">{s.workflow_name}</td>
                    <td className="py-2 text-dash-muted">{formatInterval(s.interval_seconds)}</td>
                    <td className="py-2 text-dash-muted">{s.total_runs}</td>
                    <td className="py-2">
                      <Badge
                        text={s.is_active ? "Active" : "Paused"}
                        variant={s.is_active ? "success" : "warning"}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Automation Capabilities */}
      <Card title="Capabilities">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="p-3 bg-dash-bg rounded-lg">
            <h4 className="font-semibold text-dash-accent mb-1">Step Types</h4>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {["llm_query", "agent_task", "code_execute", "http_request", "condition", "transform"].map(
                (t) => (
                  <Badge key={t} text={t} />
                )
              )}
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

function formatInterval(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${(seconds / 3600).toFixed(1)}h`;
  return `${(seconds / 86400).toFixed(1)}d`;
}

function Loading() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-dash-muted text-sm animate-pulse">Loading automation…</div>
    </div>
  );
}
