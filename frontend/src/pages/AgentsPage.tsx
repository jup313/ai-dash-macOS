import { useState } from "react";
import { usePoll } from "../hooks/usePoll";
import { fetchAgents, fetchExecutorStatus, fetchConversations, fetchMemoryStats } from "../api";
import Card, { Stat, Badge } from "../components/Card";

export default function AgentsPage() {
  const { data: agents, loading: loadingAgents } = usePoll(fetchAgents, 5000);
  const { data: executor, loading: loadingExec } = usePoll(fetchExecutorStatus, 5000);
  const { data: conversations } = usePoll(fetchConversations, 5000);
  const { data: memStats } = usePoll(fetchMemoryStats, 10000);

  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

  const loading = (loadingAgents || loadingExec) && !agents && !executor;
  if (loading) return <Loading />;

  const selected = agents?.find((a) => a.name === selectedAgent);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Agents &amp; Memory</h2>

      {/* Executor Status */}
      {executor && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card title="Registered">
            <Stat label="agents" value={executor.registered_agents} />
          </Card>
          <Card title="Active">
            <Stat
              label={`of ${executor.max_concurrency} slots`}
              value={executor.active_tasks}
              color="text-dash-accent"
            />
          </Card>
          <Card title="Completed">
            <Stat label="runs" value={executor.total_completed} color="text-dash-success" />
          </Card>
          <Card title="Failed">
            <Stat label="runs" value={executor.total_failed} color="text-dash-error" />
          </Card>
          <Card title="Conversations">
            <Stat label={`of ${memStats?.max_conversations ?? "?"} max`} value={memStats?.total_conversations ?? 0} />
          </Card>
        </div>
      )}

      {/* Agent List */}
      {agents && agents.length > 0 && (
        <Card title={`Agents (${agents.length})`}>
          <div className="space-y-2">
            {agents.map((agent) => (
              <button
                key={agent.name}
                onClick={() => setSelectedAgent(selectedAgent === agent.name ? null : agent.name)}
                className={`w-full text-left flex items-center justify-between p-3 rounded-lg border transition-colors ${
                  selectedAgent === agent.name
                    ? "border-dash-accent bg-dash-accent/10"
                    : "border-dash-border hover:border-dash-accent/50"
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="font-medium">{agent.name}</span>
                  <Badge text={agent.agent_type} />
                </div>
                <span className="text-xs text-dash-muted">{agent.provider ?? "default"}</span>
              </button>
            ))}
          </div>
        </Card>
      )}

      {/* Agent Detail */}
      {selected && (
        <Card title={`Agent: ${selected.name}`}>
          <div className="space-y-3 text-sm">
            <div>
              <span className="text-dash-muted">Type</span>
              <p className="font-medium">{selected.agent_type}</p>
            </div>
            <div>
              <span className="text-dash-muted">Description</span>
              <p className="font-medium">{selected.description}</p>
            </div>
            <div>
              <span className="text-dash-muted">Model</span>
              <p className="font-medium">{selected.model ?? "Provider default"}</p>
            </div>
            <div>
              <span className="text-dash-muted">Provider</span>
              <p className="font-medium capitalize">{selected.provider ?? "Router default"}</p>
            </div>
            <div>
              <span className="text-dash-muted">System Prompt</span>
              <pre className="mt-1 p-3 bg-dash-bg rounded-lg text-xs text-dash-text-dim whitespace-pre-wrap overflow-auto max-h-40">
                {selected.system_prompt}
              </pre>
            </div>
          </div>
        </Card>
      )}

      {/* Conversations */}
      {conversations && conversations.length > 0 && (
        <Card title={`Recent Conversations (${conversations.length})`}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-dash-muted border-b border-dash-border">
                  <th className="pb-2 font-medium">Title</th>
                  <th className="pb-2 font-medium">Messages</th>
                  <th className="pb-2 font-medium">Updated</th>
                </tr>
              </thead>
              <tbody>
                {conversations.slice(0, 20).map((c) => (
                  <tr key={c.conversation_id} className="border-b border-dash-border/50 last:border-0">
                    <td className="py-2 font-medium text-dash-text">{c.title}</td>
                    <td className="py-2 text-dash-muted">{c.message_count}</td>
                    <td className="py-2 text-dash-muted">
                      {new Date(c.updated_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {memStats && (
        <Card title="Memory Store Stats">
          <div className="grid grid-cols-3 gap-4">
            <Stat label="conversations" value={memStats.total_conversations} />
            <Stat label="messages" value={memStats.total_messages} />
            <Stat label="max capacity" value={memStats.max_conversations} />
          </div>
        </Card>
      )}
    </div>
  );
}

function Loading() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-dash-muted text-sm animate-pulse">Loading agents…</div>
    </div>
  );
}
