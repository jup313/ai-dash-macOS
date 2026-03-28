import { usePoll } from "../hooks/usePoll";
import { fetchFiles } from "../api";
import Card, { Stat, Badge } from "../components/Card";

export default function CodingPage() {
  const { data: files, loading, error, refresh } = usePoll(fetchFiles, 10000);

  if (loading && !files) return <Loading />;

  const totalSize = files?.reduce((sum, f) => sum + f.size_bytes, 0) ?? 0;
  const dirs = files?.filter((f) => f.is_directory) ?? [];
  const regularFiles = files?.filter((f) => !f.is_directory) ?? [];
  const languages = [...new Set(regularFiles.map((f) => f.language).filter(Boolean))];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Coding Engine</h2>
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

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card title="Files">
          <Stat label="in workspace" value={regularFiles.length} />
        </Card>
        <Card title="Directories">
          <Stat label="folders" value={dirs.length} />
        </Card>
        <Card title="Languages">
          <Stat label="detected" value={languages.length} />
        </Card>
        <Card title="Total Size">
          <Stat label="bytes" value={formatBytes(totalSize)} />
        </Card>
      </div>

      {/* Languages */}
      {languages.length > 0 && (
        <Card title="Languages Detected">
          <div className="flex flex-wrap gap-2">
            {languages.map((lang) => (
              <Badge key={lang} text={lang} variant="default" />
            ))}
          </div>
        </Card>
      )}

      {/* File Browser */}
      {files && files.length > 0 ? (
        <Card title={`Workspace Files (${files.length})`}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-dash-muted border-b border-dash-border">
                  <th className="pb-2 font-medium">Name</th>
                  <th className="pb-2 font-medium">Type</th>
                  <th className="pb-2 font-medium">Language</th>
                  <th className="pb-2 font-medium text-right">Size</th>
                </tr>
              </thead>
              <tbody>
                {files.map((f) => (
                  <tr
                    key={f.path}
                    className="border-b border-dash-border/50 last:border-0"
                  >
                    <td className="py-2">
                      <div className="flex items-center gap-2">
                        <span className="text-dash-muted">
                          {f.is_directory ? "📁" : "📄"}
                        </span>
                        <span className="font-medium text-dash-text">{f.name}</span>
                      </div>
                    </td>
                    <td className="py-2 text-dash-muted">
                      {f.is_directory ? "dir" : f.extension || "—"}
                    </td>
                    <td className="py-2">
                      {f.language ? (
                        <Badge text={f.language} />
                      ) : (
                        <span className="text-dash-muted">—</span>
                      )}
                    </td>
                    <td className="py-2 text-right text-dash-muted">
                      {f.is_directory ? "—" : formatBytes(f.size_bytes)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : !loading ? (
        <Card title="Workspace">
          <p className="text-dash-muted text-sm">
            No files found. The workspace directory may be empty or the backend is offline.
          </p>
        </Card>
      ) : null}

      {/* Capabilities Info */}
      <Card title="Capabilities">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div className="p-3 bg-dash-bg rounded-lg">
            <h4 className="font-semibold text-dash-accent mb-1">Analyze</h4>
            <p className="text-dash-muted">
              AST-based code analysis with complexity metrics, function extraction, and issue detection.
            </p>
          </div>
          <div className="p-3 bg-dash-bg rounded-lg">
            <h4 className="font-semibold text-dash-accent mb-1">Generate</h4>
            <p className="text-dash-muted">
              LLM-powered code generation, refactoring, documentation, and test writing.
            </p>
          </div>
          <div className="p-3 bg-dash-bg rounded-lg">
            <h4 className="font-semibold text-dash-accent mb-1">Execute</h4>
            <p className="text-dash-muted">
              Sandboxed code execution with timeout protection and output capture.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(i === 0 ? 0 : 1)} ${sizes[i]}`;
}

function Loading() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-dash-muted text-sm animate-pulse">Loading coding engine…</div>
    </div>
  );
}
