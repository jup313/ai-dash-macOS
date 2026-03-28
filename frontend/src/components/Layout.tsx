import { NavLink, Outlet } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "Overview", icon: "◉" },
  { to: "/llm", label: "LLM", icon: "⬡" },
  { to: "/agents", label: "Agents", icon: "◈" },
  { to: "/coding", label: "Coding", icon: "⟨⟩" },
  { to: "/automation", label: "Automation", icon: "⟳" },
];

function SidebarLink({ to, label, icon }: { to: string; label: string; icon: string }) {
  return (
    <NavLink
      to={to}
      end={to === "/"}
      className={({ isActive }) =>
        `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
          isActive
            ? "bg-dash-accent/20 text-dash-accent"
            : "text-dash-text-dim hover:text-dash-text hover:bg-dash-border/30"
        }`
      }
    >
      <span className="text-base">{icon}</span>
      {label}
    </NavLink>
  );
}

export default function Layout() {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 bg-dash-surface border-r border-dash-border flex flex-col">
        <div className="px-5 py-5 border-b border-dash-border">
          <h1 className="text-lg font-bold text-dash-text tracking-tight">
            ai-dash
            <span className="text-dash-accent">macOS</span>
          </h1>
          <p className="text-xs text-dash-muted mt-0.5">Universal LLM Control</p>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map((item) => (
            <SidebarLink key={item.to} {...item} />
          ))}
        </nav>
        <div className="px-4 py-3 border-t border-dash-border text-xs text-dash-muted">
          v0.1.0 · Apple Silicon
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
