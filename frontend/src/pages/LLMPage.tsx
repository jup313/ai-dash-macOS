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
            <Card title="Default Provider">
              <div className="text-xl font-bold capitalize">{router.default_provider}</div>
            </Card>
            <Card title="Memory Gate">
              <Badge
                text={router.memory_status}
                variant={
                  router.memory_status === "normal"
                    ? "success"
                    : router.memory_status === "warning"
                      ? "warning"
                      : "error"
                }
              />
              <p className="text-xs text-dash-muted mt-2">
                {router.memory_status === "normal"
                  ? "All providers available"
                  : router.memory_status === "warning"
                    ? "Large models restricted"
                    : "LLM requests blocked"}
              </p>
            </Card>
            <Card title="Providers">
              <Stat
                label="online"
                value={router.providers.filter((p) => p.available).length}
                color="text-dash-success"
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

                  {provider.error && (
                    <p className="text-sm text-dash-error mb-3">{provider.error}</p>
                  )}

                  {provider.available && provider.models.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-left text-dash-muted border-b border-dash-border">
                            <th className="pb-2 font-medium">Model</th>
                            <th className="pb-2 font-medium">Size</th>
                            <th className="pb-2 font-medium">Modified</th>
                          </tr>
                        </thead>
                        <tbody>
                          {provider.models.map((model) => (
                            <tr
                              key={model.name}
                              className="border-b border-dash-border/50 last:border-0"
                            >
                              <td className="py-2 font-medium text-dash-text">
                                {model.name}
                              </td>
                              <td className="py-2 text-dash-muted">
                                {model.size ?? "—"}
                              </td>
                              <td className="py-2 text-dash-muted">
                                {model.modified_at
                                  ? new Date(model.modified_at).toLocaleDateString()
                                  : "—"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : provider.available ? (
                    <p className="text-sm text-dash-muted">No models loaded</p>
                  ) : null}
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
