import { useCallback, useState } from "react";
import ReactFlow, {
  Background, Controls, MiniMap,
  addEdge, useNodesState, useEdgesState,
  EdgeLabelRenderer, BaseEdge, getBezierPath,
  Handle, Position,
  type Node, type Edge, type Connection, type EdgeProps,
  MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";

import { Play, Save, Trash2, X, Zap, RefreshCw, Clock, ArrowRight, GitBranch, List } from "lucide-react";
import { Spinner } from "./shared/Spinner";
import { workflowApi } from "../services/api";
import { useAppStore } from "../store";
import type { Agent, Workflow, WorkflowCreate } from "../types";

// ─── Custom agent node ────────────────────────────────────────────────────────

function AgentNode({ data }: { data: { label: string; role: string | null; tools: string[] } }) {
  return (
    <div className="bg-white border-2 border-brand-200 rounded-xl shadow-md px-4 py-3 min-w-[150px] max-w-[200px] relative">
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-brand-400 !border-2 !border-white !rounded-full"
      />
      <div className="flex items-center gap-2 mb-1">
        <span className="w-6 h-6 rounded-full bg-brand-100 text-brand-700 text-xs font-bold flex items-center justify-center shrink-0">
          {data.label[0].toUpperCase()}
        </span>
        <span className="font-semibold text-slate-800 text-sm truncate">{data.label}</span>
      </div>
      <p className="text-xs text-slate-500 truncate">{data.role ?? "—"}</p>
      {data.tools.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1.5">
          {data.tools.slice(0, 3).map(t => (
            <span key={t} className="px-1.5 py-0.5 bg-purple-50 text-purple-600 text-[10px] rounded">{t}</span>
          ))}
          {data.tools.length > 3 && (
            <span className="px-1.5 py-0.5 bg-slate-50 text-slate-400 text-[10px] rounded">+{data.tools.length - 3}</span>
          )}
        </div>
      )}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-emerald-400 !border-2 !border-white !rounded-full"
      />
    </div>
  );
}

// ─── Custom conditional edge ──────────────────────────────────────────────────

function ConditionalEdge({
  id, sourceX, sourceY, targetX, targetY,
  sourcePosition, targetPosition, data, markerEnd, style, selected,
}: EdgeProps) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition,
  });

  const condition: string | undefined = data?.condition;
  const isConditional = !!condition;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          ...style,
          stroke: isConditional ? "#f59e0b" : "#6366f1",
          strokeWidth: selected ? 2.5 : 1.5,
          strokeDasharray: isConditional ? "6 3" : undefined,
        }}
      />
      <EdgeLabelRenderer>
        <div
          style={{
            position: "absolute",
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: "all",
          }}
          className="nodrag nopan"
        >
          {isConditional ? (
            <button
              onClick={() => data?.onEdit?.(id)}
              title="Click to edit condition"
              className="flex items-center gap-1 px-2 py-0.5 bg-amber-50 border border-amber-300
                         rounded-full text-[11px] text-amber-700 font-medium cursor-pointer
                         hover:bg-amber-100 shadow-sm select-none transition"
            >
              <Zap size={9} className="shrink-0" />
              <span className="font-mono">if: {condition}</span>
            </button>
          ) : (
            <button
              onClick={() => data?.onEdit?.(id)}
              title="Always fires — click to add a condition"
              className="flex items-center gap-1 px-2 py-0.5 bg-indigo-50 border border-indigo-200
                         rounded-full text-[10px] text-indigo-400 cursor-pointer
                         hover:bg-indigo-100 hover:text-indigo-600 hover:border-indigo-400
                         shadow-sm select-none transition"
            >
              <ArrowRight size={9} />
              always
            </button>
          )}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

const nodeTypes = { agentNode: AgentNode };
const edgeTypes = { conditionalEdge: ConditionalEdge };

// ─── Edge condition modal ─────────────────────────────────────────────────────

const QUICK_CONDITIONS = [
  { label: "approved", color: "emerald" },
  { label: "rejected", color: "red" },
  { label: "yes",      color: "emerald" },
  { label: "no",       color: "red" },
  { label: "error",    color: "red" },
  { label: "success",  color: "emerald" },
  { label: "done",     color: "blue" },
  { label: "retry",    color: "amber" },
] as const;

