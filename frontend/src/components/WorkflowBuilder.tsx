import { useCallback, useState } from "react";
import ReactFlow, {
  Background, Controls, MiniMap,
  addEdge, useNodesState, useEdgesState,
  EdgeLabelRenderer, BaseEdge, getBezierPath,
  type Node, type Edge, type Connection, type EdgeProps,
  MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";

import { Play, Save, Trash2, GitMerge, X, Zap } from "lucide-react";
import { Spinner } from "./shared/Spinner";
import { workflowApi } from "../services/api";
import { useAppStore } from "../store";
import type { Agent, Workflow, WorkflowCreate } from "../types";

// ─── Custom agent node ────────────────────────────────────────────────────────

function AgentNode({ data }: { data: { label: string; role: string | null; tools: string[] } }) {
  return (
    <div className="bg-white border-2 border-brand-200 rounded-xl shadow-md px-4 py-3 min-w-[150px] max-w-[200px]">
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
          stroke: isConditional ? "#f59e0b" : "#4f6ef7",
          strokeWidth: selected ? 2.5 : 1.5,
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
            <div
              onClick={() => data?.onEdit?.(id)}
              title="Click to edit condition"
              className="flex items-center gap-1 px-2 py-0.5 bg-amber-50 border border-amber-300
                         rounded-full text-[11px] text-amber-700 font-medium cursor-pointer
                         hover:bg-amber-100 shadow-sm select-none"
            >
              <Zap size={9} />
              {condition}
            </div>
          ) : (
            <div
              onClick={() => data?.onEdit?.(id)}
              title="Click to add condition"
              className="flex items-center justify-center w-5 h-5 rounded-full
                         bg-white border border-slate-300 text-slate-400
                         cursor-pointer hover:border-brand-400 hover:text-brand-500
                         hover:bg-brand-50 shadow-sm opacity-0 group-hover:opacity-100
                         transition select-none"
            >
              <GitMerge size={9} />
            </div>
          )}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

const nodeTypes = { agentNode: AgentNode };
const edgeTypes = { conditionalEdge: ConditionalEdge };

// ─── Edge condition modal ─────────────────────────────────────────────────────

interface EdgeModalProps {
  edgeId: string;
  current: string;
  onSave: (edgeId: string, condition: string) => void;
  onClose: () => void;
}

function EdgeConditionModal({ edgeId, current, onSave, onClose }: EdgeModalProps) {
  const [value, setValue] = useState(current);
  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl p-5 w-80" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-slate-800 flex items-center gap-2">
            <Zap size={14} className="text-amber-500" /> Edge Condition
          </h3>
          <button onClick={onClose} className="p-1 rounded text-slate-400 hover:text-slate-600">
            <X size={14} />
          </button>
        </div>

        <p className="text-xs text-slate-500 mb-3">
          If the <strong>previous agent's output</strong> contains this keyword/phrase,
          follow this edge. Leave blank for an unconditional (always-on) connection.
        </p>

        <input
          autoFocus
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") onSave(edgeId, value.trim()); if (e.key === "Escape") onClose(); }}
          placeholder='e.g.  "approved"  or  "yes"  or  "error"'
          className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm
                     focus:outline-none focus:ring-2 focus:ring-brand-500 mb-4"
        />

        <div className="text-[11px] text-slate-400 bg-slate-50 rounded-lg px-3 py-2 mb-4 space-y-1">
          <p className="font-medium text-slate-600">Examples</p>
          <p><span className="text-amber-600 font-mono">approved</span> — route here when output contains "approved"</p>
          <p><span className="text-red-500 font-mono">rejected</span> — route here when output contains "rejected"</p>
          <p><em>(blank)</em> — always follow this edge (default path)</p>
        </div>

        <div className="flex justify-end gap-2">
          <button onClick={onClose}
            className="px-3 py-1.5 text-sm rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50">
            Cancel
          </button>
          {current && (
            <button onClick={() => onSave(edgeId, "")}
              className="px-3 py-1.5 text-sm rounded-lg border border-red-200 text-red-600 hover:bg-red-50">
              Remove condition
            </button>
          )}
          <button onClick={() => onSave(edgeId, value.trim())}
            className="px-3 py-1.5 text-sm rounded-lg bg-brand-500 text-white hover:bg-brand-600 font-medium">
            Save
          </button>
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
      <div className="bg-white rounded-xl shadow-xl p-5 w-[480px]" onClick={e => e.stopPropagation()}>
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
          autoFocus
          rows={4}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) onRun(input.trim()); }}
          placeholder="Type your task or message for the first agent…"
          className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm resize-none
                     focus:outline-none focus:ring-2 focus:ring-brand-500 mb-4"
        />

        <div className="flex justify-end gap-2">
          <button onClick={onClose} disabled={busy}
            className="px-3 py-1.5 text-sm rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50">
            Cancel
          </button>
          <button
            onClick={() => onRun(input.trim())}
            disabled={busy}
            className="flex items-center gap-1.5 px-4 py-1.5 text-sm rounded-lg
                       bg-emerald-500 text-white hover:bg-emerald-600 font-medium
                       disabled:opacity-50 transition"
          >
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

  // ── Initialise canvas from existing workflow ──────────────────────────────
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
  const [name,  setName]  = useState(workflow?.name ?? "");
  const [desc,  setDesc]  = useState(workflow?.description ?? "");

  const [saving,      setSaving]      = useState(false);
  const [showExecute, setShowExecute] = useState(false);
  const [executing,   setExecuting]   = useState(false);

  // Edge condition modal state
  const [editingEdge, setEditingEdge] = useState<{ id: string; current: string } | null>(null);

  // ── Handlers ─────────────────────────────────────────────────────────────

  const onConnect = useCallback(
    (params: Connection) =>
      setEdges(es =>
        addEdge(
          {
            ...params,
            type: "conditionalEdge",
            markerEnd: { type: MarkerType.ArrowClosed },
            data: { condition: "", onEdit: openEdgeModal },
          },
          es,
        ),
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
        id:   agent.id,
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
    // Store edges as [src, dst] or [src, dst, condition] triples
    const edgePairs = edges.map(e =>
      e.data?.condition
        ? [e.source, e.target, e.data.condition]
        : [e.source, e.target],
    ) as [string, string][];

    return {
      name:          name || "Untitled Workflow",
      description:   desc,
      agents:        nodeIds,
      graph:         { nodes: nodeIds, edges: edgePairs },
      template_name: workflow?.template_name ?? null,
    } as any;
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

  // Inject onEdit callback into every edge's data so the handler always has
  // the latest closure (edges state captured by onConnect would be stale).
  const edgesWithHandlers: Edge[] = edges.map(e => ({
    ...e,
    data: { ...e.data, onEdit: openEdgeModal },
  }));

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-full gap-0">
      {/* ── Sidebar — agent palette ─────────────────────────────────────── */}
      <aside className="w-56 border-r border-slate-200 bg-white flex flex-col">
        <div className="px-4 py-3 border-b border-slate-100">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Agents</p>
          <p className="text-xs text-slate-400 mt-0.5">Click to add to canvas</p>
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

        {/* ── Connection guide ────────────────────────────────────── */}
        <div className="p-3 border-t border-slate-100 bg-slate-50 text-[11px] text-slate-500 space-y-1.5">
          <p className="font-semibold text-slate-600">How to connect</p>
          <p>1. Hover a node — dots appear on the edges</p>
          <p>2. Drag from a dot to another node</p>
          <p>3. Click the <span className="text-amber-600 font-medium">⚡ label</span> on any arrow to add a condition</p>
          <p className="pt-1 text-[10px] text-slate-400">Conditional arrows only fire when the previous agent's output contains your keyword.</p>
        </div>
      </aside>

      {/* ── Main canvas ──────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
        <div className="flex items-center gap-3 px-4 py-2.5 border-b border-slate-200 bg-white">
          <input
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="Workflow name…"
            className="flex-1 px-3 py-1.5 rounded-lg border border-slate-200 text-sm
                       focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <input
            value={desc}
            onChange={e => setDesc(e.target.value)}
            placeholder="Description (optional)"
            className="w-52 px-3 py-1.5 rounded-lg border border-slate-200 text-sm
                       focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <button
            onClick={removeSelected}
            className="p-2 rounded-lg border border-slate-200 text-slate-500
                       hover:text-red-600 hover:border-red-200 hover:bg-red-50 transition"
            title="Remove selected node/edge (or press Delete key)"
          >
            <Trash2 size={15} />
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200
                       text-slate-700 text-sm hover:bg-slate-50 transition disabled:opacity-50"
          >
            {saving ? <Spinner size={14} /> : <Save size={15} />} Save
          </button>
          <button
            onClick={() => { if (!workflow) { pushToast("Save the workflow first", "info"); return; } setShowExecute(true); }}
            disabled={executing || !workflow}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 text-white
                       text-sm font-medium hover:bg-emerald-600 transition disabled:opacity-50"
          >
            {executing ? <Spinner size={14} /> : <Play size={15} />} Execute
          </button>
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
            <MiniMap nodeColor={() => "#4f6ef7"} maskColor="rgba(248,250,252,0.7)" />
          </ReactFlow>
        </div>

        {/* Hint bar */}
        <div className="px-4 py-1.5 border-t border-slate-100 bg-white text-[11px] text-slate-400 flex gap-4">
          <span>Click agent → add to canvas · Drag node handles to connect agents</span>
          <span className="text-amber-500">⚡ Click any arrow label to add/edit a condition</span>
          <span>Select + Delete key to remove</span>
        </div>
      </div>

      {/* ── Edge condition modal ─────────────────────────────────────────── */}
      {editingEdge && (
        <EdgeConditionModal
          edgeId={editingEdge.id}
          current={editingEdge.current}
          onSave={saveEdgeCondition}
          onClose={() => setEditingEdge(null)}
        />
      )}

      {/* ── Execute input modal ──────────────────────────────────────────── */}
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
