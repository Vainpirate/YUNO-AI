import { create } from "zustand";
import type { Agent, Workflow } from "../types";

// ─── Toast ────────────────────────────────────────────────────────────────────

export type ToastKind = "success" | "error" | "info";

export interface Toast {
  id: string;
  message: string;
  kind: ToastKind;
}

// ─── Store ────────────────────────────────────────────────────────────────────

interface AppState {
  // Agent cache
  agents: Agent[];
  setAgents: (agents: Agent[]) => void;
  upsertAgent: (agent: Agent) => void;
  removeAgent: (id: string) => void;

  // Workflow cache
  workflows: Workflow[];
  setWorkflows: (workflows: Workflow[]) => void;
  upsertWorkflow: (wf: Workflow) => void;

  // Toasts
  toasts: Toast[];
  pushToast: (message: string, kind?: ToastKind) => void;
  dismissToast: (id: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // ── agents ──
  agents: [],
  setAgents:   (agents) => set({ agents }),
  upsertAgent: (agent)  => set((s) => {
    const idx = s.agents.findIndex(a => a.id === agent.id);
    if (idx >= 0) {
      const updated = [...s.agents];
      updated[idx] = agent;
      return { agents: updated };
    }
    return { agents: [agent, ...s.agents] };
  }),
  removeAgent: (id) => set((s) => ({ agents: s.agents.filter(a => a.id !== id) })),

  // ── workflows ──
  workflows: [],
  setWorkflows:    (workflows) => set({ workflows }),
  upsertWorkflow:  (wf)        => set((s) => {
    const idx = s.workflows.findIndex(w => w.id === wf.id);
    if (idx >= 0) {
      const updated = [...s.workflows];
      updated[idx] = wf;
      return { workflows: updated };
    }
    return { workflows: [wf, ...s.workflows] };
  }),

  // ── toasts ──
  toasts: [],
  pushToast: (message, kind = "info") => {
    const id = Math.random().toString(36).slice(2);
    set((s) => ({ toasts: [...s.toasts, { id, message, kind }] }));
    setTimeout(() => {
      set((s) => ({ toasts: s.toasts.filter(t => t.id !== id) }));
    }, 4000);
  },
  dismissToast: (id) => set((s) => ({ toasts: s.toasts.filter(t => t.id !== id) })),
}));
