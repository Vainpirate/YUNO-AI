type Status = "success" | "running" | "error" | "idle" | "completed" | "unknown" | string;

const styles: Record<string, string> = {
  success:   "bg-emerald-100 text-emerald-700",
  completed: "bg-emerald-100 text-emerald-700",
  running:   "bg-blue-100    text-blue-700 animate-pulse",
  error:     "bg-red-100     text-red-700",
  idle:      "bg-slate-100   text-slate-600",
  unknown:   "bg-slate-100   text-slate-500",
};

export function StatusBadge({ status }: { status: Status }) {
  const cls = styles[status] ?? styles.unknown;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {status}
    </span>
  );
}
