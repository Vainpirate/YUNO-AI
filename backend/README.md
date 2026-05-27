# YUNO AI — Backend

FastAPI service that powers the agent runtime, REST API, WebSocket streaming, and Telegram integration.

---

## Requirements

| Dependency | Version |
|-----------|---------|
| Python | 3.11+ |
| pip | 23+ |

Optional infrastructure (SQLite is the zero-config default):

| Service | Purpose | Required? |
|---------|---------|----------|
| PostgreSQL 15 | Production database | No (SQLite default) |
| Redis 7 | Message bus + pub/sub | No (graceful degradation) |

---

## Local Setup

```bash
# From repo root
cd backend

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Copy and edit environment variables
cp .env.example .env
# Open .env and set OPENAI_API_KEY and/or TELEGRAM_BOT_TOKEN
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Environment tag |
| `DATABASE_URL` | `sqlite:///./yuno_dev.db` | SQLAlchemy DB URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `OPENAI_API_KEY` | _(empty)_ | OpenAI key — enables real LLM responses |
| `TELEGRAM_BOT_TOKEN` | _(empty)_ | Telegram bot token — enables bot polling |
| `FRONTEND_URL` | `http://localhost:3000` | CORS allow-list origin |

> The platform works without `OPENAI_API_KEY` — agents return deterministic tool output.
> The platform works without `TELEGRAM_BOT_TOKEN` — Telegram polling is silently skipped.

---

## Running the API

```bash
# Development (hot-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production-style (multiple workers)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

| URL | Description |
|-----|-------------|
| http://localhost:8000/docs | Swagger UI (interactive) |
| http://localhost:8000/redoc | ReDoc reference |
| http://localhost:8000/api/health | Health check |

---

## Database Migrations (Alembic)

```bash
# Apply all pending migrations (required when using PostgreSQL)
alembic upgrade head

# Create a new migration after editing models.py
alembic revision --autogenerate -m "describe your change"

# Downgrade one step
alembic downgrade -1

# View migration history
alembic history --verbose
```

> **SQLite default:** tables are auto-created on startup via `Base.metadata.create_all()`.
> Alembic is only needed when switching to PostgreSQL.

---

## Running Tests

```bash
# All tests (uses in-memory SQLite — no external services needed)
pytest tests/ -v

# With coverage report
pytest tests/ -v --cov=app --cov-report=term-missing
```

### Test Suite

| File | What it covers |
|------|---------------|
| `tests/test_agent_crud.py` | Create / update / patch tools / delete lifecycle |
| `tests/test_workflow_execution.py` | 2-agent workflow execution + status endpoint |
| `tests/test_messaging.py` | Message persistence + execution log retrieval |

---

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI entry point + lifespan hooks
│   ├── config.py            # Pydantic settings (reads .env)
│   ├── models.py            # SQLAlchemy ORM models
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── database.py          # Engine + session factory
│   ├── routes/
│   │   ├── agents.py        # Agent CRUD + single-agent execute
│   │   ├── workflows.py     # Workflow CRUD + execute + templates
│   │   ├── messages.py      # Message history
│   │   └── execution.py     # Execution logs
│   ├── runtime/
│   │   ├── executor.py      # RuntimeExecutor (LangGraph + fallback)
│   │   ├── agent_factory.py # LangGraph node builder
│   │   ├── tools.py         # ToolRegistry (auto-discovers _tool_* methods)
│   │   └── memory.py        # MemoryStore (per-agent conversation buffer)
│   ├── integrations/
│   │   ├── telegram_bot.py  # Async polling bot
│   │   ├── messaging_bus.py # Redis inter-agent queue
│   │   └── external_tools.py# Registers external tools at startup
│   └── websocket/
│       ├── broadcaster.py   # WebSocket fan-out broadcaster
│       └── handlers.py      # WS route handlers
├── migrations/              # Alembic migration scripts
├── tests/                   # Pytest test suite
├── requirements.txt
├── Dockerfile
├── alembic.ini
└── .env.example
```

---

## API Endpoints

```
# Agents
POST   /api/agents
GET    /api/agents
GET    /api/agents/{id}
PUT    /api/agents/{id}
DELETE /api/agents/{id}
PATCH  /api/agents/{id}/tools       body: {"tools": ["calculator"]}
PATCH  /api/agents/{id}/channels    body: {"channels": ["telegram"]}
POST   /api/agents/{id}/execute     body: {"input": "...", "workflow_id": "..."}

# Workflows
POST   /api/workflows
GET    /api/workflows
GET    /api/workflows/templates
GET    /api/workflows/{id}
PUT    /api/workflows/{id}
POST   /api/workflows/{id}/execute  body: {"input": "..."}  (optional)
GET    /api/workflows/{id}/status

# Messaging & Monitoring
GET    /api/messages/{workflow_id}
GET    /api/execution/{workflow_id}/logs
WS     /ws/logs/{workflow_id}
WS     /ws/agent-status/{agent_id}

# Health
GET    /api/health
GET    /api/health/db
GET    /api/health/redis
```

---

## Key Components

### RuntimeExecutor

Central execution engine (`app/runtime/executor.py`). All agent and workflow execution flows through here.

```python
# Single agent
result = await runtime_executor.execute_agent(db, agent, user_input)

# Full workflow
result = await runtime_executor.execute_workflow(db, workflow, initial_input="...")
```

- **LangGraph path:** compiles `workflow.graph` into a `StateGraph`, invokes it.
- **Fallback path:** sequential loop used if LangGraph is unavailable or the graph is invalid.
- Both paths persist `Message` + `ExecutionLog` rows and broadcast WebSocket events.

### ToolRegistry

Auto-discovers tools from `_tool_*` methods:

```python
class ToolRegistry:
    def _tool_my_tool(self, input_text: str) -> str:
        return input_text.upper()
# → registered as "my_tool"
```

### WebSocketBroadcaster

In-process fan-out broadcaster. Replace with Redis pub/sub for multi-worker deployments.

---

## Docker

```bash
# Backend only
docker build -t yuno-backend .
docker run -p 8000:8000 --env-file .env yuno-backend

# Full stack (recommended)
cd ..
docker-compose up --build
```
