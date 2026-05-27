import { useEffect, useRef, useState } from "react";
import { Activity, RefreshCw, Trash2, Wifi, WifiOff, Circle } from "lucide-react";
import { Spinner } from "./shared/Spinner";
import { StatusBadge } from "./shared/StatusBadge";
import { executionApi } from "../services/api";
import { useWebSocket } from "../hooks/useWebSocket";
import type { ExecutionLog } from "../types";

interface Props {
  workflowId: string;
  workflowName?: string;
}

function fmt(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function LogRow({ log }: { log: ExecutionLog }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-slate-100 last:border-0">
      <button
        onClick={() => setOpen(x => !x)}
        className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50 text-left transition"
      >
        <Circle size={8} className={
          log.status === "success" ? "text-emerald-400 fill-emerald-400"
          : log.status === "error" ? "text-red-400 fill-red-400"
          : "text-blue-400 fill-blue-400 animate-pulse"
        } />
        <span className="text-xs text-slate-400 font-mono w-20 shrink-0">{fmt(log.created_at)}</span>
        <span className="text-xs font-medium text-slate-700 flex-1">{log.step_name}</span>
        <StatusBadge status={log.status} />
        {log.tokens_used != null && (
          <span className="text-xs text-slate-400">{log.tokens_used} tok</span>
        )}
      </button>
      {open && (
        <div className="px-4 pb-3 space-y-2">
          {log.input && (
            <pre className="text-xs bg-slate-50 rounded-lg p-3 overflow-x-auto text-slate-600 border border-slate-100">
              {JSON.stringify(log.input, null, 2)}
            </pre>
          )}
          {log.output && (
            <pre className="text-xs bg-emerald-50 rounded-lg p-3 overflow-x-auto text-emerald-800 border border-emerald-100">
              {JSON.stringify(log.output, null, 2)}
            </pre>
          )}
          {log.error && (
            <pre className="text-xs bg-red-50 rounded-lg p-3 text-red-700 border border-red-100">{log.error}</pre>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Live event feed (WebSocket) ─────────────────────────────────────────────

function LiveFeed({ workflowId }: { workflowId: string }) {
  const { events, status, clear } = useWebSocket(`/ws/logs/${workflowId}`);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  const wsIcon = status === "connected"
    ? <Wifi size={12} className="text-emerald-500" />
    : status === "connecting"
    ? <Spinner size={12} />
    : <WifiOff size={12} className="text-slate-400" />;

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-100 bg-white">
        <span className="text-xs font-semibold text-slate-600 flex items-center gap-1.5">
          {wsIcon} Live Stream
          <span className="text-slate-400 font-normal">({status})</span>
        </span>
        <button onClick={clear} className="p-1 rounded text-slate-400 hover:text-red-500">
          <Trash2 size={12} />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2 font-mono text-xs bg-slate-950">
        {events.length === 0 && (
          <p className="text-slate-500 text-center py-6">Waiting for events…</p>
        )}
        {events.map((ev, i) => {
          const e = ev as any;
          const ts = e.timestamp ? fmt(e.timestamp) : "";
          const event = e.event ?? "status";
          return (
            <div key={i} className="flex gap-2">
              <span className="text-slate-600 shrink-0">{ts}</span>
              <span className={`shrink-0 font-bold ${
                event === "workflow_completed" ? "text-emerald-400"
                : event === "workflow_started"  ? "text-brand-400"
                : event === "agent_response"    ? "text-yellow-400"
                : "text-slate-400"
              }`}>[{event}]</span>
              <span className="text-slate-300 break-all">
                {e.agent ? `${e.agent}: ` : ""}{e.response ?? e.final_output ?? e.workflow_name ?? JSON.stringify(ev)}
              </span>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

// ─── Main ExecutionMonitor ────────────────────────────────────────────────────

export function ExecutionMonitor({ workflowId, workflowName }: Props) {
  const [logs,    setLogs]    = useState<ExecutionLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [tab,     setTab]     = useState<"logs" | "live">("live");

  async function loadLogs() {
    setLoading(true);
    try { setLogs(await executionApi.logs(workflowId)); }
    finally { setLoading(false); }
  }

  useEffect(() => { loadLogs(); }, [workflowId]);

  const totalTokens = logs.reduce((s, l) => s + (l.tokens_used ?? 0), 0);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-200 bg-white">
        <Activity size={15} className="text-brand-500" />
        <span className="text-sm font-semibold text-slate-700 flex-1">
          {workflowName ?? "Execution Monitor"}
        </span>
        <span className="text-xs text-slate-400">{logs.length} steps • {totalTokens} tokens</span>
        <button onClick={loadLogs} disabled={loading}
          className="p-1.5 rounded-lg text-slate-400 hover:text-brand-600 hover:bg-brand-50 transition">
          {loading ? <Spinner size={14} /> : <RefreshCw size={14} />}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 bg-white px-4">
        {(["live", "logs"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition
              ${tab === t ? "border-brand-500 text-brand-600" : "border-transparent text-slate-500 hover:text-slate-700"}`}>
            {t === "live" ? "Live Stream" : `Execution Logs (${logs.length})`}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {tab === "live" && <LiveFeed workflowId={workflowId} />}
        {tab === "logs" && (
          <div className="h-full overflow-y-auto bg-white">
            {loading && logs.length === 0 && (
              <div className="flex justify-center py-12"><Spinner /></div>
            )}
            {!loading && logs.length === 0 && (
              <div className="flex flex-col items-center py-12 text-slate-400 gap-2">
                <Activity size={32} className="opacity-30" />
                <p className="text-sm">No execution logs yet.</p>
              </div>
            )}
            {logs.map(l => <LogRow key={l.id} log={l} />)}
          </div>
        )}
      </div>
    </div>
  );
}
