import { useEffect, useState } from "react";
import { MessageSquare, RefreshCw, ChevronDown, ChevronUp, Wrench } from "lucide-react";
import { Spinner } from "./shared/Spinner";
import { messageApi } from "../services/api";
import type { Message } from "../types";
import { useAppStore } from "../store";

interface Props {
  workflowId: string;
  agentMap: Record<string, string>; // id → name
}

function fmt(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function MessageCard({ msg, agentMap }: { msg: Message; agentMap: Record<string, string> }) {
  const [expanded, setExpanded] = useState(false);
  const fromName = msg.from_agent_id ? (agentMap[msg.from_agent_id] ?? msg.from_agent_id.slice(0, 8)) : "User";
  const toName   = msg.to_agent_id   ? (agentMap[msg.to_agent_id]   ?? msg.to_agent_id.slice(0, 8))   : null;
  const toolOuts = (msg.metadata?.tool_outputs as any[]) ?? [];

  return (
    <div className="flex gap-3">
      {/* Avatar */}
      <div className="flex flex-col items-center">
        <span className="w-8 h-8 rounded-full bg-brand-100 text-brand-700 text-xs font-bold flex items-center justify-center shrink-0">
          {fromName[0].toUpperCase()}
        </span>
        <div className="flex-1 w-px bg-slate-200 mt-1" />
      </div>

      {/* Content */}
      <div className="flex-1 pb-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium text-slate-800">{fromName}</span>
          {toName && (
            <>
              <span className="text-slate-300">→</span>
              <span className="text-sm font-medium text-emerald-700">{toName}</span>
            </>
          )}
          <span className="ml-auto text-xs text-slate-400">{fmt(msg.created_at)}</span>
          <span className="px-2 py-0.5 bg-slate-100 text-slate-500 text-xs rounded-full">{msg.channel}</span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-700 shadow-sm">
          {msg.content}
        </div>

        {/* Tool outputs */}
        {toolOuts.length > 0 && (
          <div className="mt-1.5">
            <button
              onClick={() => setExpanded(x => !x)}
              className="flex items-center gap-1 text-xs text-purple-600 hover:text-purple-800"
            >
              <Wrench size={12} /> {toolOuts.length} tool call(s)
              {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
            {expanded && (
              <div className="mt-1 space-y-1">
                {toolOuts.map((t: any, i: number) => (
                  <div key={i} className="bg-purple-50 border border-purple-100 rounded-lg px-3 py-2 text-xs font-mono text-purple-800">
                    <span className="font-bold">{t.tool}:</span> {t.result}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function MessageHistory({ workflowId, agentMap }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading,  setLoading]  = useState(false);
  const { pushToast } = useAppStore();

  async function load() {
    setLoading(true);
    try {
      const data = await messageApi.list(workflowId);
      setMessages(data);
    } catch {
      pushToast("Could not load messages", "error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [workflowId]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-white">
        <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
          <MessageSquare size={15} className="text-brand-500" />
          Message History
          <span className="text-xs text-slate-400 font-normal">({messages.length})</span>
        </h3>
        <button onClick={load} disabled={loading}
          className="p-1.5 rounded-lg text-slate-400 hover:text-brand-600 hover:bg-brand-50 transition">
          {loading ? <Spinner size={14} /> : <RefreshCw size={14} />}
        </button>
      </div>

      {/* Timeline */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {loading && messages.length === 0 && (
          <div className="flex justify-center py-12"><Spinner /></div>
        )}
        {!loading && messages.length === 0 && (
          <div className="flex flex-col items-center py-12 text-slate-400 gap-2">
            <MessageSquare size={32} className="opacity-30" />
            <p className="text-sm">No messages yet. Execute the workflow first.</p>
          </div>
        )}
        {messages.map(m => (
          <MessageCard key={m.id} msg={m} agentMap={agentMap} />
        ))}
      </div>
    </div>
  );
}
