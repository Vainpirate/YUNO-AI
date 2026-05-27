import { useState } from "react";
import { Pencil, Trash2, Plus, Zap, Bot } from "lucide-react";
import { AgentForm } from "./AgentForm";
import { StatusBadge } from "./shared/StatusBadge";
import { Spinner } from "./shared/Spinner";
import { agentApi } from "../services/api";
import { useAppStore } from "../store";
import type { Agent, AgentCreate } from "../types";

export function AgentList() {
  const { agents, upsertAgent, removeAgent, pushToast } = useAppStore();
  const [formOpen, setFormOpen]   = useState(false);
  const [editing,  setEditing]    = useState<Agent | null>(null);
  const [deleting, setDeleting]   = useState<string | null>(null);

  async function handleSave(data: AgentCreate) {
    if (editing) {
      const updated = await agentApi.update(editing.id, data);
      upsertAgent(updated);
      pushToast(`Agent "${updated.name}" updated`, "success");
    } else {
      const created = await agentApi.create(data);
      upsertAgent(created);
      pushToast(`Agent "${created.name}" created`, "success");
    }
  }

  async function handleDelete(agent: Agent) {
    if (!confirm(`Delete agent "${agent.name}"?`)) return;
    setDeleting(agent.id);
    try {
      await agentApi.remove(agent.id);
      removeAgent(agent.id);
      pushToast(`Agent "${agent.name}" deleted`, "info");
    } finally {
      setDeleting(null);
    }
  }

  return (
    <>
      {/* Toolbar */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold text-slate-800 flex items-center gap-2">
          <Bot size={20} className="text-brand-500" /> Agents
          <span className="ml-1 text-sm font-normal text-slate-400">({agents.length})</span>
        </h1>
        <button
          onClick={() => { setEditing(null); setFormOpen(true); }}
          className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-brand-500 text-white text-sm font-medium hover:bg-brand-600 transition"
        >
          <Plus size={15} /> New Agent
        </button>
      </div>

      {/* Table */}
      {agents.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400 gap-3">
          <Bot size={40} className="opacity-30" />
          <p className="text-sm">No agents yet. Create your first one!</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
              <tr>
                <th className="text-left px-4 py-3 font-medium">Name</th>
                <th className="text-left px-4 py-3 font-medium">Role</th>
                <th className="text-left px-4 py-3 font-medium">Model</th>
                <th className="text-left px-4 py-3 font-medium">Tools</th>
                <th className="text-left px-4 py-3 font-medium">Channels</th>
                <th className="text-left px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {agents.map(agent => (
                <tr key={agent.id} className="hover:bg-slate-50 transition">
                  <td className="px-4 py-3 font-medium text-slate-800 flex items-center gap-2">
                    <span className="w-7 h-7 rounded-full bg-brand-100 flex items-center justify-center text-brand-600 text-xs font-bold shrink-0">
                      {agent.name[0].toUpperCase()}
                    </span>
                    {agent.name}
                  </td>
                  <td className="px-4 py-3 text-slate-500">{agent.role ?? "—"}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-600 text-xs font-mono">
                      {agent.model ?? "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {agent.tools.length ? agent.tools.map(t => (
                        <span key={t} className="px-1.5 py-0.5 bg-purple-50 text-purple-600 rounded text-xs flex items-center gap-0.5">
                          <Zap size={10} />{t}
                        </span>
                      )) : <span className="text-slate-400">—</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {agent.channels.length ? agent.channels.map(c => (
                        <span key={c} className="px-1.5 py-0.5 bg-teal-50 text-teal-600 rounded text-xs">{c}</span>
                      )) : <span className="text-slate-400">—</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3"><StatusBadge status="idle" /></td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 justify-end">
                      <button
                        onClick={() => { setEditing(agent); setFormOpen(true); }}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-brand-600 hover:bg-brand-50 transition"
                        title="Edit"
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        onClick={() => handleDelete(agent)}
                        disabled={deleting === agent.id}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition"
                        title="Delete"
                      >
                        {deleting === agent.id ? <Spinner size={14} /> : <Trash2 size={14} />}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <AgentForm
        open={formOpen}
        initial={editing}
        onSave={handleSave}
        onClose={() => setFormOpen(false)}
      />
    </>
  );
}