const CHIP_COLORS: Record<string, string> = {
  emerald: "bg-emerald-50 text-emerald-700 border-emerald-300 hover:bg-emerald-100",
  red:     "bg-red-50 text-red-700 border-red-300 hover:bg-red-100",
  blue:    "bg-blue-50 text-blue-700 border-blue-300 hover:bg-blue-100",
  amber:   "bg-amber-50 text-amber-700 border-amber-300 hover:bg-amber-100",
};

interface EdgeModalProps {
  edgeId: string;
  current: string;
  sourceName: string;
  targetName: string;
  onSave: (edgeId: string, condition: string) => void;
  onClose: () => void;
}

function EdgeConditionModal({ edgeId, current, sourceName, targetName, onSave, onClose }: EdgeModalProps) {
  const [value, setValue] = useState(current);
  const trimmed = value.trim();

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-[420px]" onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-5 pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center">
              <GitBranch size={14} className="text-amber-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-800">Routing Condition</p>
              <p className="text-[11px] text-slate-400">
                {sourceName} <ArrowRight size={10} className="inline" /> {targetName}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition">
            <X size={14} />
          </button>
        </div>

        <div className="px-5 py-4 space-y-4">
          {/* Rule explanation */}
          <div className="bg-slate-50 rounded-xl px-4 py-3 text-xs text-slate-600 leading-relaxed">
            This edge fires when the <span className="font-semibold text-slate-800">previous agent's output</span> contains your keyword.
            Leave it blank to make this edge fire <span className="font-semibold text-slate-800">always</span>.
          </div>

          {/* Input */}
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1.5">
              Condition keyword / phrase
            </label>
            <input
              autoFocus
              value={value}
              onChange={e => setValue(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter") onSave(edgeId, trimmed);
                if (e.key === "Escape") onClose();
              }}
              placeholder='e.g.  approved   or   rejected   or   error'
              className="w-full px-3 py-2.5 rounded-xl border border-slate-200 text-sm font-mono
                         focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-amber-400"
            />
          </div>

          {/* Quick-insert chips */}
          <div>
            <p className="text-[11px] font-medium text-slate-500 mb-2">Quick insert</p>
            <div className="flex flex-wrap gap-1.5">
              {QUICK_CONDITIONS.map(({ label, color }) => (
                <button
                  key={label}
                  type="button"
                  onClick={() => setValue(label)}
                  className={`px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium border transition
                    ${value === label ? "ring-2 ring-offset-1 ring-amber-400" : ""}
                    ${CHIP_COLORS[color]}`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Live preview */}
          <div className={`rounded-xl px-4 py-2.5 text-xs border transition-all ${
            trimmed
              ? "bg-amber-50 border-amber-200 text-amber-800"
              : "bg-indigo-50 border-indigo-200 text-indigo-700"
          }`}>
            {trimmed ? (
              <span>
                <Zap size={10} className="inline mr-1" />
                Route to <strong>{targetName}</strong> when output contains{" "}
                <code className="font-bold bg-amber-100 px-1 rounded">"{trimmed}"</code>
              </span>
            ) : (
              <span>
                <ArrowRight size={10} className="inline mr-1" />
                Always route to <strong>{targetName}</strong> (unconditional)
              </span>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 pb-5">
          <div>
            {current && (
              <button
                onClick={() => onSave(edgeId, "")}
                className="text-xs text-red-500 hover:text-red-700 hover:underline transition"
              >
                Make unconditional
              </button>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-3 py-1.5 text-sm rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition"
            >
              Cancel
            </button>
            <button
              onClick={() => onSave(edgeId, trimmed)}
              className="px-4 py-1.5 text-sm rounded-lg bg-amber-500 text-white hover:bg-amber-600 font-medium transition"
            >
              {trimmed ? "Set condition" : "Set unconditional"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Execute input modal ──────────────────────────────────────────────────────

interface ExecuteModalProps {
  workflowName: string;
  onRun: (input: string) => void;
  onClose: () => void;
  busy: boolean;
}

function ExecuteModal({ workflowName, onRun, onClose, busy }: ExecuteModalProps) {
  const [input, setInput] = useState("");
  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl p-5 w-[480px]" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-slate-800 flex items-center gap-2">
            <Play size={14} className="text-emerald-500" /> Execute — {workflowName}
          </h3>
          <button onClick={onClose} className="p-1 rounded text-slate-400 hover:text-slate-600">
            <X size={14} />
          </button>
        </div>
        <p className="text-xs text-slate-500 mb-3">
          This input is passed to the <strong>first agent</strong> in the workflow.
          Each agent's output becomes the next agent's input.
        </p>
        <textarea
          autoFocus rows={4} value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) onRun(input.trim()); }}
          placeholder="Type your task or message for the first agent…"
          className="w-full px-3 py-2 rounded-xl border border-slate-200 text-sm resize-none
                     focus:outline-none focus:ring-2 focus:ring-brand-500 mb-4"
        />
        <div className="flex justify-end gap-2">
          <button onClick={onClose} disabled={busy}
            className="px-3 py-1.5 text-sm rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50">
            Cancel
          </button>
          <button onClick={() => onRun(input.trim())} disabled={busy}
            className="flex items-center gap-1.5 px-4 py-1.5 text-sm rounded-lg
                       bg-emerald-500 text-white hover:bg-emerald-600 font-medium disabled:opacity-50 transition">
            {busy ? <Spinner size={14} /> : <Play size={14} />}
            {busy ? "Running…" : "Run  (Ctrl+Enter)"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── WorkflowBuilder ─────────────────────────────────────────────────────────

interface Props {
  workflow?: Workflow | null;
  onSaved?: (wf: Workflow) => void;
  onExecuted?: (result: any) => void;
}

export function WorkflowBuilder({ workflow, onSaved, onExecuted }: Props) {
  const { agents, upsertWorkflow, pushToast } = useAppStore();

  const initNodes: Node[] = workflow
    ? workflow.agents.map((id, i) => {
        const a = agents.find(x => x.id === id);
        return {
          id,
          type: "agentNode",
          position: (workflow.graph?.nodes as any)?.[i]?.position ?? { x: 100 + i * 240, y: 200 },
          data: { label: a?.name ?? id, role: a?.role, tools: a?.tools ?? [] },
        };
      })
    : [];

  const initEdges: Edge[] = (workflow?.graph?.edges ?? []).map(([s, t, cond]: any, i: number) => ({
    id: `e${i}`,
    source: s,
    target: t,
    type: "conditionalEdge",
    markerEnd: { type: MarkerType.ArrowClosed },
    data: { condition: cond ?? "" },
  }));

  const [nodes, setNodes, onNodesChange] = useNodesState(initNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initEdges);
  const [name,          setName]          = useState(workflow?.name ?? "");
  const [desc,          setDesc]          = useState(workflow?.description ?? "");
  const [maxIterations, setMaxIterations] = useState(workflow?.max_iterations ?? 10);
  const [schedule,      setSchedule]      = useState(workflow?.schedule ?? "");
  const [sidebarTab,    setSidebarTab]    = useState<"agents" | "routes">("agents");

  const [saving,      setSaving]      = useState(false);
  const [showExecute, setShowExecute] = useState(false);
  const [executing,   setExecuting]   = useState(false);
  const [editingEdge, setEditingEdge] = useState<{ id: string; current: string } | null>(null);

  // ── Helpers ───────────────────────────────────────────────────────────────

  const nodeName = (id: string) =>
    nodes.find(n => n.id === id)?.data?.label ?? id.slice(0, 8);

  const onConnect = useCallback(
    (params: Connection) =>
      setEdges(es =>
        addEdge({
          ...params,
          type: "conditionalEdge",
          markerEnd: { type: MarkerType.ArrowClosed },
          data: { condition: "", onEdit: openEdgeModal },
        }, es),
      ),
    [setEdges],
  );

  function openEdgeModal(edgeId: string) {
    const edge = edges.find(e => e.id === edgeId);
    setEditingEdge({ id: edgeId, current: edge?.data?.condition ?? "" });
  }

  function saveEdgeCondition(edgeId: string, condition: string) {
    setEdges(es =>
      es.map(e =>
        e.id === edgeId
          ? { ...e, data: { ...e.data, condition, onEdit: openEdgeModal } }
          : e,
      ),
    );
    setEditingEdge(null);
  }

  function addAgentNode(agent: Agent) {
    if (nodes.find(n => n.id === agent.id)) {
      pushToast(`${agent.name} is already on the canvas`, "info");
      return;
    }
    setNodes(ns => [
      ...ns,
      {
        id: agent.id,
        type: "agentNode",
        position: { x: 80 + ns.length * 230, y: 180 },
        data: { label: agent.name, role: agent.role, tools: agent.tools },
      },
    ]);
  }

  function removeSelected() {
    setNodes(ns => ns.filter(n => !n.selected));
    setEdges(es => es.filter(e => !e.selected));
  }

  function buildPayload(): WorkflowCreate {
    const nodeIds = nodes.map(n => n.id);
    const edgePairs = edges.map(e =>
      e.data?.condition ? [e.source, e.target, e.data.condition] : [e.source, e.target],
    ) as [string, string][];
    return {
      name:           name || "Untitled Workflow",
      description:    desc,
      agents:         nodeIds,
      graph:          { nodes: nodeIds, edges: edgePairs },
      max_iterations: maxIterations,
      schedule:       schedule.trim() || undefined,
      template_name:  workflow?.template_name ?? null,
    } as any;
  }

  function hasCycles(): boolean {
    const adj: Map<string, string[]> = new Map();
    nodes.forEach(n => adj.set(n.id, []));
    edges.forEach(e => adj.get(e.source)?.push(e.target));
    const visited = new Set<string>();
    const stack = new Set<string>();
    function dfs(id: string): boolean {
      if (stack.has(id)) return true;
      if (visited.has(id)) return false;
      visited.add(id); stack.add(id);
      for (const nb of adj.get(id) || []) { if (dfs(nb)) return true; }
      stack.delete(id);
      return false;
    }
    return nodes.some(n => dfs(n.id));
  }

  async function handleSave() {
    if (!name.trim()) { pushToast("Give the workflow a name first", "error"); return; }
    setSaving(true);
    try {
      const payload = buildPayload();
      const saved = workflow
        ? await workflowApi.update(workflow.id, payload)
        : await workflowApi.create(payload);
      upsertWorkflow(saved);
      pushToast(`Workflow "${saved.name}" saved`, "success");
      onSaved?.(saved);
    } catch (e: any) {
      pushToast(e?.response?.data?.detail ?? "Save failed", "error");
    } finally {
      setSaving(false);
    }
  }

  async function handleExecute(input: string) {
    if (!workflow) return;
    setExecuting(true);
    try {
      const result = await workflowApi.execute(workflow.id, input || undefined);
      pushToast(`Workflow completed — ${result.steps} step(s)`, "success");
      setShowExecute(false);
      onExecuted?.(result);
    } catch (e: any) {
      pushToast(e?.response?.data?.detail ?? "Execution failed", "error");
    } finally {
      setExecuting(false);
    }
  }

  const edgesWithHandlers: Edge[] = edges.map(e => ({
    ...e,
    data: { ...e.data, onEdit: openEdgeModal },
  }));

  const conditionalCount = edges.filter(e => e.data?.condition).length;
  const cycles = hasCycles();

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-full gap-0">

      {/* ── Sidebar ──────────────────────────────────────────────────── */}
      <aside className="w-56 border-r border-slate-200 bg-white flex flex-col">

        {/* Tab bar */}
        <div className="flex border-b border-slate-100">
          <button
            onClick={() => setSidebarTab("agents")}
            className={`flex-1 py-2.5 text-xs font-medium flex items-center justify-center gap-1.5 transition border-b-2
              ${sidebarTab === "agents"
                ? "border-brand-500 text-brand-700 bg-brand-50"
                : "border-transparent text-slate-500 hover:text-slate-700"}`}
          >
            <List size={12} /> Agents
          </button>
          <button
            onClick={() => setSidebarTab("routes")}
            className={`flex-1 py-2.5 text-xs font-medium flex items-center justify-center gap-1.5 transition border-b-2 relative
              ${sidebarTab === "routes"
                ? "border-amber-500 text-amber-700 bg-amber-50"
                : "border-transparent text-slate-500 hover:text-slate-700"}`}
          >
            <GitBranch size={12} /> Routes
            {conditionalCount > 0 && (
              <span className="absolute top-1.5 right-2 w-4 h-4 rounded-full bg-amber-500 text-white text-[9px] flex items-center justify-center font-bold">
                {conditionalCount}
              </span>
            )}
          </button>
        </div>

        {/* Agents tab */}
        {sidebarTab === "agents" && (
          <>
            <div className="px-4 py-2 border-b border-slate-100">
              <p className="text-[11px] text-slate-400">Click to add to canvas</p>
            </div>
            <div className="overflow-y-auto flex-1 p-2 flex flex-col gap-1.5">
              {agents.length === 0 && (
                <p className="text-xs text-slate-400 px-2 py-4 text-center">
                  No agents yet.<br />Create one in the Agents page first.
                </p>
              )}
              {agents.map(a => (
                <button
                  key={a.id}
                  onClick={() => addAgentNode(a)}
                  className={`w-full text-left px-3 py-2 rounded-lg border text-sm transition
                    ${nodes.find(n => n.id === a.id)
                      ? "border-brand-300 bg-brand-50 text-brand-700"
                      : "border-slate-200 hover:border-brand-300 hover:bg-brand-50 text-slate-700"}`}
                >
                  <p className="font-medium truncate">{a.name}</p>
                  <p className="text-xs text-slate-400 truncate mt-0.5">{a.role ?? "No role"}</p>
                  {nodes.find(n => n.id === a.id) && (
                    <p className="text-[10px] text-brand-500 mt-0.5">On canvas</p>
                  )}
                </button>
              ))}
            </div>
            <div className="p-3 border-t border-slate-100 bg-slate-50 text-[11px] text-slate-500 space-y-1">
              <p className="font-semibold text-slate-600">How to connect</p>
              <p>Hover a node → drag from the dot to another node</p>
              <p>Click any edge label to set a condition</p>
            </div>
          </>
        )}

        {/* Routes tab */}
        {sidebarTab === "routes" && (
          <>
            <div className="px-4 py-2 border-b border-slate-100">
              <p className="text-[11px] text-slate-400">{edges.length} connection{edges.length !== 1 ? "s" : ""} · {conditionalCount} conditional</p>
            </div>
            <div className="overflow-y-auto flex-1 p-2 flex flex-col gap-1.5">
              {edges.length === 0 && (
                <p className="text-xs text-slate-400 px-2 py-4 text-center">
                  No connections yet.<br />Drag from a node handle to connect agents.
                </p>
              )}
              {edges.map(e => {
                const isConditional = !!e.data?.condition;
                return (
                  <button
                    key={e.id}
                    onClick={() => openEdgeModal(e.id)}
                    className={`w-full text-left px-3 py-2 rounded-lg border text-xs transition group
                      ${isConditional
                        ? "border-amber-200 bg-amber-50 hover:border-amber-400"
                        : "border-slate-200 bg-white hover:border-indigo-300 hover:bg-indigo-50"}`}
                  >
                    <div className="flex items-center gap-1.5 mb-1 font-medium text-slate-700 truncate">
                      <span className="truncate">{nodeName(e.source)}</span>
                      <ArrowRight size={10} className="shrink-0 text-slate-400" />
                      <span className="truncate">{nodeName(e.target)}</span>
                    </div>
                    {isConditional ? (
                      <span className="flex items-center gap-1 text-amber-700">
                        <Zap size={9} />
                        <code className="font-mono">if: {e.data.condition}</code>
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-indigo-400">
                        <ArrowRight size={9} />
                        always fires
                      </span>
                    )}
                    <span className="text-[10px] text-slate-400 group-hover:text-slate-600 mt-0.5 block">
                      Click to edit
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Legend */}
            <div className="p-3 border-t border-slate-100 bg-slate-50 space-y-1.5 text-[11px]">
              <div className="flex items-center gap-2">
                <div className="w-8 h-0.5 bg-indigo-400 rounded" />
                <span className="text-slate-500">Unconditional (always fires)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-8 h-0.5 border-t-2 border-dashed border-amber-400" />
                <span className="text-slate-500">Conditional (keyword match)</span>
              </div>
            </div>
          </>
        )}
      </aside>

      {/* ── Main canvas ──────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col">

        {/* Toolbar */}
        <div className="flex items-center gap-2 px-4 py-2.5 border-b border-slate-200 bg-white flex-wrap">
          <input
            value={name} onChange={e => setName(e.target.value)}
            placeholder="Workflow name…"
            className="flex-1 min-w-[120px] px-3 py-1.5 rounded-lg border border-slate-200 text-sm
                       focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <input
            value={desc} onChange={e => setDesc(e.target.value)}
            placeholder="Description (optional)"
            className="w-40 px-3 py-1.5 rounded-lg border border-slate-200 text-sm
                       focus:outline-none focus:ring-2 focus:ring-brand-500"
          />

          {/* Cron */}
          <div className="flex items-center gap-1" title="Cron schedule (e.g. 0 9 * * 1-5)">
            <Clock size={12} className="text-slate-400 shrink-0" />
            <input
              value={schedule} onChange={e => setSchedule(e.target.value)}
              placeholder="Cron…"
              className="w-28 px-2 py-1.5 rounded-lg border border-slate-200 text-xs font-mono
                         focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          {/* Max iterations */}
          <div className="flex items-center gap-1" title="Max loop iterations (loop safety)">
            <RefreshCw size={12} className="text-slate-400 shrink-0" />
            <input
              type="number" min={1} max={100} value={maxIterations}
              onChange={e => setMaxIterations(parseInt(e.target.value) || 10)}
              className="w-12 px-2 py-1.5 rounded-lg border border-slate-200 text-xs text-center
                         focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          {/* Cycle badge */}
          {cycles && (
            <span className="flex items-center gap-1 px-2 py-1 rounded-full bg-amber-50 border border-amber-300
                             text-[11px] text-amber-700 font-medium shrink-0">
              <RefreshCw size={9} /> Loop
            </span>
          )}

          <div className="flex items-center gap-2 ml-auto">
            <button onClick={removeSelected}
              className="p-1.5 rounded-lg border border-slate-200 text-slate-500
                         hover:text-red-600 hover:border-red-200 hover:bg-red-50 transition"
              title="Remove selected (Delete key)">
              <Trash2 size={14} />
            </button>
            <button onClick={handleSave} disabled={saving}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200
                         text-slate-700 text-sm hover:bg-slate-50 transition disabled:opacity-50">
              {saving ? <Spinner size={13} /> : <Save size={14} />} Save
            </button>
            <button
              onClick={() => { if (!workflow) { pushToast("Save the workflow first", "info"); return; } setShowExecute(true); }}
              disabled={executing || !workflow}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 text-white
                         text-sm font-medium hover:bg-emerald-600 transition disabled:opacity-50">
              {executing ? <Spinner size={13} /> : <Play size={14} />} Execute
            </button>
          </div>
        </div>

        {/* Canvas */}
        <div className="flex-1 bg-slate-50">
          <ReactFlow
            nodes={nodes}
            edges={edgesWithHandlers}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            fitView
            deleteKeyCode="Delete"
            defaultEdgeOptions={{ type: "conditionalEdge", markerEnd: { type: MarkerType.ArrowClosed } }}
          >
            <Background color="#cbd5e1" gap={16} size={1} />
            <Controls />
            <MiniMap nodeColor={() => "#6366f1"} maskColor="rgba(248,250,252,0.7)" />
          </ReactFlow>
        </div>

        {/* Status bar */}
        <div className="px-4 py-1.5 border-t border-slate-100 bg-white text-[11px] text-slate-400 flex items-center gap-4 flex-wrap">
          <span>{nodes.length} agent{nodes.length !== 1 ? "s" : ""} · {edges.length} connection{edges.length !== 1 ? "s" : ""}</span>
          {conditionalCount > 0 && (
            <span className="text-amber-500 flex items-center gap-1">
              <Zap size={9} /> {conditionalCount} conditional route{conditionalCount !== 1 ? "s" : ""}
            </span>
          )}
          {cycles && (
            <span className="text-amber-600 flex items-center gap-1">
              <RefreshCw size={9} /> Loop detected — max {maxIterations} iterations per node
            </span>
          )}
          <span className="ml-auto">Drag handles to connect · Click edge label to edit · Delete key to remove</span>
        </div>
      </div>

      {/* ── Edge condition modal ─────────────────────────────────────── */}
      {editingEdge && (() => {
        const e = edges.find(x => x.id === editingEdge.id);
        return (
          <EdgeConditionModal
            edgeId={editingEdge.id}
            current={editingEdge.current}
            sourceName={e ? nodeName(e.source) : "Source"}
            targetName={e ? nodeName(e.target) : "Target"}
            onSave={saveEdgeCondition}
            onClose={() => setEditingEdge(null)}
          />
        );
      })()}

      {/* ── Execute modal ────────────────────────────────────────────── */}
      {showExecute && workflow && (
        <ExecuteModal
          workflowName={workflow.name}
          onRun={handleExecute}
          onClose={() => { if (!executing) setShowExecute(false); }}
          busy={executing}
        />
      )}
    </div>
  );
}
