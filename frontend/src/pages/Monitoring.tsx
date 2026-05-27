import { useEffect, useState } from "react";
import { Activity } from "lucide-react";
import { ExecutionMonitor } from "../components/ExecutionMonitor";
import { Spinner } from "../components/shared/Spinner";
import { workflowApi } from "../services/api";
import { useAppStore } from "../store";
import type { Workflow } from "../types";

export function Monitoring() {
  const { workflows, setWorkflows, pushToast } = useAppStore();
  const [selected, setSelected] = useState<Workflow | null>(null);
  const [loading,  setLoading]  = useState(true);

  useEffect(() => {
    workflowApi.list()
      .then(w => { setWorkflows(w); if (w.length) setSelected(w[0]); })
      .catch(() => pushToast("Failed to load workflows", "error"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex-1 flex items-center justify-center"><Spinner size={28} /></div>;

  return (
    <div className="flex h-[calc(100vh-56px)]">
      {/* Sidebar */}
      <aside className="w-56 border-r border-slate-200 bg-white flex flex-col">
        <div className="px-4 py-3 border-b border-slate-100">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Workflows</p>
        </div>
        <div className="overflow-y-auto flex-1 p-2 space-y-1">
          {workflows.length === 0 && (
            <p className="text-xs text-slate-400 text-center py-6">No workflows yet.</p>
          )}
          {workflows.map(wf => (
            <button key={wf.id}
              onClick={() => setSelected(wf)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm border transition
                ${selected?.id === wf.id ? "border-brand-300 bg-brand-50 text-brand-700" : "border-transparent hover:bg-slate-50 text-slate-600"}`}
            >
              <p className="font-medium truncate">{wf.name}</p>
              <p className="text-xs text-slate-400 mt-0.5">{wf.agents.length} agent(s)</p>
            </button>
          ))}
        </div>
      </aside>

      {/* Monitor */}
      <div className="flex-1 overflow-hidden">
        {selected ? (
          <ExecutionMonitor workflowId={selected.id} workflowName={selected.name} />
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-3">
            <Activity size={40} className="opacity-30" />
            <p className="text-sm">Select a workflow to monitor</p>
          </div>
        )}
      </div>
    </div>
  );
}
