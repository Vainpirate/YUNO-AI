# YUNO AI — Agent Orchestration Platform

> Build, connect, and monitor multi-agent AI workflows — with real-time messaging, a visual workflow builder, and Telegram integration.

[![Tests](https://img.shields.io/badge/tests-3%2F3%20passing-brightgreen)](#testing)
[![Stack](https://img.shields.io/badge/stack-FastAPI%20%7C%20LangGraph%20%7C%20React-blue)](#architecture)

---

## Overview

YUNO AI is a full-stack **AI Agent Orchestration Platform** that lets you:

- **Create & configure** AI agents with custom roles, tools, memory, and guardrails
- **Build multi-agent workflows** via a drag-and-drop canvas
- **Execute workflows** end-to-end with LangGraph orchestration
- **Monitor executions** in real-time via WebSocket-streamed logs
- **Integrate with Telegram** — send a message to a bot, get an AI response
- **Track message history** and per-step cost/token usage

---

## Quick Start

### Prerequisites

| Requirement | Version |
|-------------|---------|
| Docker + Docker Compose | v2+ |
| Python | 3.11+ (for local dev) |
| Node.js | 20+ (for local dev) |

### One-command startup

```bash
# 1. Clone the repo
git clone <repo-url>
cd yuno-ai

# 2. Copy and fill in environment variables
cp backend/.env.example backend/.env
# → set OPENAI_API_KEY and (optionally) TELEGRAM_BOT_TOKEN

# 3. Start all services
docker-compose up --build

# 4. Access the platform
#    UI:      http://localhost:3000
#    API:     http://localhost:8000/docs
#    Health:  http://localhost:8000/api/health
```

> **First run only** — if using PostgreSQL (the Docker default):
> ```bash
> docker-compose exec backend alembic upgrade head
> ```
> With SQLite (local dev default) tables are created automatically on startup.

### Local development (no Docker)

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env          # edit as needed
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev                   # → http://localhost:5173
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Web UI  (React + TypeScript)                  │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────────┐  │
│  │ Agent Manager│  │ Workflow Builder  │  │  Live Monitor     │  │
│  │  (CRUD + cfg)│  │  (ReactFlow DAG) │  │  (WebSocket logs) │  │
│  └──────────────┘  └──────────────────┘  └───────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                    REST / WebSocket
┌───────────────────────────┴─────────────────────────────────────┐
│              FastAPI Backend  (port 8000)                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Routes: /api/agents  /api/workflows  /api/messages        │  │
│  │          /api/execution  /api/health                       │  │
│  │  WebSocket: /ws/logs/{wf_id}  /ws/agent-status/{id}       │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Runtime Layer (LangGraph)                                 │  │
│  │   ├─ RuntimeExecutor (execute_agent / execute_workflow)    │  │
│  │   ├─ AgentFactory   (node builder for StateGraph)         │  │
│  │   ├─ ToolRegistry   (calculator, datetime, random_fact…)  │  │
│  │   └─ MemoryStore    (per-agent conversation buffer)       │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Data Layer                                                │  │
│  │   ├─ SQLite (dev default, zero-config)                     │  │
│  │   ├─ PostgreSQL (production / Docker)                     │  │
│  │   └─ Redis  (messaging bus + pub/sub)                     │  │
│  └────────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                    Webhook / Polling
┌──────────┐      ┌─────────────────────────────────────────────┐
│ Telegram │─────▶│  integrations/telegram_bot.py               │
│   Bot    │      │  integrations/messaging_bus.py (Redis queue)│
└──────────┘      └─────────────────────────────────────────────┘
```

### Data Flow

1. **User** sends a prompt via UI or Telegram.
2. **FastAPI** validates and routes the request to `RuntimeExecutor`.
3. **RuntimeExecutor** builds a LangGraph `StateGraph` from the workflow DAG, then invokes it.
4. **Each agent node** executes: loads memory → runs registered tools → calls OpenAI LLM (if key is set) → returns response.
5. **Agent output** is persisted to `messages` + `execution_logs` tables and broadcast over WebSocket.
6. **Frontend** receives real-time log events; status indicators update live.

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Agent runtime | **LangGraph** | Graph-based orchestration with typed state, streaming, memory |
| API | **FastAPI** | Async-native, auto-OpenAPI docs, minimal boilerplate |
| Database | **SQLite** (dev) / **PostgreSQL** (prod) | ACID + JSON columns for flexible configs |
| Message bus | **Redis** | Pub/sub for inter-agent messaging |
| Frontend | **React + TypeScript + TailwindCSS** | Mature ecosystem; ReactFlow for DAG canvas |
| Workflow canvas | **ReactFlow** | Drag-and-drop DAG with custom nodes/edges |
| External channel | **python-telegram-bot** | Free API, no OAuth friction |
| ORM | **SQLAlchemy 2** + **Alembic** | Typed models, migration history |

---

## Project Structure

```
yuno-ai/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point + lifespan
│   │   ├── config.py                # Pydantic settings (env vars)
│   │   ├── models.py                # SQLAlchemy ORM models
│   │   ├── schemas.py               # Pydantic request/response schemas
│   │   ├── database.py              # Engine + session factory
│   │   ├── routes/                  # REST route handlers
│   │   │   ├── agents.py
│   │   │   ├── workflows.py
│   │   │   ├── messages.py
│   │   │   └── execution.py
│   │   ├── runtime/                 # Core agent execution engine
│   │   │   ├── executor.py          # RuntimeExecutor (LangGraph + fallback)
│   │   │   ├── agent_factory.py     # LangGraph node builder
│   │   │   ├── tools.py             # ToolRegistry
│   │   │   └── memory.py            # MemoryStore (conversation buffer)
│   │   ├── integrations/
│   │   │   ├── telegram_bot.py      # Telegram polling bot
│   │   │   ├── messaging_bus.py     # Redis-backed inter-agent bus
│   │   │   └── external_tools.py   # datetime, random_fact, word_count…
│   │   └── websocket/
│   │       ├── broadcaster.py       # WebSocket fan-out broadcaster
│   │       └── handlers.py          # WS route handlers
│   ├── migrations/                  # Alembic migration scripts
│   ├── tests/                       # Pytest test suite
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/              # AgentForm, WorkflowBuilder, ExecutionMonitor…
│   │   ├── pages/                   # Dashboard, AgentManager, WorkflowStudio, Monitoring
│   │   ├── hooks/useWebSocket.ts    # Auto-reconnecting WebSocket hook
│   │   ├── services/api.ts          # Axios client + typed endpoint wrappers
│   │   ├── store/index.ts           # Zustand global state
│   │   └── types/index.ts           # Shared TypeScript interfaces
│   └── Dockerfile
├── docker-compose.yml
├── schema.sql                       # Reference DDL (authoritative schema)
├── openapi_spec.yaml                # API contract
├── ARCHITECTURE.md                  # Architecture decisions log
├── DECISION_LOG.md                  # Why each tech choice was made
├── EXTENDING.md                     # How to add tools / channels / templates
└── DEMO.md                          # Demo script + scenarios
```

---

## API Reference

Interactive docs at **http://localhost:8000/docs** (Swagger UI).

### Agents

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/agents` | Create a new agent |
| `GET` | `/api/agents` | List all agents |
| `GET` | `/api/agents/{id}` | Get agent details |
| `PUT` | `/api/agents/{id}` | Update agent config |
| `DELETE` | `/api/agents/{id}` | Delete agent |
| `PATCH` | `/api/agents/{id}/tools` | Update tool list |
| `PATCH` | `/api/agents/{id}/channels` | Update channel list |
| `POST` | `/api/agents/{id}/execute` | Execute a single agent |

### Workflows

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/workflows` | Create a workflow |
| `GET` | `/api/workflows` | List workflows |
| `GET` | `/api/workflows/templates` | List built-in templates |
| `GET` | `/api/workflows/{id}` | Get workflow details |
| `PUT` | `/api/workflows/{id}` | Update workflow graph |
| `POST` | `/api/workflows/{id}/execute` | Execute workflow (body: `{"input": "..."}`) |
| `GET` | `/api/workflows/{id}/status` | Get execution status |

### Messages & Monitoring

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/messages/{workflow_id}` | Message history |
| `GET` | `/api/execution/{workflow_id}/logs` | Execution logs |
| `WS` | `/ws/logs/{workflow_id}` | Real-time log stream |
| `WS` | `/ws/agent-status/{agent_id}` | Agent status updates |

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | App alive |
| `GET` | `/api/health/db` | Database connectivity |
| `GET` | `/api/health/redis` | Redis connectivity |

---

## Agent Configuration

```json
{
  "name": "Research Assistant",
  "role": "Web Researcher",
  "system_prompt": "You are an expert at finding and synthesizing information.",
  "model": "gpt-4o-mini",
  "tools": ["calculator", "datetime_now", "random_fact"],
  "channels": ["telegram"],
  "memory_config": {},
  "guardrails": {}
}
```

### Available Tools

| Tool | Description |
|------|-------------|
| `calculator` | Evaluates math expressions safely |
| `datetime_now` | Returns current UTC datetime |
| `random_fact` | Returns a random interesting fact |
| `word_count` | Counts words in a string |

> See [EXTENDING.md](EXTENDING.md) to add custom tools.

---

## Telegram Setup

1. Create a bot via [@BotFather](https://t.me/botfather) → get `TELEGRAM_BOT_TOKEN`
2. Set it in `backend/.env`:
   ```
   TELEGRAM_BOT_TOKEN=1234567890:ABCdef...
   ```
3. Start the platform. The bot polls automatically on startup.
4. Send `/start` to your bot — it will be routed to the first active agent.

> Use the `/config` command in Telegram to bind a specific agent to your chat.

---

## Workflow Templates

Three built-in templates available via `GET /api/workflows/templates`:

| Template | Agents | Description |
|----------|--------|-------------|
| `research_summarize` | 2 | Researcher → Summarizer |
| `qa_router` | 2 | Router → Specialist |
| `research_summarize_validate` | 3 | Researcher → Summarizer → Validator |

---

## Testing

```bash
cd backend
pytest tests/ -v
# → 3 passed (agent_crud, workflow_execution, message_delivery)
```

Test coverage areas:
- Agent CRUD lifecycle (create / update / patch tools / delete)
- 2-agent workflow execution with message passing
- Message persistence and execution log retrieval

---

## Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `DATABASE_URL` | `sqlite:///./yuno_dev.db` | No | DB connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | No | Redis connection string |
| `OPENAI_API_KEY` | _(empty)_ | No* | Enables real LLM responses |
| `TELEGRAM_BOT_TOKEN` | _(empty)_ | No* | Enables Telegram bot |
| `BACKEND_URL` | `http://localhost:8000` | No | Used for internal cross-service calls |
| `FRONTEND_URL` | `http://localhost:3000` | No | CORS allow-list origin |

> \* Platform works without these keys — agents fall back to deterministic tool output or an echo response.

---

## Known Limitations

- **No authentication** — all API endpoints are unauthenticated (add Bearer token middleware for production).
- **In-memory broadcaster** — WebSocket fan-out is per-process; horizontally scaling the backend requires a Redis pub/sub adapter.
- **OpenAI only** — the LLM client targets OpenAI; add an Anthropic/Groq adapter in `executor.py` for other providers.
- **SQLite concurrency** — SQLite works for single-process dev; switch to PostgreSQL for multi-worker deployments.

---

## Extending the Platform

See [EXTENDING.md](EXTENDING.md) for step-by-step guides on:
- Adding new tools
- Adding new messaging channels (WhatsApp, Slack)
- Adding custom workflow templates

---

## License

MIT
