import { useEffect, useState } from "react";
import { ArrowRight, Server } from "lucide-react";
import { Link } from "react-router-dom";

import { listAuditLogs } from "../api/audit";
import { ApiError } from "../api/client";
import { listServices } from "../api/services";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import type { AuditLog, Service } from "../types/api";

export function OverviewPage() {
  const { user, loading: authLoading } = useAuth();
  const [services, setServices] = useState<Service[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [svcList, logs] = await Promise.all([
          listServices(),
          user?.role === "admin" ? listAuditLogs(6) : Promise.resolve([])
        ]);
        if (!cancelled) {
          setServices(svcList);
          setAuditLogs(logs);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Failed to load workspace overview");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [authLoading, user?.role]);

  const healthyCount = services.filter((s) => s.status === "healthy").length;
  const unhealthyCount = services.filter((s) => s.status === "degraded" || s.status === "down").length;
  const unknownCount = services.filter((s) => s.status === "unknown").length;

  const stats = [
    { label: "Total Services", value: services.length, note: "Registered in catalog" },
    { label: "Healthy", value: healthyCount, note: "Passing checks" },
    { label: "Degraded / Down", value: unhealthyCount, note: "Requires attention" },
    { label: "Awaiting Telemetry", value: unknownCount, note: "Pending Phase 2 metrics" }
  ];

  return (
    <div className="space-y-6 animate-fade-up">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-100">Overview</h1>
          <p className="mt-1 text-sm text-slate-400">
            Service catalog health and recent control-plane activity.
          </p>
        </div>
        <Link
          to="/services"
          className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:bg-panel"
        >
          Manage services
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-md border border-red-900/60 bg-red-950/40 px-3 py-2 text-xs text-red-300"
        >
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((item) => (
          <div
            key={item.label}
            className="rounded-lg border border-border bg-surface p-4 transition-colors duration-150 hover:border-slate-600"
          >
            <p className="text-xs font-medium text-slate-400">{item.label}</p>
            <p className="mt-2 font-mono text-2xl font-semibold tabular-nums text-slate-100">
              {loading ? "—" : item.value}
            </p>
            <p className="mt-1 text-[11px] text-slate-500">{item.note}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <section className="lg:col-span-2 rounded-lg border border-border bg-surface">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <h2 className="text-sm font-medium text-slate-200">Registered Services</h2>
            <span className="font-mono text-xs tabular-nums text-slate-400">
              {services.length} total
            </span>
          </div>

          {!loading && services.length === 0 ? (
            <div className="px-4 py-10 text-center">
              <Server className="mx-auto h-6 w-6 text-slate-500" />
              <p className="mt-2 text-sm font-medium text-slate-300">No services registered yet</p>
              <p className="mt-1 text-xs text-slate-500">
                Add your first microservice to define environments and alert thresholds.
              </p>
              <Link
                to="/services"
                className="mt-4 inline-flex items-center rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-500"
              >
                Go to Services
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {services.slice(0, 8).map((svc) => (
                <div
                  key={svc.id}
                  className="flex items-center justify-between px-4 py-2.5 text-xs transition-colors hover:bg-panel/60"
                >
                  <div className="min-w-0">
                    <p className="font-medium text-slate-200 truncate">{svc.name}</p>
                    <p className="font-mono text-[11px] text-slate-500">
                      {svc.environment} · {svc.tier}
                    </p>
                  </div>
                  <StatusBadge status={svc.status} />
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-lg border border-border bg-surface">
          <div className="border-b border-border px-4 py-3">
            <h2 className="text-sm font-medium text-slate-200">Audit Activity</h2>
          </div>

          {user?.role !== "admin" ? (
            <div className="px-4 py-8 text-xs text-slate-500">
              Audit log history is restricted to organization admins.
            </div>
          ) : auditLogs.length === 0 ? (
            <div className="px-4 py-8 text-xs text-slate-500">
              {loading ? "Loading activity..." : "No recorded events yet."}
            </div>
          ) : (
            <ul className="divide-y divide-border">
              {auditLogs.map((entry) => (
                <li key={entry.id} className="px-4 py-2.5 text-xs">
                  <p className="font-mono text-slate-200">{entry.action}</p>
                  <p className="mt-0.5 text-[11px] text-slate-500">
                    {entry.resource_type} · {new Date(entry.created_at).toLocaleString()}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
