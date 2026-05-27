import { useEffect, useState } from "react";
import { Plus, GitBranch, ChevronRight } from "lucide-react";
import { WorkflowBuilder } from "../components/WorkflowBuilder";
import { MessageHistory } from "../components/MessageHistory";
import { ExecutionMonitor } from "../components/ExecutionMonitor";
import { Spinner } from "../components/shared/Spinner";
import { agentApi, workflowApi } from "../services/api";
import { useAppStore } from "../store";
import type { Workflow } from "../types";

type Panel = "builder" | "messages" | "monitor";

export function WorkflowStudio() {
  const { agents, setAgents, workflows, setWorkflows, pushToast } = useAppStore();
  const [selected, setSelected] = useState<Workflow | null>(null);
  const [panel,    setPanel]    = useState<Panel>("builder");
  const [loading,  setLoading]  = useState(true);

  useEffect(() => {
    Promise.all([agentApi.list(), workflowApi.list()])
      .then(([a, w]) => { setAgents(a); setWorkflows(w); })
      .catch(() => pushToast("Failed to load data", "error"))
      .finally(() => setLoading(false));
  }, []);

  const agentMap = Object.fromEntries(agents.map(a => [a.id, a.name]));

  if (loading) return (
    <div className="flex-1 flex items-center justify-center"><Spinner size={28} /></div>
  );

  return (
    <div className="flex h-[calc(100vh-56px)]">
      {/* Left: workflow list */}
      <aside className="w-60 border-r border-slate-200 bg-white flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Workflows</span>
          <button
            onClick={() => { setSelected(null); setPanel("builder"); }}
            className="p-1 rounded-lg text-slate-400 hover:text-brand-600 hover:bg-brand-50 transition"
            title="New workflow"
          >
            <Plus size={14} />
          </button>
        </div>
        <div className="overflow-y-auto flex-1 p-2 space-y-1">
          <button
            onClick={() => { setSelected(null); setPanel("builder"); }}
            className={`w-full text-left px-3 py-2 rounded-lg text-sm border transition
              ${!selected ? "border-brand-300 bg-brand-50 text-brand-700" : "border-transparent hover:bg-slate-50 text-slate-600"}`}
          >
            <div className="flex items-center gap-2">
              <Plus size={13} /> New Workflow
            </div>
          </button>
          {workflows.map(wf => (
            <button key={wf.id}
              onClick={() => { setSelected(wf); setPanel("builder"); }}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm border transition
                ${selected?.id === wf.id ? "border-brand-300 bg-brand-50 text-brand-700" : "border-transparent hover:bg-slate-50 text-slate-600"}`}
            >
              <div className="flex items-center gap-2">
                <GitBranch size={13} className="shrink-0" />
                <span className="truncate font-medium">{wf.name}</span>
                <ChevronRight size={12} className="ml-auto shrink-0 opacity-50" />
              </div>
              <p className="text-xs text-slate-400 mt-0.5 ml-5 truncate">{wf.agents.length} agent(s)</p>
            </button>
          ))}
        </div>
      </aside>

      {/* Right: builder + panels */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Panel tabs (only show when workflow selected) */}
        {selected && (
          <div className="flex items-center gap-0 border-b border-slate-200 bg-white px-4 py-0">
            {(["builder", "messages", "monitor"] as Panel[]).map(p => (
              <button key={p}
                onClick={() => setPanel(p)}
                className={`px-4 py-2.5 text-sm font-medium border-b-2 transition capitalize
                  ${panel === p ? "border-brand-500 text-brand-600" : "border-transparent text-slate-500 hover:text-slate-700"}`}
              >
                {p === "messages" ? "Message History" : p === "monitor" ? "Live Monitor" : "Workflow Builder"}
              </button>
            ))}
          </div>
        )}

        {/* Panel content */}
        <div className="flex-1 overflow-hidden">
          {panel === "builder" && (
            <WorkflowBuilder
              workflow={selected}
              onSaved={(wf) => { setSelected(wf); }}
              onExecuted={() => { setPanel("monitor"); }}
            />
          )}
          {panel === "messages" && selected && (
            <MessageHistory workflowId={selected.id} agentMap={agentMap} />
          )}
          {panel === "monitor" && selected && (
            <ExecutionMonitor workflowId={selected.id} workflowName={selected.name} />
          )}
        </div>
      </div>
    </div>
  );
}
