import axios from "axios";
import type {
  Agent, AgentCreate,
  Workflow, WorkflowCreate, WorkflowTemplate,
  Message, ExecutionLog, ExecutionResult,
} from "../types";

// Axios client — Vite proxy forwards /api → http://localhost:8000
const http = axios.create({ baseURL: "/api", timeout: 30_000 });

// ─── Agents ──────────────────────────────────────────────────────────────────

export const agentApi = {
  list:    ()                         => http.get<Agent[]>("/agents").then(r => r.data),
  get:     (id: string)               => http.get<Agent>(`/agents/${id}`).then(r => r.data),
  create:  (data: AgentCreate)        => http.post<Agent>("/agents", data).then(r => r.data),
  update:  (id: string, data: Partial<AgentCreate>) =>
                                         http.put<Agent>(`/agents/${id}`, data).then(r => r.data),
  remove:  (id: string)               => http.delete(`/agents/${id}`).then(r => r.data),
  patchTools:    (id: string, tools: string[])    =>
                                         http.patch<Agent>(`/agents/${id}/tools`, { tools }).then(r => r.data),
  patchChannels: (id: string, channels: string[]) =>
                                         http.patch<Agent>(`/agents/${id}/channels`, { channels }).then(r => r.data),
  execute: (id: string, input: string, workflowId?: string) =>
                                         http.post(`/agents/${id}/execute`, {
                                           input,
                                           ...(workflowId ? { workflow_id: workflowId } : {}),
                                         }).then(r => r.data),
};

// ─── Workflows ────────────────────────────────────────────────────────────────

export const workflowApi = {
  list:      ()                            => http.get<Workflow[]>("/workflows").then(r => r.data),
  get:       (id: string)                  => http.get<Workflow>(`/workflows/${id}`).then(r => r.data),
  create:    (data: WorkflowCreate)        => http.post<Workflow>("/workflows", data).then(r => r.data),
  update:    (id: string, data: Partial<WorkflowCreate>) =>
                                              http.put<Workflow>(`/workflows/${id}`, data).then(r => r.data),
  remove:    (id: string)                  => http.delete(`/workflows/${id}`).then(r => r.data),
  execute:   (id: string, input?: string)  => http.post<ExecutionResult>(`/workflows/${id}/execute`,
                                              input ? { input } : undefined).then(r => r.data),
  status:    (id: string)                  => http.get<{ workflow_id: string; status: string }>(`/workflows/${id}/status`).then(r => r.data),
  templates: ()                            => http.get<WorkflowTemplate[]>("/workflows/templates").then(r => r.data),
};

// ─── Messages & Execution Logs ───────────────────────────────────────────────

export const messageApi = {
  list: (workflowId: string) => http.get<Message[]>(`/messages/${workflowId}`).then(r => r.data),
};

export const executionApi = {
  logs: (workflowId: string) => http.get<ExecutionLog[]>(`/execution/${workflowId}/logs`).then(r => r.data),
};

// ─── Health ───────────────────────────────────────────────────────────────────

export const healthApi = {
  check: () => http.get<{ status: string }>("/health").then(r => r.data),
};
