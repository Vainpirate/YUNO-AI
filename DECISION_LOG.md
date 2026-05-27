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
