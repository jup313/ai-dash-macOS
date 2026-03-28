import { usePoll } from "../hooks/usePoll";
import { fetchAll } from "../api";
import Card, { Stat, Badge } from "../components/Card";

export default function OverviewPage() {
  const { data, loading, error } = usePoll(fetchAll, 5000);

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
              <div className="text-xl font-bold capitalize">{router.default_provider}</div>
              <div className="text-xs text-dash-muted">
                {router.providers.filter((p) => p.available).length} provider(s) online
              </div>
              <Badge
                text={router.memory_status}
                variant={router.memory_status === "normal" ? "success" : "warning"}
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

      {/* System Info */}
      {health && (
        <Card title="System">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-dash-muted">Platform</span>
              <p className="font-medium">{health.platform}</p>
            </div>
            <div>
              <span className="text-dash-muted">Architecture</span>
              <p className="font-medium">{health.architecture}</p>
            </div>
            <div>
              <span className="text-dash-muted">Python</span>
              <p className="font-medium">{health.python_version}</p>
            </div>
            <div>
              <span className="text-dash-muted">Total Memory</span>
              <p className="font-medium">{health.memory.total_gb.toFixed(1)} GB</p>
            </div>
          </div>
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
                  {p.available ? `${p.models.length} model(s)` : p.error || "Offline"}
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
