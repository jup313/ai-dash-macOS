import { usePoll } from "../hooks/usePoll";
import { fetchRouterStatus } from "../api";
import Card, { Stat, Badge } from "../components/Card";

export default function LLMPage() {
  const { data: router, loading, error, refresh } = usePoll(fetchRouterStatus, 5000);

  if (loading && !router) return <Loading />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">LLM Router</h2>
        <div className="flex items-center gap-3">
          {error && <Badge text="Offline" variant="error" />}
          <button
            onClick={refresh}
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-dash-accent/20 text-dash-accent hover:bg-dash-accent/30 transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Router Status */}
      {router && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card title="Active Provider">
              <div className="text-xl font-bold capitalize">{router.active_provider}</div>
            </Card>
            <Card title="Memory Gate">
              <Badge
                text={router.memory_ok ? "OK — All clear" : "Critical — Blocked"}
                variant={router.memory_ok ? "success" : "error"}
              />
              <p className="text-xs text-dash-muted mt-2">
                {router.memory_ok
                  ? "All providers available"
                  : "LLM requests may be restricted due to memory pressure"}
              </p>
            </Card>
            <Card title="Models">
              <Stat
                label="total available"
                value={router.total_models}
                color={router.total_models > 0 ? "text-dash-success" : "text-dash-muted"}
              />
            </Card>
          </div>

          {/* Provider Details */}
          <Card title="Provider Details">
            <div className="space-y-4">
              {router.providers.map((provider) => (
                <div
                  key={provider.name}
                  className="border border-dash-border rounded-lg p-4"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-2.5 h-2.5 rounded-full ${
                          provider.available ? "bg-dash-success" : "bg-dash-error"
                        }`}
                      />
                      <span className="font-semibold text-lg capitalize">
                        {provider.name}
                      </span>
                    </div>
                    <Badge
                      text={provider.available ? "Online" : "Offline"}
                      variant={provider.available ? "success" : "error"}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-dash-muted">Models</span>
                      <p className="font-medium">{provider.models_count}</p>
                    </div>
                    <div>
                      <span className="text-dash-muted">Default Model</span>
                      <p className="font-medium">{provider.default_model || "—"}</p>
                    </div>
                  </div>

                  {provider.detail && (
                    <p className="text-sm text-dash-muted mt-3">{provider.detail}</p>
                  )}
                </div>
              ))}
            </div>
          </Card>
        </>
      )}

      {!router && !loading && (
        <Card title="Error">
          <p className="text-dash-error text-sm">
            Unable to reach LLM router. Ensure the backend is running.
          </p>
        </Card>
      )}
    </div>
  );
}

function Loading() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-dash-muted text-sm animate-pulse">Loading LLM status…</div>
    </div>
  );
}
