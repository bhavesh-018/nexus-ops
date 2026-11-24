import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";
import { Plus, SlidersHorizontal, Trash2, X } from "lucide-react";

import { ApiError } from "../api/client";
import {
  createMonitoringConfig,
  createService,
  deleteMonitoringConfig,
  deleteService,
  listMonitoringConfigs,
  listServices,
  updateMonitoringConfig,
  updateService
} from "../api/services";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import type {
  Environment,
  MetricName,
  MonitoringConfig,
  Operator,
  Service,
  Severity,
  Tier
} from "../types/api";

const ENVIRONMENTS: Environment[] = ["production", "staging", "development"];
const TIERS: Tier[] = ["tier1", "tier2", "tier3"];
const METRICS: MetricName[] = [
  "error_rate_percent",
  "latency_p95_ms",
  "cpu_percent",
  "memory_percent",
  "availability_percent",
  "network_in_bytes",
  "network_out_bytes"
];
const OPERATORS: Operator[] = ["gt", "gte", "lt", "lte"];
const SEVERITIES: Severity[] = ["critical", "warning", "info"];

export function ServicesPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [envFilter, setEnvFilter] = useState<string>("all");

  // Service create / edit drawer
  const [serviceDrawerOpen, setServiceDrawerOpen] = useState(false);
  const [editingService, setEditingService] = useState<Service | null>(null);
  const [svcName, setSvcName] = useState("");
  const [svcEnv, setSvcEnv] = useState<Environment>("production");
  const [svcTier, setSvcTier] = useState<Tier>("tier2");
  const [svcHealthUrl, setSvcHealthUrl] = useState("");
  const [svcSaving, setSvcSaving] = useState(false);
  const [svcFormError, setSvcFormError] = useState<string | null>(null);

  // Thresholds drawer
  const [thresholdTarget, setThresholdTarget] = useState<Service | null>(null);
  const [configs, setConfigs] = useState<MonitoringConfig[]>([]);
  const [configsLoading, setConfigsLoading] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);
  const [metricName, setMetricName] = useState<MetricName>("error_rate_percent");
  const [operator, setOperator] = useState<Operator>("gt");
  const [thresholdValue, setThresholdValue] = useState("5");
  const [windowSeconds, setWindowSeconds] = useState("60");
  const [severity, setSeverity] = useState<Severity>("critical");

  const loadServices = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await listServices();
      setServices(list);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load services");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadServices();
  }, [loadServices]);

  const filteredServices = useMemo(() => {
    const q = search.trim().toLowerCase();
    return services.filter((s) => {
      if (envFilter !== "all" && s.environment !== envFilter) return false;
      if (q && !s.name.toLowerCase().includes(q) && !s.slug.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [services, search, envFilter]);

  function openCreateDrawer() {
    setEditingService(null);
    setSvcName("");
    setSvcEnv("production");
    setSvcTier("tier2");
    setSvcHealthUrl("");
    setSvcFormError(null);
    setServiceDrawerOpen(true);
  }

  function openEditDrawer(svc: Service) {
    setEditingService(svc);
    setSvcName(svc.name);
    setSvcEnv(svc.environment);
    setSvcTier(svc.tier);
    setSvcHealthUrl(svc.health_url ?? "");
    setSvcFormError(null);
    setServiceDrawerOpen(true);
  }

  async function handleSaveService(e: FormEvent) {
    e.preventDefault();
    setSvcSaving(true);
    setSvcFormError(null);
    try {
      const payload = {
        name: svcName,
        environment: svcEnv,
        tier: svcTier,
        health_url: svcHealthUrl.trim() ? svcHealthUrl.trim() : null
      };
      if (editingService) {
        await updateService(editingService.id, payload);
      } else {
        await createService(payload);
      }
      setServiceDrawerOpen(false);
      await loadServices();
    } catch (err) {
      setSvcFormError(err instanceof ApiError ? err.message : "Unable to save service");
    } finally {
      setSvcSaving(false);
    }
  }

  async function handleDeleteService(svc: Service) {
    setError(null);
    try {
      await deleteService(svc.id);
      if (thresholdTarget?.id === svc.id) setThresholdTarget(null);
      await loadServices();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to delete service");
    }
  }

  async function openThresholds(svc: Service) {
    setThresholdTarget(svc);
    setConfigsLoading(true);
    setConfigError(null);
    try {
      setConfigs(await listMonitoringConfigs(svc.id));
    } catch (err) {
      setConfigError(err instanceof ApiError ? err.message : "Failed to load rules");
    } finally {
      setConfigsLoading(false);
    }
  }

  async function handleAddConfig(e: FormEvent) {
    e.preventDefault();
    if (!thresholdTarget) return;
    setConfigError(null);
    try {
      const created = await createMonitoringConfig(thresholdTarget.id, {
        metric_name: metricName,
        operator,
        threshold_value: Number(thresholdValue),
        window_seconds: Number(windowSeconds),
        severity,
        enabled: true
      });
      setConfigs((prev) => [...prev, created]);
    } catch (err) {
      setConfigError(err instanceof ApiError ? err.message : "Unable to add threshold rule");
    }
  }

  async function handleToggleConfig(cfg: MonitoringConfig) {
    if (!thresholdTarget) return;
    setConfigError(null);
    try {
      const updated = await updateMonitoringConfig(thresholdTarget.id, cfg.id, {
        enabled: !cfg.enabled
      });
      setConfigs((prev) => prev.map((c) => (c.id === cfg.id ? updated : c)));
    } catch (err) {
      setConfigError(err instanceof ApiError ? err.message : "Unable to update rule");
    }
  }

  async function handleDeleteConfig(cfg: MonitoringConfig) {
    if (!thresholdTarget) return;
    setConfigError(null);
    try {
      await deleteMonitoringConfig(thresholdTarget.id, cfg.id);
      setConfigs((prev) => prev.filter((c) => c.id !== cfg.id));
    } catch (err) {
      setConfigError(err instanceof ApiError ? err.message : "Unable to delete rule");
    }
  }

  return (
    <div className="space-y-5 animate-fade-up">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-100">Services</h1>
          <p className="mt-1 text-sm text-slate-400">
            Register microservices and manage per-metric alert thresholds.
          </p>
        </div>

        {isAdmin && (
          <button
            type="button"
            onClick={openCreateDrawer}
            className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-500"
          >
            <Plus className="h-3.5 w-3.5" />
            Register service
          </button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          type="search"
          aria-label="Search services"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter by name or slug..."
          className="w-64 rounded-md border border-border bg-surface px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
        />

        <select
          aria-label="Filter by environment"
          value={envFilter}
          onChange={(e) => setEnvFilter(e.target.value)}
          className="rounded-md border border-border bg-surface px-3 py-1.5 text-xs text-slate-200 focus:border-blue-500 focus:outline-none"
        >
          <option value="all">All environments</option>
          {ENVIRONMENTS.map((env) => (
            <option key={env} value={env}>
              {env}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-md border border-red-900/60 bg-red-950/40 px-3 py-2 text-xs text-red-300"
        >
          {error}
        </div>
      )}

      <div className="overflow-hidden rounded-lg border border-border bg-surface">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-border bg-panel/60 text-slate-400">
            <tr>
              <th className="px-4 py-2.5 font-medium">Service</th>
              <th className="px-4 py-2.5 font-medium">Environment</th>
              <th className="px-4 py-2.5 font-medium">Tier</th>
              <th className="px-4 py-2.5 font-medium">Status</th>
              <th className="px-4 py-2.5 font-medium">Health URL</th>
              <th className="px-4 py-2.5 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                  Loading services...
                </td>
              </tr>
            ) : filteredServices.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                  No matching services found.
                </td>
              </tr>
            ) : (
              filteredServices.map((svc) => (
                <tr key={svc.id} className="transition-colors hover:bg-panel/40">
                  <td className="px-4 py-3">
                    <p className="font-medium text-slate-100">{svc.name}</p>
                    <p className="font-mono text-[11px] text-slate-500">{svc.slug}</p>
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-300">{svc.environment}</td>
                  <td className="px-4 py-3 font-mono text-slate-400">{svc.tier}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={svc.status} />
                  </td>
                  <td className="px-4 py-3 font-mono text-[11px] text-slate-400">
                    {svc.health_url ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="inline-flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => void openThresholds(svc)}
                        className="inline-flex items-center gap-1 rounded border border-border bg-canvas px-2 py-1 text-[11px] text-slate-300 transition-colors hover:border-slate-600 hover:text-white"
                      >
                        <SlidersHorizontal className="h-3 w-3" />
                        Thresholds
                      </button>
                      {isAdmin && (
                        <>
                          <button
                            type="button"
                            onClick={() => openEditDrawer(svc)}
                            className="rounded border border-border bg-canvas px-2 py-1 text-[11px] text-slate-300 transition-colors hover:border-slate-600 hover:text-white"
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            aria-label={`Delete ${svc.name}`}
                            onClick={() => void handleDeleteService(svc)}
                            className="rounded border border-border bg-canvas p-1 text-slate-400 transition-colors hover:border-red-900/60 hover:text-red-400"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Create / Edit Service Slide-Over Drawer (portaled to body so page transform doesn't clip fixed layout) */}
      {serviceDrawerOpen &&
        createPortal(
          <div className="fixed inset-0 z-40 flex justify-end bg-black/60 animate-backdrop-in">
            <div
              role="dialog"
              aria-modal="true"
              aria-label={editingService ? "Edit service" : "Register service"}
              className="h-full w-full max-w-md border-l border-border bg-surface p-6 flex flex-col justify-between overflow-y-auto animate-drawer-in"
            >
              <div>
                <div className="flex items-center justify-between border-b border-border pb-3">
                  <h2 className="text-sm font-semibold text-slate-100">
                    {editingService ? "Edit service" : "Register service"}
                  </h2>
                  <button
                    type="button"
                    aria-label="Close service drawer"
                    onClick={() => setServiceDrawerOpen(false)}
                    className="rounded p-1 text-slate-400 hover:bg-panel hover:text-slate-200"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>

                <form id="service-form" onSubmit={handleSaveService} className="mt-5 space-y-4">
                  <div>
                    <label htmlFor="svc-name" className="block text-xs font-medium text-slate-300">
                      Service name
                    </label>
                    <input
                      id="svc-name"
                      type="text"
                      required
                      value={svcName}
                      onChange={(e) => setSvcName(e.target.value)}
                      placeholder="payment-service"
                      className="mt-1.5 w-full rounded-md border border-border bg-canvas px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label htmlFor="svc-env" className="block text-xs font-medium text-slate-300">
                        Environment
                      </label>
                      <select
                        id="svc-env"
                        value={svcEnv}
                        onChange={(e) => setSvcEnv(e.target.value as Environment)}
                        className="mt-1.5 w-full rounded-md border border-border bg-canvas px-3 py-2 text-sm text-slate-100 focus:border-blue-500 focus:outline-none"
                      >
                        {ENVIRONMENTS.map((env) => (
                          <option key={env} value={env}>
                            {env}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label htmlFor="svc-tier" className="block text-xs font-medium text-slate-300">
                        Tier
                      </label>
                      <select
                        id="svc-tier"
                        value={svcTier}
                        onChange={(e) => setSvcTier(e.target.value as Tier)}
                        className="mt-1.5 w-full rounded-md border border-border bg-canvas px-3 py-2 text-sm text-slate-100 focus:border-blue-500 focus:outline-none"
                      >
                        {TIERS.map((tier) => (
                          <option key={tier} value={tier}>
                            {tier}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label htmlFor="svc-health" className="block text-xs font-medium text-slate-300">
                      Health URL (optional)
                    </label>
                    <input
                      id="svc-health"
                      type="url"
                      value={svcHealthUrl}
                      onChange={(e) => setSvcHealthUrl(e.target.value)}
                      placeholder="http://payment-service:8080/health"
                      className="mt-1.5 w-full rounded-md border border-border bg-canvas px-3 py-2 text-sm font-mono text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                    />
                  </div>

                  {svcFormError && (
                    <div
                      role="alert"
                      className="rounded-md border border-red-900/60 bg-red-950/40 px-3 py-2 text-xs text-red-300"
                    >
                      {svcFormError}
                    </div>
                  )}
                </form>
              </div>

              <div className="flex justify-end gap-2 border-t border-border pt-4">
                <button
                  type="button"
                  onClick={() => setServiceDrawerOpen(false)}
                  className="rounded-md border border-border bg-canvas px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-panel"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  form="service-form"
                  disabled={svcSaving}
                  className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-500 disabled:opacity-50"
                >
                  {svcSaving ? "Saving..." : editingService ? "Save changes" : "Create service"}
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}

      {/* Monitoring Thresholds Slide-Over Drawer */}
      {thresholdTarget &&
        createPortal(
          <div className="fixed inset-0 z-40 flex justify-end bg-black/60 animate-backdrop-in">
            <div
              role="dialog"
              aria-modal="true"
              aria-label={`Thresholds for ${thresholdTarget.name}`}
              className="h-full w-full max-w-lg border-l border-border bg-surface p-6 overflow-y-auto animate-drawer-in"
            >
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div>
                  <h2 className="text-sm font-semibold text-slate-100">Monitoring Thresholds</h2>
                  <p className="font-mono text-xs text-slate-400">{thresholdTarget.name}</p>
                </div>
                <button
                  type="button"
                  aria-label="Close thresholds drawer"
                  onClick={() => setThresholdTarget(null)}
                  className="rounded p-1 text-slate-400 hover:bg-panel hover:text-slate-200"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {configError && (
                <div
                  role="alert"
                  className="mt-4 rounded-md border border-red-900/60 bg-red-950/40 px-3 py-2 text-xs text-red-300"
                >
                  {configError}
                </div>
              )}

              <div className="mt-4 space-y-2">
                {configsLoading ? (
                  <p className="text-xs text-slate-500">Loading rules...</p>
                ) : configs.length === 0 ? (
                  <p className="rounded-md border border-border bg-canvas px-3 py-4 text-center text-xs text-slate-500">
                    No threshold rules configured for this service.
                  </p>
                ) : (
                  configs.map((cfg) => (
                    <div
                      key={cfg.id}
                      className="flex items-center justify-between rounded-md border border-border bg-canvas px-3 py-2.5 text-xs"
                    >
                      <div>
                        <p className="font-mono text-slate-200">
                          {cfg.metric_name} {cfg.operator} {cfg.threshold_value}
                        </p>
                        <p className="mt-0.5 text-[11px] text-slate-500">
                          window {cfg.window_seconds}s · severity{" "}
                          <span className="text-slate-300">{cfg.severity}</span>
                        </p>
                      </div>
                      {isAdmin && (
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => void handleToggleConfig(cfg)}
                            className={`rounded border px-2 py-0.5 text-[11px] font-medium transition-colors ${
                              cfg.enabled
                                ? "border-emerald-900/70 bg-emerald-950/40 text-emerald-400"
                                : "border-border bg-panel text-slate-400"
                            }`}
                          >
                            {cfg.enabled ? "Enabled" : "Paused"}
                          </button>
                          <button
                            type="button"
                            aria-label={`Delete ${cfg.metric_name} rule`}
                            onClick={() => void handleDeleteConfig(cfg)}
                            className="rounded p-1 text-slate-400 hover:text-red-400"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>

              {isAdmin && (
                <form
                  onSubmit={handleAddConfig}
                  className="mt-6 rounded-md border border-border bg-canvas p-4 space-y-3"
                >
                  <p className="text-xs font-medium text-slate-200">Add alert threshold</p>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label htmlFor="cfg-metric" className="block text-[11px] text-slate-400">
                        Metric
                      </label>
                      <select
                        id="cfg-metric"
                        value={metricName}
                        onChange={(e) => setMetricName(e.target.value as MetricName)}
                        className="mt-1 w-full rounded border border-border bg-surface px-2.5 py-1.5 font-mono text-xs text-slate-100"
                      >
                        {METRICS.map((m) => (
                          <option key={m} value={m}>
                            {m}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label htmlFor="cfg-severity" className="block text-[11px] text-slate-400">
                        Severity
                      </label>
                      <select
                        id="cfg-severity"
                        value={severity}
                        onChange={(e) => setSeverity(e.target.value as Severity)}
                        className="mt-1 w-full rounded border border-border bg-surface px-2.5 py-1.5 text-xs text-slate-100"
                      >
                        {SEVERITIES.map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <label htmlFor="cfg-op" className="block text-[11px] text-slate-400">
                        Operator
                      </label>
                      <select
                        id="cfg-op"
                        value={operator}
                        onChange={(e) => setOperator(e.target.value as Operator)}
                        className="mt-1 w-full rounded border border-border bg-surface px-2.5 py-1.5 font-mono text-xs text-slate-100"
                      >
                        {OPERATORS.map((op) => (
                          <option key={op} value={op}>
                            {op}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label htmlFor="cfg-val" className="block text-[11px] text-slate-400">
                        Threshold
                      </label>
                      <input
                        id="cfg-val"
                        type="number"
                        step="any"
                        required
                        value={thresholdValue}
                        onChange={(e) => setThresholdValue(e.target.value)}
                        className="mt-1 w-full rounded border border-border bg-surface px-2.5 py-1.5 font-mono text-xs text-slate-100"
                      />
                    </div>

                    <div>
                      <label htmlFor="cfg-win" className="block text-[11px] text-slate-400">
                        Window (s)
                      </label>
                      <input
                        id="cfg-win"
                        type="number"
                        min={1}
                        max={86400}
                        required
                        value={windowSeconds}
                        onChange={(e) => setWindowSeconds(e.target.value)}
                        className="mt-1 w-full rounded border border-border bg-surface px-2.5 py-1.5 font-mono text-xs text-slate-100"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    className="w-full rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-500"
                  >
                    Add rule
                  </button>
                </form>
              )}
            </div>
          </div>,
          document.body
        )}
    </div>
  );
}
