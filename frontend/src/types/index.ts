// ─── Domain models (mirror backend Pydantic schemas) ─────────────────────────

export interface AgentSkill {
  name: string;
  description: string;
  enabled: boolean;
}

export interface AgentGuardrails {
  banned_keywords?: string[];
  blocked_topics?: string[];
  max_input_tokens?: number;
  max_output_tokens?: number;
  require_safe_response?: boolean;
}

export interface AgentMemoryConfig {
  window_size?: number;
  memory_type?: "sliding_window" | "full";
}

export interface AgentInteractionRules {
  response_format?: "text" | "json" | "markdown";
  language?: string;
  temperature?: number;
  max_turns?: number;
}

export interface Agent {
  id: string;
  name: string;
  role: string | null;
  system_prompt: string | null;
  model: string | null;
  tools: string[];
  channels: string[];
  memory_config: AgentMemoryConfig;
  guardrails: AgentGuardrails;
  skills: AgentSkill[];
  interaction_rules: AgentInteractionRules;
  created_at: string;
  updated_at: string;
}

export interface AgentCreate {
  name: string;
  role?: string;
  system_prompt?: string;
  model?: string;
  tools?: string[];
  channels?: string[];
  memory_config?: AgentMemoryConfig;
  guardrails?: AgentGuardrails;
  skills?: AgentSkill[];
  interaction_rules?: AgentInteractionRules;
}

export interface Workflow {
  id: string;
  name: string;
  description: string | null;
  agents: string[];
  graph: WorkflowGraph;
  schedule: string | null;
  max_iterations: number;
  template_name: string | null;
  created_at: string;
}

export interface WorkflowGraph {
  nodes: string[];
  edges: [string, string][];
}

export interface WorkflowCreate {
  name: string;
  description?: string;
  agents?: string[];
  graph?: WorkflowGraph;
  schedule?: string;
  max_iterations?: number;
  template_name?: string;
}

export interface WorkflowTemplate {
  name: string;
  description: string;
  graph: WorkflowGraph;
}

// ─── Execution / messaging ────────────────────────────────────────────────────

export interface Message {
  id: string;
  from_agent_id: string | null;
  to_agent_id: string | null;
  workflow_id: string | null;
  channel: string;
  content: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface ExecutionLog {
  id: string;
  workflow_id: string | null;
  agent_id: string | null;
  step_name: string;
  status: "running" | "success" | "error";
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
  tokens_used: number | null;
  cost: number | null;
  error: string | null;
  created_at: string;
}

export interface ExecutionResult {
  workflow_id: string;
  status: string;
  final_output: string;
  steps: number;
}

// ─── WebSocket events ─────────────────────────────────────────────────────────

export type WsEvent =
  | { event: "workflow_started"; workflow_id: string; workflow_name: string; agent_count: number; timestamp: string }
  | { event: "agent_response";   agent: string; response: string; tool_outputs: ToolOutput[]; timestamp: string }
  | { event: "step_completed";   agent: string; response: string; tool_outputs: ToolOutput[]; timestamp: string }
  | { event: "workflow_completed"; workflow_id: string; final_output: string; steps: number; timestamp: string }
  | { status: "connected"; workflow_id: string };

export interface ToolOutput {
  tool: string;
  result: string;
}

// ─── UI helpers ───────────────────────────────────────────────────────────────

export const AVAILABLE_TOOLS = [
  "calculator",
  "datetime_now",
  "json_format",
  "random_fact",
  "url_fetch",
  "web_search",
  "word_count",
] as const;

// ── Groq models (default provider for testing — fast + free tier) ─────────────
export const GROQ_MODELS = [
  "llama-3.3-70b-versatile",
  "llama-3.1-8b-instant",
  "llama3-70b-8192",
  "mixtral-8x7b-32768",
  "gemma2-9b-it",
] as const;

// ── Gemini models (fallback) ────────────────────────────────────────────────
export const GEMINI_MODELS = [
  "gemini-3-flash-preview",
  "gemini-2.0-flash-lite",
  "gemini-1.5-flash",
  "gemini-1.5-pro",
] as const;

export const AVAILABLE_MODELS = [
  ...GROQ_MODELS,
  ...GEMINI_MODELS,
] as const;

export const AVAILABLE_CHANNELS = ["telegram", "slack", "webhook"] as const;
