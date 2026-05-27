# Decision Log - Phase 1

## Decision 001: Language
- Chosen: Python
- Alternatives: TypeScript, Rust
- Why: strongest AI tooling ecosystem and fast iteration with async support.

## Decision 002: Agent Framework
- Chosen: LangGraph
- Alternatives: CrewAI, AutoGen, custom orchestration
- Why: explicit graph/state model aligns with workflow builder and multi-agent execution paths.

## Decision 003: Backend Framework
- Chosen: FastAPI
- Alternatives: Django, Flask
- Why: async-native, high performance, minimal overhead, built-in OpenAPI docs.

## Decision 004: Frontend Stack
- Chosen: React + TypeScript + TailwindCSS
- Alternatives: Vue, Svelte
- Why: mature ecosystem, strong team familiarity, reliable for complex dashboard/state UX.

## Decision 005: Primary Database
- Chosen: PostgreSQL
- Alternatives: MongoDB, DynamoDB
- Why: ACID guarantees + relational joins + JSONB flexibility for agent/workflow configs.

## Decision 006: Cache/Queue
- Chosen: Redis
- Alternatives: Memcached
- Why: pub/sub and queue capability support inter-agent communication and live updates.

## Decision 007: External Channel Priority
- Chosen: Telegram first
- Alternatives: WhatsApp first, Slack first
- Why: simpler setup and faster delivery for demo-critical external channel requirement.

## Decision 008: Day-1 WebSocket Support
- Chosen: Yes
- Why: real-time logs/agent state are core UX and required for execution monitoring screens.

## Decision 009: Data Lifecycle
- Chosen: soft-delete agents/workflows, retain execution/message history
- Why: auditability and traceability for debugging and demo validation.

## Open Questions for Backend Engineer
- Authentication strategy: JWT bearer vs API key + service token
- Rate limit defaults on execute/webhook endpoints
- Execution timeout defaults per agent/workflow

---

# Decision Log - Phase 2 (Backend)

## Decision 010: SQLite as Development Default
- Chosen: SQLite (dev), PostgreSQL (Docker/prod)
- Why: zero-config startup for local development; `DATABASE_URL` is the only switch needed for PostgreSQL; Alembic handles both dialects identically.
- Impact: tests run without any external services; CI is trivially simple.

## Decision 011: Hard Delete vs Soft Delete
- Chosen: Hard delete (`db.delete(agent)`) for Phase 2 simplicity
- Original plan: soft-delete with `is_deleted` flag
- Why: avoids a schema migration; execution logs use nullable FK so orphaned rows are non-breaking.
- Future: add `is_deleted BOOLEAN DEFAULT FALSE` column in next migration.

## Decision 012: LangGraph StateGraph per Execution (not per Workflow)
- Chosen: compile the `StateGraph` fresh on every `execute_workflow` call
- Why: workflow DAG can change between executions (user edits the graph); caching a compiled graph would serve stale topology.
- Trade-off: minor compilation overhead (~5ms) on each call; acceptable at current scale.

## Decision 013: Fallback Sequential Executor
- Chosen: implement a plain sequential loop as fallback if LangGraph fails
- Why: makes the platform functional even if LangGraph has an import issue or graph compilation error; improves demo reliability.

## Decision 014: Token Counting via Word Split (not tiktoken)
- Chosen: `len(text.split())` approximation
- Why: avoids adding `tiktoken` to dependencies; for demo accuracy is sufficient.
- Future: swap for `tiktoken` when real cost tracking is needed.

---

# Decision Log - Phase 3 (Frontend)

## Decision 015: ReactFlow for Workflow Canvas
- Chosen: ReactFlow (`reactflow` v11)
- Alternatives: dagre-d3, vis.js, custom SVG
- Why: production-ready DAG renderer with drag-and-drop, custom node/edge types, and a mature React API; fastest path to a polished workflow builder.

## Decision 016: Zustand over Redux / Context
- Chosen: Zustand for global state
- Why: minimal boilerplate; fine-grained subscriptions prevent unnecessary re-renders on the live monitor page; no Provider wrapping needed.

## Decision 017: Axios over fetch
- Chosen: Axios for HTTP calls
- Why: interceptors simplify error handling; typed response generics; consistent with team conventions.

---

# Decision Log - Phase 4 (Integrations)

## Decision 018: Telegram Polling over Webhooks
- Chosen: Long-polling (`run_polling`) started as a background asyncio task
- Alternatives: webhook (requires public HTTPS endpoint)
- Why: polling works on localhost with no ngrok / port-forwarding; ideal for local demo; switching to webhook in production is a one-line change.

## Decision 019: In-Process WebSocket Broadcaster over Redis Pub/Sub
- Chosen: in-memory `WebSocketBroadcaster` (per-process)
- Why: no extra Redis dependency for the broadcast layer; single-process demo needs no cross-process fan-out.
- Limitation documented: scaling to multiple workers requires a Redis pub/sub adapter.

---

# Decision Log - Phase 5 (DevOps)

## Decision 020: Docker Compose with Health-Check Gating
- Chosen: `depends_on` with `condition: service_healthy` for all service dependencies
- Why: prevents backend from starting before Postgres accepts connections, eliminating race-condition startup failures.

## Decision 021: Alembic Migration on Container Startup
- Chosen: `alembic upgrade head` in the Docker `command` before uvicorn
- Why: ensures schema is always up-to-date on first run without a separate init step.

## Decision 022: Multi-Stage Frontend Dockerfile
- Chosen: Node 20 builder → `serve dist/` runner
- Why: final image contains only the static build output + serve; significantly smaller than shipping the full Node dev environment.

---

# Decision Log - Phase 6 (Demo / Testing)

## Decision 023: Optional Input for Workflow Execute
- Chosen: add `{"input": "..."}` body to `POST /api/workflows/{id}/execute`
- Why: without this, all workflow executions started with the literal string "Workflow started", making demos less compelling.
- Impact: updated `execute_workflow()` signature in executor + route handler.

---

# Open Items (Future Work)

| Item | Priority | Notes |
|------|----------|-------|
| Add `is_deleted` soft-delete column | Medium | Avoids orphaned FK logs |
| Replace word-split token counting with tiktoken | Low | Accuracy only matters for real cost tracking |
| Add Bearer token authentication middleware | High | Required before any public deployment |
| Redis pub/sub broadcaster | Medium | Needed for multi-worker horizontal scaling |
| Real `datetime.now(UTC)` in models (replace `utcnow()`) | Low | Clears deprecation warnings |
