interface CardProps {
  title: string;
  children: React.ReactNode;
  className?: string;
}

export default function Card({ title, children, className = "" }: CardProps) {
  return (
    <div className={`bg-dash-surface border border-dash-border rounded-xl p-5 ${className}`}>
      <h3 className="text-sm font-semibold text-dash-text-dim uppercase tracking-wider mb-3">
        {title}
      </h3>
      {children}
    </div>
  );
}

export function Stat({ label, value, color = "text-dash-text" }: { label: string; value: string | number; color?: string }) {
  return (
    <div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-dash-muted mt-0.5">{label}</div>
    </div>
  );
}

export function Badge({ text, variant = "default" }: { text: string; variant?: "default" | "success" | "warning" | "error" }) {
  const colors = {
    default: "bg-dash-border text-dash-text-dim",
    success: "bg-dash-success/20 text-dash-success",
    warning: "bg-dash-warning/20 text-dash-warning",
    error: "bg-dash-error/20 text-dash-error",
  };
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${colors[variant]}`}>
      {text}
    </span>
  );
}
