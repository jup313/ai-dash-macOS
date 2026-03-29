import { useEffect, useState } from "react";
import { fetchFleetStatus, fetchFleetLocalInfo } from "../api";
import type { FleetStatus, FleetDevice, FleetLocalInfo } from "../types";

// ── Device type icons & colors ───────────────────────────────────────────────

const DEVICE_META: Record<string, { icon: string; color: string; label: string }> = {
  mac:        { icon: "🖥", color: "text-blue-400",   label: "Local Mac" },
  "remote-mac": { icon: "💻", color: "text-cyan-400",  label: "Remote Mac" },
  qnap:       { icon: "🗄", color: "text-amber-400",  label: "QNAP NAS" },
  unifi:      { icon: "📡", color: "text-green-400",  label: "UniFi" },
  alexa:      { icon: "🔊", color: "text-purple-400", label: "Alexa" },
  sonos:      { icon: "🎵", color: "text-pink-400",   label: "Sonos" },
};

function meta(type: string) {
  return DEVICE_META[type] ?? { icon: "⬡", color: "text-dash-text-dim", label: type };
}

// ── Status badge ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    online:  "bg-green-500/20 text-green-400 border-green-500/30",
    offline: "bg-red-500/20 text-red-400 border-red-500/30",
    unconfigured: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  };
  return (
    <span
      className={`px-2.5 py-0.5 text-xs font-medium rounded-full border ${
        styles[status] ?? styles.unconfigured
      }`}
    >
      {status}
    </span>
  );
}

// ── Device Card ──────────────────────────────────────────────────────────────

function DeviceCard({ device }: { device: FleetDevice }) {
  const m = meta(device.type);
  return (
    <div className="bg-dash-surface border border-dash-border rounded-xl p-5 hover:border-dash-accent/40 transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className={`text-2xl ${m.color}`}>{m.icon}</span>
          <div>
            <h3 className="text-sm font-semibold text-dash-text">{device.name}</h3>
            <p className="text-xs text-dash-muted">{m.label}</p>
          </div>
        </div>
        <StatusBadge status={device.status} />
      </div>
      <div className="space-y-1.5 text-xs text-dash-text-dim">
        <div className="flex justify-between">
          <span>Host</span>
          <span className="font-mono text-dash-text">{device.host}</span>
        </div>
        {device.detail && (
          <div className="flex justify-between">
            <span>Detail</span>
            <span className="text-dash-text">{device.detail}</span>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Local Mac Info Panel ─────────────────────────────────────────────────────

function LocalMacPanel({ info }: { info: FleetLocalInfo | null }) {
  if (!info) return null;
  return (
    <div className="bg-dash-surface border border-dash-border rounded-xl p-5 col-span-full">
      <h3 className="text-sm font-semibold text-dash-text mb-3 flex items-center gap-2">
        <span className="text-blue-400">🖥</span> Local Mac Details
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
        <div>
          <span className="text-dash-muted block">Hostname</span>
          <span className="text-dash-text font-mono">{info.hostname}</span>
        </div>
        <div>
          <span className="text-dash-muted block">Chip</span>
          <span className="text-dash-text">{info.chip}</span>
        </div>
        <div>
          <span className="text-dash-muted block">Uptime</span>
          <span className="text-dash-text">{info.uptime}</span>
        </div>
        <div>
          <span className="text-dash-muted block">Software</span>
          <span className="text-dash-text whitespace-pre-line">{info.software}</span>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function DevicesPage() {
  const [fleet, setFleet] = useState<FleetStatus | null>(null);
  const [localInfo, setLocalInfo] = useState<FleetLocalInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const [status, info] = await Promise.allSettled([
        fetchFleetStatus(),
        fetchFleetLocalInfo(),
      ]);
      if (status.status === "fulfilled") setFleet(status.value);
      else setError(status.reason?.message ?? "Failed to fetch fleet status");
      if (info.status === "fulfilled") setLocalInfo(info.value);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 30_000); // refresh every 30s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-dash-text">Device Fleet</h1>
          <p className="text-sm text-dash-muted mt-1">
            {fleet
              ? fleet.summary
              : loading
              ? "Loading fleet status…"
              : "Fleet MCP server unavailable"}
          </p>
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="px-4 py-2 text-sm font-medium rounded-lg bg-dash-accent/20 text-dash-accent hover:bg-dash-accent/30 disabled:opacity-50 transition-colors"
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          <strong>Fleet MCP Error:</strong> {error}
          <p className="mt-1 text-xs text-red-400/70">
            Make sure the fleet-mcp-server is running in SSE mode:{" "}
            <code className="font-mono">cd ~/Desktop/fleet && npm run start:sse</code>
          </p>
        </div>
      )}

      {/* Summary cards */}
      {fleet && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-dash-surface border border-dash-border rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-dash-text">{fleet.total}</div>
            <div className="text-xs text-dash-muted mt-1">Total Devices</div>
          </div>
          <div className="bg-dash-surface border border-green-500/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-green-400">{fleet.online}</div>
            <div className="text-xs text-dash-muted mt-1">Online</div>
          </div>
          <div className="bg-dash-surface border border-red-500/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-red-400">
              {fleet.total - fleet.online}
            </div>
            <div className="text-xs text-dash-muted mt-1">Offline</div>
          </div>
        </div>
      )}

      {/* Local Mac details */}
      <LocalMacPanel info={localInfo} />

      {/* Device grid */}
      {fleet && fleet.devices.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
          {fleet.devices.map((device) => (
            <DeviceCard key={device.name} device={device} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && !fleet && !error && (
        <div className="text-center py-16 text-dash-muted">
          <p className="text-4xl mb-3">📡</p>
          <p className="text-sm">No fleet data available.</p>
          <p className="text-xs mt-1">Start the fleet-mcp-server with SSE mode to see devices here.</p>
        </div>
      )}
    </div>
  );
}
