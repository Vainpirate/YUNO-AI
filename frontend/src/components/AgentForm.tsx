import { useEffect, useState } from "react";
import { Modal } from "./shared/Modal";
import type { Agent, AgentCreate } from "../types";
import { AVAILABLE_TOOLS, AVAILABLE_MODELS, AVAILABLE_CHANNELS } from "../types";

interface Props {
  open: boolean;
  initial?: Agent | null;
  onSave: (data: AgentCreate) => Promise<void>;
  onClose: () => void;
}

const EMPTY: AgentCreate = {
  name: "", role: "", system_prompt: "", model: "gpt-4o-mini",
  tools: [], channels: [], memory_config: {}, guardrails: {},
};

function toggle<T>(arr: T[], item: T): T[] {
  return arr.includes(item) ? arr.filter(x => x !== item) : [...arr, item];
}

export function AgentForm({ open, initial, onSave, onClose }: Props) {
  const [form, setForm] = useState<AgentCreate>(EMPTY);
  const [busy, setBusy] = useState(false);
  const [err,  setErr]  = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setForm(initial
        ? { name: initial.name, role: initial.role ?? "", system_prompt: initial.system_prompt ?? "",
            model: initial.model ?? "gpt-4o-mini", tools: initial.tools, channels: initial.channels,
            memory_config: initial.memory_config, guardrails: initial.guardrails }
        : EMPTY);
      setErr(null);
    }
  }, [open, initial]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr(null);
    try {
      await onSave(form);
      onClose();
    } catch (e: any) {
      setErr(e?.response?.data?.detail ?? "Save failed");
    } finally {
      setBusy(false);
    }
  }

  const set = (k: keyof AgentCreate, v: any) => setForm(f => ({ ...f, [k]: v }));

  return (
    <Modal title={initial ? "Edit Agent" : "New Agent"} open={open} onClose={onClose}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">

        {/* Name + Role */}
        <div className="grid grid-cols-2 gap-3">
          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium text-slate-600">Name *</span>
            <input required value={form.name} onChange={e => set("name", e.target.value)}
              placeholder="Research Agent"
              className="px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium text-slate-600">Role</span>
            <input value={form.role} onChange={e => set("role", e.target.value)}
              placeholder="Web Researcher"
              className="px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
          </label>
        </div>

        {/* System Prompt */}
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-600">System Prompt</span>
          <textarea
            value={form.system_prompt} onChange={e => set("system_prompt", e.target.value)}
            rows={4} placeholder="You are an expert at finding the latest information on the web..."
            className="px-3 py-2 rounded-lg border border-slate-200 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </label>

        {/* Model */}
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-600">Model</span>
          <select value={form.model} onChange={e => set("model", e.target.value)}
            className="px-3 py-2 rounded-lg border border-slate-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-500">
            {AVAILABLE_MODELS.map(m => <option key={m}>{m}</option>)}
          </select>
        </label>

        {/* Tools */}
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-600">Tools</span>
          <div className="flex flex-wrap gap-2">
            {AVAILABLE_TOOLS.map(t => {
              const on = form.tools?.includes(t) ?? false;
              return (
                <button key={t} type="button"
                  onClick={() => set("tools", toggle(form.tools ?? [], t))}
                  className={`px-3 py-1 rounded-full text-xs font-medium border transition
                    ${on ? "bg-brand-500 text-white border-brand-500" : "bg-white text-slate-600 border-slate-200 hover:border-brand-400"}`}>
                  {on ? "✓ " : ""}{t}
                </button>
              );
            })}
          </div>
        </div>

        {/* Channels */}
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-600">Channels</span>
          <div className="flex flex-wrap gap-2">
            {AVAILABLE_CHANNELS.map(c => {
              const on = form.channels?.includes(c) ?? false;
              return (
                <button key={c} type="button"
                  onClick={() => set("channels", toggle(form.channels ?? [], c))}
                  className={`px-3 py-1 rounded-full text-xs font-medium border transition
                    ${on ? "bg-emerald-500 text-white border-emerald-500" : "bg-white text-slate-600 border-slate-200 hover:border-emerald-400"}`}>
                  {on ? "✓ " : ""}{c}
                </button>
              );
            })}
          </div>
        </div>

        {err && <p className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2">{err}</p>}

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
          <button type="button" onClick={onClose}
            className="px-4 py-2 text-sm rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition">
            Cancel
          </button>
          <button type="submit" disabled={busy}
            className="px-4 py-2 text-sm rounded-lg bg-brand-500 text-white hover:bg-brand-600 disabled:opacity-50 transition font-medium">
            {busy ? "Saving…" : initial ? "Update Agent" : "Create Agent"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
