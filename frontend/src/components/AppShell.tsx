import { LayoutGrid, LogOut, Server, ShieldCheck, Terminal } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

const NAV_ITEMS = [
  { to: "/", label: "Overview", icon: LayoutGrid, end: true },
  { to: "/services", label: "Services", icon: Server, end: false }
];

export function AppShell() {
  const { user, logout, logoutAll } = useAuth();

  return (
    <div className="min-h-screen bg-canvas text-slate-100 flex">
      <aside className="w-56 shrink-0 border-r border-border bg-surface flex flex-col justify-between">
        <div>
          <div className="h-12 px-4 border-b border-border flex items-center gap-2.5">
            <div className="flex h-6 w-6 items-center justify-center rounded border border-border bg-panel text-slate-200">
              <Terminal className="h-3.5 w-3.5" />
            </div>
            <span className="text-sm font-semibold tracking-tight text-slate-100">NexusOps</span>
          </div>

          <nav aria-label="Primary" className="p-2.5 space-y-0.5">
            {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-all duration-150 ${
                    isActive
                      ? "bg-panel text-slate-100 border border-border"
                      : "text-slate-400 border border-transparent hover:text-slate-200 hover:bg-panel/50"
                  }`
                }
              >
                <Icon className="h-3.5 w-3.5 shrink-0" />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="mx-3 mt-4 border-t border-border pt-4">
            <p className="px-1.5 text-[10px] font-medium uppercase tracking-wider text-slate-500">
              Upcoming Phases
            </p>
            <ul className="mt-2 space-y-1 px-1.5 text-xs text-slate-500">
              <li>Telemetry &amp; Metrics</li>
              <li>Incidents &amp; AI RCA</li>
              <li>Dependency Graph</li>
              <li>Remediation Center</li>
            </ul>
          </div>
        </div>

        <div className="border-t border-border p-3 space-y-2.5">
          {user && (
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="truncate text-xs font-medium text-slate-200">{user.full_name}</p>
                <p className="truncate text-[11px] text-slate-400">{user.email}</p>
              </div>
              <span className="shrink-0 inline-flex items-center gap-1 rounded border border-border bg-canvas px-1.5 py-0.5 font-mono text-[10px] text-slate-300">
                <ShieldCheck className="h-2.5 w-2.5 text-slate-400" />
                {user.role}
              </span>
            </div>
          )}

          <div className="flex gap-1.5">
            <button
              type="button"
              onClick={() => void logout()}
              className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-md border border-border bg-panel px-2 py-1.5 text-xs font-medium text-slate-300 transition-colors hover:text-white hover:border-slate-600"
            >
              <LogOut className="h-3 w-3" />
              Sign out
            </button>
            <button
              type="button"
              onClick={() => void logoutAll()}
              title="Revoke sessions on all devices"
              className="rounded-md border border-border bg-canvas px-2 py-1.5 text-[11px] text-slate-400 transition-colors hover:text-slate-200 hover:border-slate-600"
            >
              All
            </button>
          </div>
        </div>
      </aside>

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="h-12 shrink-0 border-b border-border bg-surface/60 px-6 flex items-center justify-between">
          <p className="text-xs text-slate-400">
            Workspace <span className="text-slate-600">/</span>{" "}
            <span className="text-slate-200 font-medium">Foundation (Phase 1)</span>
          </p>
          <span className="font-mono text-[11px] text-slate-400">API v1</span>
        </header>

        <main className="flex-1 p-6 max-w-6xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
