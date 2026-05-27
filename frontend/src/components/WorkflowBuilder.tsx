import { useCallback, useState } from "react";
import ReactFlow, {
  Background, Controls, MiniMap,
  addEdge, useNodesState, useEdgesState,
  type Node, type Edge, type Connection,
  MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";

import { Play, Save, Trash2 } from "lucide-react";
import { Spinner } from "./shared/Spinner";
import { workflowApi } from "../services/api";
import { useAppStore } from "../store";
import type { Agent, Workflow, WorkflowCreate } from "../types";

// ─── Custom node ─────────────────────────────────────────────────────────────

function AgentNode({ data }: { data: { label: string; role: string | null; tools: string[] } }) {
  return (
    <div className="bg-white border-2 border-brand-200 rounded-xl shadow-md px-4 py-3 min-w-[140px]">
      <div className="flex items-center gap-2 mb-1">
        <span className="w-6 h-6 rounded-full bg-brand-100 text-brand-700 text-xs font-bold flex items-center justify-center shrink-0">
          {data.label[0].toUpperCase()}
        </span>
        <span className="font-semibold text-slate-800 text-sm truncate">{data.label}</span>
      </div>
      <p className="text-xs text-slate-500 truncate">{data.role ?? "—"}</p>
      {data.tools.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1.5">
          {data.tools.map(t => (
            <span key={t} className="px-1.5 py-0.5 bg-purple-50 text-purple-600 text-[10px] rounded">{t}</span>
          ))}
        </div>
      )}
    </div>
  );
}

const nodeTypes = { agentNode: AgentNode };

// ─── WorkflowBuilder ─────────────────────────────────────────────────────────

interface Props {
  workflow?: Workflow | null;
  onSaved?: (wf: Workflow) => void;
  onExecuted?: (result: any) => void;
}


export function WorkflowBuilder({ workflow, onSaved, onExecuted }: Props) {
  const { agents, upsertWorkflow, pushToast } = useAppStore();

  // Initialise from existing workflow, or blank canvas
  const initNodes: Node[] = workflow
    ? workflow.agents.map((id, i) => {
        const a = agents.find(x => x.id === id);
        return {
          id,
          type: "agentNode",
          position: (workflow.graph?.nodes as any)?.[i]?.position ?? { x: 100 + i * 220, y: 200 },
          data: { label: a?.name ?? id, role: a?.role, tools: a?.tools ?? [] },
        };
      })
    : [];

  const initEdges: Edge[] = (workflow?.graph?.edges ?? []).map(([s, t], i) => ({
    id: `e${i}`, source: s, target: t,
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: "#4f6ef7" },
  }));

  const [nodes, setNodes, onNodesChange] = useNodesState(initNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initEdges);
  const [name,  setName]  = useState(workflow?.name ?? "");
  const [desc,  setDesc]  = useState(workflow?.description ?? "");
  const [saving,    setSaving]    = useState(false);
  const [executing, setExecuting] = useState(false);

  const onConnect = useCallback(
    (params: Connection) => setEdges(es =>
      addEdge({ ...params, markerEnd: { type: MarkerType.ArrowClosed }, style: { stroke: "#4f6ef7" } }, es)),
    [setEdges],
  );

  // Drag agent from sidebar onto canvas
  function addAgentNode(agent: Agent) {
    const already = nodes.find(n => n.id === agent.id);
    if (already) { pushToast(`${agent.name} is already on the canvas`, "info"); return; }
    const newNode: Node = {
      id:   agent.id,
      type: "agentNode",
      position: { x: 100 + nodes.length * 200, y: 200 },
      data: { label: agent.name, role: agent.role, tools: agent.tools },
    };
    setNodes(ns => [...ns, newNode]);
  }

  function removeSelected() {
    setNodes(ns => ns.filter(n => !n.selected));
    setEdges(es => es.filter(e => !e.selected));
  }

  function buildPayload(): WorkflowCreate {
    const nodeIds = nodes.map(n => n.id);
    const edgePairs: [string, string][] = edges.map(e => [e.source, e.target]);
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

  async function handleExecute() {
    if (!workflow) { pushToast("Save the workflow first", "info"); return; }
    setExecuting(true);
    try {
      const result = await workflowApi.execute(workflow.id);
      pushToast(`Workflow completed — ${result.steps} step(s)`, "success");
      onExecuted?.(result);
    } catch (e: any) {
      pushToast(e?.response?.data?.detail ?? "Execution failed", "error");
    } finally {
      setExecuting(false);
    }
  }

  return (
    <div className="flex h-full gap-0">
      {/* Sidebar — agent palette */}
      <aside className="w-56 border-r border-slate-200 bg-white flex flex-col">
        <div className="px-4 py-3 border-b border-slate-100">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Agents</p>
          <p className="text-xs text-slate-400 mt-0.5">Click to add to canvas</p>
        </div>
        <div className="overflow-y-auto flex-1 p-2 flex flex-col gap-1.5">
          {agents.length === 0 && (
            <p className="text-xs text-slate-400 px-2 py-4 text-center">No agents yet.<br/>Create one first.</p>
          )}
          {agents.map(a => (
            <button key={a.id} onClick={() => addAgentNode(a)}
              className={`w-full text-left px-3 py-2 rounded-lg border text-sm transition
                ${nodes.find(n => n.id === a.id)
                  ? "border-brand-300 bg-brand-50 text-brand-700"
                  : "border-slate-200 hover:border-brand-300 hover:bg-brand-50 text-slate-700"}`}>
              <p className="font-medium truncate">{a.name}</p>
              <p className="text-xs text-slate-400 truncate mt-0.5">{a.role ?? "No role"}</p>
            </button>
          ))}
        </div>
      </aside>

      {/* Main canvas area */}
      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
        <div className="flex items-center gap-3 px-4 py-2.5 border-b border-slate-200 bg-white">
          <input
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="Workflow name…"
            className="flex-1 px-3 py-1.5 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <input
            value={desc}
            onChange={e => setDesc(e.target.value)}
            placeholder="Description (optional)"
            className="w-56 px-3 py-1.5 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <button onClick={removeSelected}
            className="p-2 rounded-lg border border-slate-200 text-slate-500 hover:text-red-600 hover:border-red-200 hover:bg-red-50 transition"
            title="Remove selected node/edge">
            <Trash2 size={15} />
          </button>
          <button onClick={handleSave} disabled={saving}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-slate-700 text-sm hover:bg-slate-50 transition disabled:opacity-50">
            {saving ? <Spinner size={14} /> : <Save size={15} />} Save
          </button>
          <button onClick={handleExecute} disabled={executing || !workflow}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 text-white text-sm font-medium hover:bg-emerald-600 transition disabled:opacity-50">
            {executing ? <Spinner size={14} /> : <Play size={15} />} Execute
          </button>
        </div>

        {/* React Flow canvas */}
        <div className="flex-1 bg-slate-50">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            fitView
            defaultEdgeOptions={{ markerEnd: { type: MarkerType.ArrowClosed } }}
          >
            <Background color="#cbd5e1" gap={16} size={1} />
            <Controls />
            <MiniMap nodeColor={() => "#4f6ef7"} maskColor="rgba(248,250,252,0.7)" />
          </ReactFlow>
        </div>

        {/* Hint bar */}
        <div className="px-4 py-2 border-t border-slate-100 bg-white text-xs text-slate-400 flex gap-4">
          <span>Click agent in sidebar to add • Drag nodes to reposition</span>
          <span>Draw arrow between nodes to connect • Select + Delete key to remove</span>
        </div>
      </div>
    </div>
  );
}
