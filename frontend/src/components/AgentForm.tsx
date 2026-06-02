import { useEffect, useState } from "react";
import { Modal } from "./shared/Modal";
import { Plus, X } from "lucide-react";
import type { Agent, AgentCreate, AgentSkill } from "../types";
import { AVAILABLE_TOOLS, GROQ_MODELS, GEMINI_MODELS, AVAILABLE_CHANNELS } from "../types";

interface Props {
  open: boolean;
  initial?: Agent | null;
  onSave: (data: AgentCreate) => Promise<void>;
  onClose: () => void;
}

type Tab = "basic" | "guardrails" | "memory" | "skills" | "rules";

const EMPTY: AgentCreate = {
  name: "", role: "", system_prompt: "", model: "llama-3.3-70b-versatile",
  tools: [], channels: [],
  memory_config: { window_size: 20, memory_type: "sliding_window" },
  guardrails: { banned_keywords: [], blocked_topics: [], require_safe_response: false },
  skills: [],
  interaction_rules: { response_format: "text", language: "", temperature: 0.7, max_turns: 10 },
};

function toggle<T>(arr: T[], item: T): T[] {
  return arr.includes(item) ? arr.filter(x => x !== item) : [...arr, item];
}

export function AgentForm({ open, initial, onSave, onClose }: Props) {
  const [form, setForm] = useState<AgentCreate>(EMPTY);
  const [tab, setTab] = useState<Tab>("basic");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // Keyword input state for guardrails
  const [kwInput, setKwInput] = useState("");
  const [topicInput, setTopicInput] = useState("");

  // Skill form state
  const [skillName, setSkillName] = useState("");
  const [skillDesc, setSkillDesc] = useState("");

  useEffect(() => {
    if (open) {
      setForm(initial
        ? {
            name: initial.name, role: initial.role ?? "", system_prompt: initial.system_prompt ?? "",
            model: initial.model ?? "gemini-3-flash-preview", tools: initial.tools, channels: initial.channels,
            memory_config: { window_size: 20, memory_type: "sliding_window", ...(initial.memory_config || {}) },
            guardrails: { banned_keywords: [], blocked_topics: [], require_safe_response: false, ...(initial.guardrails || {}) },
            skills: initial.skills || [],
            interaction_rules: { response_format: "text", language: "", temperature: 0.7, max_turns: 10, ...(initial.interaction_rules || {}) },
          }
        : EMPTY);
      setTab("basic");
      setErr(null);
      setKwInput(""); setTopicInput("");
      setSkillName(""); setSkillDesc("");
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
      setTab("basic");
    } finally {
      setBusy(false);
    }
  }

  const set = (k: keyof AgentCreate, v: any) => setForm(f => ({ ...f, [k]: v }));
  const setGuardrail = (k: string, v: any) =>
    setForm(f => ({ ...f, guardrails: { ...(f.guardrails || {}), [k]: v } }));
  const setMemory = (k: string, v: any) =>
    setForm(f => ({ ...f, memory_config: { ...(f.memory_config || {}), [k]: v } }));
  const setRules = (k: string, v: any) =>
    setForm(f => ({ ...f, interaction_rules: { ...(f.interaction_rules || {}), [k]: v } }));

  function addKeyword() {
    const kw = kwInput.trim().toLowerCase();
    if (!kw) return;
    const existing = (form.guardrails?.banned_keywords || []) as string[];
    if (!existing.includes(kw)) setGuardrail("banned_keywords", [...existing, kw]);
    setKwInput("");
  }

  function removeKeyword(kw: string) {
    setGuardrail("banned_keywords", ((form.guardrails?.banned_keywords || []) as string[]).filter(k => k !== kw));
  }

  function addTopic() {
    const t = topicInput.trim().toLowerCase();
    if (!t) return;
    const existing = (form.guardrails?.blocked_topics || []) as string[];
    if (!existing.includes(t)) setGuardrail("blocked_topics", [...existing, t]);
    setTopicInput("");
  }

  function removeTopic(t: string) {
    setGuardrail("blocked_topics", ((form.guardrails?.blocked_topics || []) as string[]).filter(x => x !== t));
  }

  function addSkill() {
    if (!skillName.trim()) return;
    const skill: AgentSkill = { name: skillName.trim(), description: skillDesc.trim(), enabled: true };
    set("skills", [...(form.skills || []), skill]);
    setSkillName(""); setSkillDesc("");
  }

  function removeSkill(idx: number) {
    set("skills", (form.skills || []).filter((_, i) => i !== idx));
  }

  function toggleSkill(idx: number) {
    set("skills", (form.skills || []).map((s, i) => i === idx ? { ...s, enabled: !s.enabled } : s));
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: "basic", label: "Basic" },
    { id: "guardrails", label: "Guardrails" },
    { id: "memory", label: "Memory" },
    { id: "skills", label: "Skills" },
    { id: "rules", label: "Rules" },
  ];

  return (
    <Modal title={initial ? "Edit Agent" : "New Agent"} open={open} onClose={onClose}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-0">

        {/* Tab bar */}
        <div className="flex gap-0 border-b border-slate-200 mb-4 -mx-1">
          {tabs.map(t => (
            <button
              key={t.id} type="button"
              onClick={() => setTab(t.id)}
              className={`px-4 py-2 text-xs font-medium border-b-2 transition -mb-px
                ${tab === t.id
                  ? "border-brand-500 text-brand-700 bg-brand-50"
                  : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"}`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* ── Basic ── */}
        {tab === "basic" && (
          <div className="flex flex-col gap-4">
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
            <label className="flex flex-col gap-1">
              <span className="text-xs font-medium text-slate-600">System Prompt</span>
              <textarea
                value={form.system_prompt} onChange={e => set("system_prompt", e.target.value)}
                rows={4} placeholder="You are an expert at finding the latest information on the web..."
                className="px-3 py-2 rounded-lg border border-slate-200 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs font-medium text-slate-600">Model</span>
              <select value={form.model} onChange={e => set("model", e.target.value)}
                className="px-3 py-2 rounded-lg border border-slate-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-500">
                <optgroup label="Groq (fast — recommended)">
                  {GROQ_MODELS.map(m => <option key={m} value={m}>{m}</option>)}
                </optgroup>
                <optgroup label="Gemini (fallback)">
                  {GEMINI_MODELS.map(m => <option key={m} value={m}>{m}</option>)}
                </optgroup>
              </select>
            </label>
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
          </div>
        )}

        {/* ── Guardrails ── */}
        {tab === "guardrails" && (
          <div className="flex flex-col gap-4">
            <p className="text-xs text-slate-500 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              Guardrails are enforced at runtime — inputs and outputs that violate these rules will be blocked.
            </p>

            {/* Banned keywords */}
            <div className="flex flex-col gap-2">
              <span className="text-xs font-medium text-slate-600">Banned Keywords</span>
              <p className="text-xs text-slate-400">Agent will refuse to process inputs or produce outputs containing these words.</p>
              <div className="flex gap-2">
                <input value={kwInput} onChange={e => setKwInput(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addKeyword(); } }}
                  placeholder="e.g. violence, hate"
                  className="flex-1 px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
                <button type="button" onClick={addKeyword}
                  className="px-3 py-2 rounded-lg bg-red-500 text-white text-xs font-medium hover:bg-red-600 transition">
                  Add
                </button>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {((form.guardrails?.banned_keywords || []) as string[]).map(kw => (
                  <span key={kw} className="flex items-center gap-1 px-2 py-0.5 bg-red-50 border border-red-200 rounded-full text-xs text-red-700">
                    {kw}
                    <button type="button" onClick={() => removeKeyword(kw)} className="hover:text-red-900">
                      <X size={10} />
                    </button>
                  </span>
                ))}
              </div>
            </div>

            {/* Blocked topics */}
            <div className="flex flex-col gap-2">
              <span className="text-xs font-medium text-slate-600">Blocked Topics</span>
              <p className="text-xs text-slate-400">Block entire topic areas (e.g. gambling, weapons).</p>
              <div className="flex gap-2">
                <input value={topicInput} onChange={e => setTopicInput(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addTopic(); } }}
                  placeholder="e.g. gambling, nsfw"
                  className="flex-1 px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
                <button type="button" onClick={addTopic}
                  className="px-3 py-2 rounded-lg bg-orange-500 text-white text-xs font-medium hover:bg-orange-600 transition">
                  Add
                </button>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {((form.guardrails?.blocked_topics || []) as string[]).map(t => (
                  <span key={t} className="flex items-center gap-1 px-2 py-0.5 bg-orange-50 border border-orange-200 rounded-full text-xs text-orange-700">
                    {t}
                    <button type="button" onClick={() => removeTopic(t)} className="hover:text-orange-900">
                      <X size={10} />
                    </button>
                  </span>
                ))}
              </div>
            </div>

            {/* Token caps */}
            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-1">
                <span className="text-xs font-medium text-slate-600">Max Input Tokens</span>
                <input type="number" min={1}
                  value={(form.guardrails?.max_input_tokens as number) ?? ""}
                  onChange={e => setGuardrail("max_input_tokens", e.target.value ? parseInt(e.target.value) : undefined)}
                  placeholder="No limit"
                  className="px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-xs font-medium text-slate-600">Max Output Tokens</span>
                <input type="number" min={1}
                  value={(form.guardrails?.max_output_tokens as number) ?? ""}
                  onChange={e => setGuardrail("max_output_tokens", e.target.value ? parseInt(e.target.value) : undefined)}
                  placeholder="No limit"
                  className="px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
              </label>
            </div>

            {/* Safe response toggle */}
            <label className="flex items-center gap-3 cursor-pointer">
              <input type="checkbox"
                checked={!!(form.guardrails?.require_safe_response)}
                onChange={e => setGuardrail("require_safe_response", e.target.checked)}
                className="w-4 h-4 accent-red-500" />
              <span className="text-xs text-slate-700">Require safe response (hard-block any guardrail violation)</span>
            </label>
          </div>
        )}

        {/* ── Memory ── */}
        {tab === "memory" && (
          <div className="flex flex-col gap-4">
            <p className="text-xs text-slate-500 bg-blue-50 border border-blue-200 rounded-lg px-3 py-2">
              Memory settings control how much conversation history this agent retains between turns.
            </p>
            <label className="flex flex-col gap-1">
              <span className="text-xs font-medium text-slate-600">Memory Type</span>
              <select
                value={(form.memory_config?.memory_type as string) || "sliding_window"}
                onChange={e => setMemory("memory_type", e.target.value)}
                className="px-3 py-2 rounded-lg border border-slate-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-500">
                <option value="sliding_window">Sliding Window</option>
                <option value="full">Full History</option>
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs font-medium text-slate-600">Window Size (messages)</span>
              <p className="text-xs text-slate-400">Number of individual messages to keep in context. Default: 20.</p>
              <input type="number" min={2} max={200}
                value={(form.memory_config?.window_size as number) ?? 20}
                onChange={e => setMemory("window_size", parseInt(e.target.value) || 20)}
                className="px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
            </label>
          </div>
        )}

        {/* ── Skills ── */}
        {tab === "skills" && (
          <div className="flex flex-col gap-4">
            <p className="text-xs text-slate-500 bg-purple-50 border border-purple-200 rounded-lg px-3 py-2">
              Skills are capabilities declared to the agent — they extend the system prompt so the LLM knows it can exhibit these behaviours.
            </p>
            <div className="flex flex-col gap-2">
              <span className="text-xs font-medium text-slate-600">Add Skill</span>
              <div className="flex gap-2">
                <input value={skillName} onChange={e => setSkillName(e.target.value)}
                  placeholder="Skill name (e.g. summarize)"
                  className="flex-1 px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
              </div>
              <div className="flex gap-2">
                <input value={skillDesc} onChange={e => setSkillDesc(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addSkill(); } }}
                  placeholder="Description (e.g. Summarizes long text into key points)"
                  className="flex-1 px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
                <button type="button" onClick={addSkill}
                  className="flex items-center gap-1 px-3 py-2 rounded-lg bg-purple-500 text-white text-xs font-medium hover:bg-purple-600 transition">
                  <Plus size={12} /> Add
                </button>
              </div>
            </div>
            <div className="flex flex-col gap-2">
              {(form.skills || []).length === 0 && (
                <p className="text-xs text-slate-400 text-center py-4">No skills added yet.</p>
              )}
              {(form.skills || []).map((skill, i) => (
                <div key={i} className={`flex items-start gap-3 px-3 py-2.5 rounded-lg border transition
                  ${skill.enabled ? "border-purple-200 bg-purple-50" : "border-slate-200 bg-slate-50 opacity-60"}`}>
                  <input type="checkbox" checked={skill.enabled}
                    onChange={() => toggleSkill(i)}
                    className="mt-0.5 w-3.5 h-3.5 accent-purple-500 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-slate-700 truncate">{skill.name}</p>
                    {skill.description && (
                      <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{skill.description}</p>
                    )}
                  </div>
                  <button type="button" onClick={() => removeSkill(i)}
                    className="text-slate-400 hover:text-red-500 shrink-0 transition">
                    <X size={13} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Interaction Rules ── */}
        {tab === "rules" && (
          <div className="flex flex-col gap-4">
            <p className="text-xs text-slate-500 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">
              Interaction rules control how the agent formats responses and behaves during conversations.
            </p>
            <label className="flex flex-col gap-1">
              <span className="text-xs font-medium text-slate-600">Response Format</span>
              <select
                value={(form.interaction_rules?.response_format as string) || "text"}
                onChange={e => setRules("response_format", e.target.value)}
                className="px-3 py-2 rounded-lg border border-slate-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-500">
                <option value="text">Plain Text</option>
                <option value="json">JSON</option>
                <option value="markdown">Markdown</option>
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs font-medium text-slate-600">Language</span>
              <input
                value={(form.interaction_rules?.language as string) || ""}
                onChange={e => setRules("language", e.target.value)}
                placeholder="e.g. Spanish, French (leave blank for default)"
                className="px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs font-medium text-slate-600">Temperature ({(form.interaction_rules?.temperature as number) ?? 0.7})</span>
              <p className="text-xs text-slate-400">Controls creativity/randomness. 0 = deterministic, 1 = creative.</p>
              <input type="range" min={0} max={1} step={0.05}
                value={(form.interaction_rules?.temperature as number) ?? 0.7}
                onChange={e => setRules("temperature", parseFloat(e.target.value))}
                className="w-full accent-emerald-500" />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs font-medium text-slate-600">Max Turns</span>
              <p className="text-xs text-slate-400">Maximum conversation turns stored in memory.</p>
              <input type="number" min={1} max={100}
                value={(form.interaction_rules?.max_turns as number) ?? 10}
                onChange={e => setRules("max_turns", parseInt(e.target.value) || 10)}
                className="px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
            </label>
          </div>
        )}

        {err && <p className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2 mt-2">{err}</p>}

        <div className="flex justify-end gap-2 pt-3 mt-3 border-t border-slate-100">
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
