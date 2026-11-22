import type { ServiceStatus } from "../types/api";

const STATUS_STYLES: Record<ServiceStatus, { dot: string; text: string; label: string }> = {
  healthy: { dot: "bg-emerald-500", text: "text-emerald-400", label: "Healthy" },
  degraded: { dot: "bg-amber-500", text: "text-amber-400", label: "Degraded" },
  down: { dot: "bg-rose-500", text: "text-rose-400", label: "Down" },
  unknown: { dot: "bg-slate-500", text: "text-slate-400", label: "No telemetry" }
};

export function StatusBadge({ status }: { status: ServiceStatus }) {
  const style = STATUS_STYLES[status];
  return (
    <span className="inline-flex items-center gap-1.5 rounded border border-border bg-canvas px-2 py-0.5 text-xs font-medium">
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
      <span className={style.text}>{style.label}</span>
    </span>
  );
}
