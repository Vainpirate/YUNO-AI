# YUNO AI — Setup Guide

Complete setup instructions for every deployment mode, plus a troubleshooting reference.

---

## Contents

1. [Prerequisites](#1-prerequisites)
2. [Docker Compose (Recommended)](#2-docker-compose-recommended)
3. [Local Development (No Docker)](#3-local-development-no-docker)
4. [Environment Variables Reference](#4-environment-variables-reference)
5. [First-Time Database Setup](#5-first-time-database-setup)
6. [Telegram Bot Setup](#6-telegram-bot-setup)
7. [Verifying the Stack](#7-verifying-the-stack)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Prerequisites

### Docker Compose (recommended)

| Tool | Minimum version |
|------|----------------|
| Docker Engine | 24+ |
| Docker Compose | v2 (plugin form — `docker compose`) |

### Local development

| Tool | Minimum version |
|------|----------------|
| Python | 3.11 |
| Node.js | 20 |
| npm | 10 |

---

## 2. Docker Compose (Recommended)

```bash
# Clone the repo
git clone <repo-url>
cd yuno-ai

# Copy and fill in environment variables
cp backend/.env.example backend/.env
```

Open `backend/.env` and set at minimum:
```
OPENAI_API_KEY=sk-...          # optional — enables real LLM responses
TELEGRAM_BOT_TOKEN=123:abc...  # optional — enables Telegram bot
```

```bash
# Build and start all 4 services
docker-compose up --build
```

On first run with PostgreSQL (Docker default), run migrations once:
```bash
docker-compose exec backend alembic upgrade head
```

> **SQLite note:** if you run the backend locally (not via Docker) it uses SQLite by default
> and creates tables automatically — no migration step needed.

### What starts

| Service | Port | Description |
|---------|------|-------------|
| `postgres` | 5432 | PostgreSQL 15 |
| `redis` | 6379 | Redis 7 |
| `backend` | 8000 | FastAPI + LangGraph runtime |
| `frontend` | 3000 | React app (production build) |

### Accessing the platform

| URL | Description |
|-----|-------------|
| http://localhost:3000 | Web UI |
| http://localhost:8000/docs | Swagger API docs |
| http://localhost:8000/api/health | Health check |

### Stopping

```bash
docker-compose down              # stop containers, keep volumes
docker-compose down -v           # stop and delete all data volumes
```

---

## 3. Local Development (No Docker)

Run each service in a separate terminal.

### Terminal 1 — Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — DATABASE_URL defaults to SQLite, no further config needed

# Start the API server (hot-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2 — Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173 (Vite dev server)
```

> **CORS:** The backend allows `http://localhost:3000` and `http://localhost:5173` by default
> via the wildcard `"*"` in the CORS middleware. No config change needed for local dev.

### Optional: PostgreSQL + Redis locally

If you want the full production stack locally:

```bash
# Start infrastructure only (no backend/frontend containers)
docker-compose up postgres redis
```

Then set in `backend/.env`:
```
DATABASE_URL=postgresql+psycopg://admin:password@localhost:5432/agent_platform
REDIS_URL=redis://localhost:6379/0
```

---

## 4. Environment Variables Reference

All variables are read from `backend/.env` by Pydantic Settings.

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `YUNO Agent Orchestration API` | Display name in Swagger UI |
| `APP_ENV` | `development` | Environment tag (`development` / `production`) |
| `APP_HOST` | `0.0.0.0` | Uvicorn bind address |
| `APP_PORT` | `8000` | Uvicorn port |
| `DATABASE_URL` | `sqlite:///./yuno_dev.db` | SQLAlchemy connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `OPENAI_API_KEY` | _(empty)_ | OpenAI API key — enables LLM synthesis |
| `TELEGRAM_BOT_TOKEN` | _(empty)_ | Telegram bot token — enables polling |
| `BACKEND_URL` | `http://localhost:8000` | Backend base URL (used internally) |
| `FRONTEND_URL` | `http://localhost:3000` | CORS allow-list origin |

### Connection string examples

```bash
# SQLite (default — zero config)
DATABASE_URL=sqlite:///./yuno_dev.db

# PostgreSQL (Docker Compose)
DATABASE_URL=postgresql+psycopg://admin:password@postgres:5432/agent_platform

# PostgreSQL (local)
DATABASE_URL=postgresql+psycopg://admin:password@localhost:5432/agent_platform

# Redis (Docker Compose)
REDIS_URL=redis://redis:6379/0

# Redis (local)
REDIS_URL=redis://localhost:6379/0
```

---

## 5. First-Time Database Setup

### SQLite (default)

No action needed — tables are created automatically when the backend starts.

### PostgreSQL (first time only)

```bash
# Option A: via Docker Compose exec
docker-compose exec backend alembic upgrade head

# Option B: locally (backend virtual env must be active)
cd backend
alembic upgrade head
```

Verify the migration applied:
```bash
alembic history --verbose
# Should show: 001_initial_schema  (head)
```

---

## 6. Telegram Bot Setup

1. **Create a bot:**
   - Open Telegram → search `@BotFather` → send `/newbot`
   - Choose a name (e.g. `YUNO Demo Bot`) and a username (e.g. `yuno_demo_bot`)
   - Copy the token: `1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ`

2. **Configure the token:**
   ```bash
   # backend/.env
   TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
   ```

3. **Restart the backend** — the bot starts polling automatically on startup. Check logs for:
   ```
   INFO     app.integrations.telegram_bot:telegram_bot.py  Telegram bot started polling
   ```

4. **Test the bot:**
   - Open Telegram → search for your bot's username → send `/start`
   - The bot routes the message to the first active agent and replies

5. **Assign a specific agent** (optional):
   - Via Telegram: send `/config` and follow the prompts
   - Via API: update the agent's `channels` field to include `"telegram"`

---

## 7. Verifying the Stack

After startup, run these checks:

```bash
# App health
curl http://localhost:8000/api/health
# → {"status":"ok","env":"development"}

# Database connectivity
curl http://localhost:8000/api/health/db
# → {"status":"ok","db":"connected"}

# Redis connectivity
curl http://localhost:8000/api/health/redis
# → {"status":"ok","redis":"connected"} or {"status":"degraded",...} if Redis isn't running

# Create a test agent
curl -s -X POST http://localhost:8000/api/agents \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","role":"echo","system_prompt":"Repeat the input.","model":"gpt-4o-mini","tools":[],"channels":[]}' \
  | python -m json.tool

# List agents
curl http://localhost:8000/api/agents
```

If all of the above succeed, the stack is fully operational.

---

## 8. Troubleshooting

### Docker Compose startup fails with "connection refused" on backend

**Cause:** backend starts before PostgreSQL is ready.  
**Fix:** the `docker-compose.yml` uses `condition: service_healthy` — ensure you're using Docker Compose v2.

```bash
docker compose version  # must be v2+
```

---

### `alembic upgrade head` fails: "relation already exists"

**Cause:** tables were auto-created by SQLAlchemy before Alembic ran.  
**Fix:**

```bash
# Mark the migration as already applied without running SQL
alembic stamp head
```

---

### Backend starts but Telegram bot says "Invalid token"

**Cause:** `TELEGRAM_BOT_TOKEN` is wrong or has extra whitespace.  
**Fix:** verify the token in `backend/.env` — it should look like `1234567890:ABCdefGHI...` with no spaces or quotes.

---

### Frontend says "Network Error" / API calls fail

**Cause:** backend is not running, or CORS is blocking the origin.  
**Check:**

```bash
curl http://localhost:8000/api/health
```

If that fails, the backend isn't running. If it succeeds but the UI still fails, check the browser console for the exact CORS error and verify `FRONTEND_URL` in `backend/.env` matches the dev server origin.

---

### WebSocket connects but no events appear

**Cause:** the workflow execution hasn't been triggered, or the workflow ID in the URL doesn't match the one being executed.  
**Fix:**
1. Note the `workflow_id` returned by `POST /api/workflows/{id}/execute`
2. Connect the WebSocket to `/ws/logs/<that exact workflow_id>`

---

### `pytest` fails with "ModuleNotFoundError"

**Cause:** virtual environment not activated, or dependencies not installed.  
**Fix:**

```bash
cd backend
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
pytest tests/ -v
```

---

### Port 8000 or 3000 already in use

```bash
# Find what's using the port (Windows)
netstat -ano | findstr :8000

# Kill the process
taskkill /PID <pid> /F
```

```bash
# macOS / Linux
lsof -ti:8000 | xargs kill -9
```

Or change the port in `docker-compose.yml` and `backend/.env`.

---

### docker-compose up is very slow on first run

**Cause:** Docker is pulling base images and building layers for the first time.  
**Expected time:** 2–5 minutes on a typical broadband connection.  
Subsequent runs use cached layers and take ~10–15 seconds.
