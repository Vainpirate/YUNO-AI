import { useEffect } from "react";
import { Link } from "react-router-dom";
import { Bot, GitBranch, MessageSquare, Activity, ArrowRight, CheckCircle } from "lucide-react";
import { agentApi, workflowApi, healthApi } from "../services/api";
import { useAppStore } from "../store";
import { Spinner } from "../components/shared/Spinner";
import { useState } from "react";

interface Health { status: string }

export function Dashboard() {
  const { agents, workflows, setAgents, setWorkflows, pushToast } = useAppStore();
  const [health, setHealth] = useState<Health | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [a, w, h] = await Promise.all([
          agentApi.list(),
          workflowApi.list(),
          healthApi.check(),
        ]);
        setAgents(a);
        setWorkflows(w);
        setHealth(h);
      } catch {
        pushToast("Cannot reach backend. Is it running on :8000?", "error");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const stats = [
    { label: "Agents",    value: agents.length,    icon: <Bot size={20} className="text-brand-500" />,    to: "/agents" },
    { label: "Workflows", value: workflows.length,  icon: <GitBranch size={20} className="text-emerald-500" />, to: "/workflows" },
    { label: "Messages",  value: "—",               icon: <MessageSquare size={20} className="text-violet-500" />, to: "/workflows" },
    { label: "Monitor",   value: "Live",             icon: <Activity size={20} className="text-amber-500" />, to: "/monitor" },
  ];

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Hero */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">YUNO AI Platform</h1>
          <p className="text-slate-500 text-sm mt-1">Multi-agent orchestration · Built with LangGraph + FastAPI</p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          {loading ? <Spinner size={16} /> : health ? (
            <span className="flex items-center gap-1.5 text-emerald-600 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-full">
              <CheckCircle size={13} /> API online
            </span>
          ) : (
            <span className="text-red-500 bg-red-50 border border-red-200 px-3 py-1.5 rounded-full text-xs">API offline</span>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {stats.map(s => (
          <Link key={s.label} to={s.to}
            className="bg-white rounded-2xl border border-slate-200 p-4 hover:shadow-md hover:border-brand-200 transition group">
            <div className="flex items-center justify-between mb-3">
              <div className="p-2 bg-slate-50 rounded-xl group-hover:bg-brand-50 transition">{s.icon}</div>
              <ArrowRight size={14} className="text-slate-300 group-hover:text-brand-400 transition" />
            </div>
            <p className="text-2xl font-bold text-slate-800">{s.value}</p>
            <p className="text-xs text-slate-500 mt-0.5">{s.label}</p>
          </Link>
        ))}
      </div>

      {/* Quick actions */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5">
        <h2 className="text-sm font-semibold text-slate-700 mb-4">Quick Start</h2>
        <div className="grid grid-cols-3 gap-3">
          <Link to="/agents"
            className="flex flex-col gap-2 p-4 rounded-xl border border-dashed border-slate-200 hover:border-brand-300 hover:bg-brand-50 transition group">
            <Bot size={18} className="text-brand-500" />
            <p className="text-sm font-medium text-slate-700">1. Create an Agent</p>
            <p className="text-xs text-slate-400">Configure role, prompt, tools and channels</p>
          </Link>
          <Link to="/workflows"
            className="flex flex-col gap-2 p-4 rounded-xl border border-dashed border-slate-200 hover:border-emerald-300 hover:bg-emerald-50 transition group">
            <GitBranch size={18} className="text-emerald-500" />
            <p className="text-sm font-medium text-slate-700">2. Build a Workflow</p>
            <p className="text-xs text-slate-400">Drag agents onto the canvas and connect them</p>
          </Link>
          <Link to="/monitor"
            className="flex flex-col gap-2 p-4 rounded-xl border border-dashed border-slate-200 hover:border-amber-300 hover:bg-amber-50 transition group">
            <Activity size={18} className="text-amber-500" />
            <p className="text-sm font-medium text-slate-700">3. Monitor Execution</p>
            <p className="text-xs text-slate-400">Watch live logs, messages, and token usage</p>
          </Link>
        </div>
      </div>

      {/* Recent agents */}
      {agents.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-700">Recent Agents</h2>
            <Link to="/agents" className="text-xs text-brand-500 hover:underline">View all</Link>
          </div>
          <div className="flex flex-wrap gap-2">
            {agents.slice(0, 6).map(a => (
              <span key={a.id} className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700">
                <span className="w-5 h-5 rounded-full bg-brand-100 text-brand-700 text-xs font-bold flex items-center justify-center">
                  {a.name[0].toUpperCase()}
                </span>
                {a.name}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
