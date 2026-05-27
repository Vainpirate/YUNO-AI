# Architecture — YUNO AI Agent Orchestration Platform

## Stack at a Glance

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Agent orchestration | **LangGraph** | Graph-based state machine; composable nodes; native streaming |
| API | **FastAPI** | Async-native; auto OpenAPI; zero-overhead dependency injection |
| ORM / migrations | **SQLAlchemy 2 + Alembic** | Typed models; migration version control |
| Database (dev) | **SQLite** | Zero-config; starts immediately without Docker |
| Database (prod) | **PostgreSQL** | ACID; JSONB for flexible agent configs; referential integrity |
| Message bus | **Redis** | Low-latency pub/sub; inter-agent queue |
| Frontend | **React 19 + TypeScript + TailwindCSS** | Mature ecosystem; full type safety |
| Workflow canvas | **ReactFlow** | Production-grade DAG renderer; drag-and-drop |
| External messaging | **python-telegram-bot** | Free API; no OAuth; instant setup |

---

## System Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                      Browser (port 3000)                          │
│                                                                   │
│   ┌─────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│   │  Agent Mgr  │  │ Workflow Studio   │  │  Live Monitor      │  │
│   │  (CRUD UI)  │  │  (ReactFlow DAG) │  │  (WS log stream)  │  │
│   └──────┬──────┘  └────────┬─────────┘  └─────────┬──────────┘  │
│          │                  │                       │             │
│   ┌──────┴──────────────────┴───────────────────────┴──────────┐  │
│   │           services/api.ts  +  hooks/useWebSocket.ts        │  │
│   └──────────────────────────────────┬──────────────────────────┘  │
└─────────────────────────────────────┼────────────────────────────┘
                                      │  REST + WebSocket
┌─────────────────────────────────────┴────────────────────────────┐
│                  FastAPI  (port 8000)                             │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  REST Routes                                             │    │
│  │  POST/GET/PUT/DELETE  /api/agents                        │    │
│  │  POST/GET/PUT         /api/workflows   + /execute        │    │
│  │  GET                  /api/messages/{wf_id}              │    │
│  │  GET                  /api/execution/{wf_id}/logs        │    │
│  │  GET                  /api/health  /health/db  /health/redis│  │
│  └──────────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  WebSocket Handlers                                      │    │
│  │  /ws/logs/{workflow_id}       → workflow log stream      │    │
│  │  /ws/agent-status/{agent_id} → agent state changes      │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Runtime Layer  (app/runtime/)                           │    │
│  │                                                          │    │
│  │   RuntimeExecutor                                        │    │
│  │   ├─ execute_agent()     → single-agent + LLM synthesis  │    │
│  │   └─ execute_workflow()  → LangGraph StateGraph invoke   │    │
│  │                                                          │    │
│  │   LangGraph StateGraph                                   │    │
│  │   ├─ Nodes = agent closures (make_agent_node)            │    │
│  │   ├─ Edges = workflow DAG  (from workflow.graph JSON)    │    │
│  │   └─ State = WorkflowState {messages, current_input,    │    │
│  │              final_output, step_outputs}                 │    │
│  │                                                          │    │
│  │   ToolRegistry   → execute registered tools by name     │    │
│  │   MemoryStore    → per-agent conversation buffer        │    │
│  │   AgentFactory   → build_agent_prompt + make_agent_node │    │
│  └──────────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  WebSocket Broadcaster  (app/websocket/broadcaster.py)   │    │
│  │  Maintains per-workflow + per-agent subscriber sets.     │    │
│  │  Fan-out: publish_workflow_log / publish_agent_status    │    │
│  └──────────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Data Layer                                              │    │
│  │  agents │ workflows │ messages │ message_history         │    │
│  │  execution_logs                                          │    │
│  │  SQLite (dev)  ──or──  PostgreSQL (Docker / prod)        │    │
│  └──────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────┬────────────────────────────┘
                                      │  Redis pub/sub + HTTP webhook
          ┌───────────────────────────┴───────────────────────────┐
          │  Integrations  (app/integrations/)                    │
          │                                                       │
          │  telegram_bot.py     — async polling bot              │
          │  messaging_bus.py    — Redis-backed agent queue       │
          │  external_tools.py   — datetime, random_fact…        │
          └───────────────────────────────────────────────────────┘
                         ▲
                         │  Telegram Bot API
                    ┌────┴──────┐
                    │ Telegram  │
                    │   User    │
                    └───────────┘
