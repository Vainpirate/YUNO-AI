# Architecture Decisions - Phase 1 (ARCHITECT)

## Objective
Design the technical architecture for the AI Agent Orchestration Platform with clear rationale and implementation-ready contracts.

## Final Stack
- Language: Python 3.11+
- Agent orchestration runtime: LangGraph
- Backend API: FastAPI
- Frontend: React + TypeScript + TailwindCSS
- Primary database: PostgreSQL
- Queue/cache/event bus: Redis
- External messaging: Telegram first (WhatsApp optional in later phase)

## Rationale Summary
- Python + LangGraph gives the strongest velocity for multi-agent orchestration with robust state handling.
- FastAPI provides async-native APIs and automatic OpenAPI docs.
- PostgreSQL supports both relational integrity and JSONB flexibility for workflow/agent configuration.
- Redis supports pub/sub and low-latency inter-agent message transport.
- React + TypeScript provides a mature ecosystem for workflow canvas + real-time dashboard UX.

## High-Level System Architecture
1. Frontend UI sends REST requests and subscribes to WebSocket streams.
2. FastAPI validates requests and persists control-plane data.
3. Runtime layer loads workflow DAG and executes agents via LangGraph.
4. Each execution event is persisted to `execution_logs` and broadcast to WebSocket clients.
5. Inter-agent messages are written to `messages` and optionally queued via Redis.
6. External messages (Telegram) are ingested and persisted to `message_history`.

## Core Components
- API Layer
- Runtime Layer (agent factory, executor, tools)
- Persistence Layer (PostgreSQL)
- Messaging Layer (Redis + external channels)
- Monitoring Layer (execution logs + WebSocket streaming)

## Key Non-Functional Decisions
- Async-first architecture for execution and monitoring
- Soft-delete strategy for agents/workflows to preserve audit history
- UUID primary keys across all major entities
- UTC timestamps for observability consistency
- Idempotent execution status transitions

## Security & Reliability Baseline
- API key/JWT auth planned from Backend Phase start
- Input validation on all create/update endpoints
- Rate limiting recommended for execute and external webhook endpoints
- Structured error payloads with correlation IDs

## Phase 1 Output Mapping
- Database DDL: `schema.sql`
- API contract: `openapi_spec.yaml`
- UI direction: `wireframes/`
- Decision history: `DECISION_LOG.md`

## Checkpoint 1 Sign-off Criteria
- Stack finalized: Python + FastAPI + LangGraph + React + PostgreSQL + Redis
- Schema approved
- API contract agreed
- Wireframes reviewed