```

---

## Execution Flow (Multi-Agent Workflow)

```
User clicks [Execute] in WorkflowStudio
        │
        ▼
POST /api/workflows/{id}/execute  {"input": "..."}
        │
        ▼
execute_workflow(db, workflow, initial_input)
        │
        ├─ Resolve agent records from DB (by UUID in workflow.agents)
        │
        ├─ Build LangGraph StateGraph
        │   ├─ Each agent UUID → node  (make_agent_node closure)
        │   ├─ Edges from workflow.graph.edges  [[src_id, dst_id], ...]
        │   └─ Final node → END
        │
        ├─ compiled.invoke(initial_state)
        │   │
        │   └─ Per node: _run_agent_step(agent, current_input)
        │       ├─ Load memory (conversation buffer)
        │       ├─ Build prompt (system + memory + input)
        │       ├─ Execute each registered tool
        │       ├─ (async) LLM call if no tool output + OPENAI_API_KEY set
        │       └─ Return {response, tool_outputs, prompt}
        │
        ├─ Persist to DB
        │   ├─ Message row  (from_agent → content → workflow_id)
        │   └─ ExecutionLog row  (step, status, tokens, cost)
        │
        └─ Broadcast WebSocket events
            ├─ step_completed  → /ws/logs/{workflow_id}
            └─ workflow_completed → /ws/logs/{workflow_id}
```

---

## Database Schema

```
agents
  id UUID PK | name VARCHAR UNIQUE | role VARCHAR
  system_prompt TEXT | model VARCHAR
  tools JSON | channels JSON | memory_config JSON | guardrails JSON
  created_at DATETIME | updated_at DATETIME

workflows
  id UUID PK | name VARCHAR | description TEXT
  agents JSON          -- [uuid, uuid, ...]
  graph JSON           -- {nodes:[...], edges:[[src,dst],...]}
  schedule VARCHAR | template_name VARCHAR
  created_at DATETIME

messages
  id UUID PK | from_agent_id UUID FK | to_agent_id UUID FK
  workflow_id UUID FK | channel VARCHAR
  content TEXT | metadata JSON | created_at DATETIME

message_history          -- external channel (Telegram) conversation log
  id UUID PK | channel_user_id VARCHAR | agent_id UUID FK
  direction VARCHAR      -- "inbound" | "outbound"
  content TEXT | metadata JSON | created_at DATETIME

execution_logs
  id UUID PK | workflow_id UUID FK | agent_id UUID FK
  step_name VARCHAR | status VARCHAR
  input JSON | output JSON
  tokens_used INT | cost DECIMAL | error TEXT
  created_at DATETIME
```

---

## Key Design Decisions

### Why LangGraph over CrewAI / AutoGen?

- **Graph-aligned** — the visual workflow builder maps 1:1 to a `StateGraph`; nodes are agents, edges are message routes.
- **Typed state** — `WorkflowState` (TypedDict) makes inter-node data flow explicit and debuggable.
- **Streaming** — LangGraph supports step-by-step streaming; we broadcast each step over WebSocket.
- **Flexibility** — no opinionated agent personas; any Python function can be a node.

### Why SQLite as dev default?

Zero Docker dependency for local development. The `DATABASE_URL` switch to PostgreSQL in `.env` or `docker-compose.yml` is a single line change; Alembic handles both dialects identically.

### Why in-process WebSocket broadcaster?

Simplicity for single-process local demo. The broadcaster interface (`publish_workflow_log`, `publish_agent_status`) is clean enough to swap for a Redis pub/sub adapter when horizontal scaling is needed.

### Soft-delete not implemented (known gap)

The current `DELETE /api/agents/{id}` performs a hard delete. Execution logs referencing the agent are orphaned (FK is nullable). A production implementation would add an `is_deleted` flag and filter it in all `SELECT` queries.

---

## Non-Functional Characteristics

| Characteristic | Current behaviour | Production recommendation |
|----------------|------------------|--------------------------|
| Authentication | None | Add Bearer token middleware |
| Rate limiting | None | Add slowapi or nginx rate limit |
| Error format | HTTP exceptions with `detail` string | Add correlation ID + structured error body |
| Observability | `logging` to stdout | Ship to structured log aggregator (Loki/Datadog) |
| Scalability | Single-process | Replace in-memory broadcaster with Redis pub/sub |
| LLM providers | OpenAI (AsyncOpenAI) | Add Anthropic / Groq adapter in `executor.py` |
