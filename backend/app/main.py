"""FastAPI application entry point.

Lifespan
--------
On startup:
  1. Create all SQLAlchemy tables (if they don't exist).
  2. Register external tools (datetime_now, random_fact, word_count, etc.)
     into the shared ToolRegistry so every agent can use them.
  3. Start the Telegram bot as a background asyncio task.
     - If TELEGRAM_BOT_TOKEN is empty the task exits immediately (no error).

On shutdown:
  4. Cancel the Telegram polling task gracefully.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routes import agents, execution, messages, workflows
from app.websocket import handlers as ws_handlers

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lifespan context manager
# ---------------------------------------------------------------------------

def _migrate_db() -> None:
    """Add columns introduced after the initial schema without dropping data.

    SQLAlchemy's create_all only creates missing *tables* — it never alters
    existing ones.  This function issues idempotent ALTER TABLE statements for
    every column added since v1.0 so developers with an old yuno_dev.db don't
    have to wipe their data.
    """
    from sqlalchemy import text
    migrations = [
        # v1.1 — agent skills + interaction rules
        ("agents",    "skills",            "TEXT"),
        ("agents",    "interaction_rules", "TEXT"),
        # v1.2 — workflow loop safety
        ("workflows", "max_iterations",    "INTEGER DEFAULT 10"),
    ]
    with engine.connect() as conn:
        for table, column, col_type in migrations:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                conn.commit()
                logger.info("Migration applied: %s.%s", table, column)
            except Exception:  # column already exists — safe to ignore
                pass


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────
    # 1. DB tables + incremental column migrations
    Base.metadata.create_all(bind=engine)
    _migrate_db()
    logger.info("Database tables verified/migrated.")

    # 2. External tools
    from app.integrations.external_tools import register_external_tools
    from app.runtime.executor import runtime_executor
    register_external_tools(runtime_executor.tools)

    # 3. Telegram bot background task
    from app.integrations.telegram_bot import telegram_bot
    tg_task = asyncio.create_task(telegram_bot.run(), name="telegram-bot")
    logger.info("Telegram bot task started.")

    # 4. Workflow scheduler (asyncio background task — non-blocking)
    from app.scheduler import workflow_scheduler
    from app.database import SessionLocal
    await workflow_scheduler.start(SessionLocal)
    logger.info("Workflow scheduler initialised.")

    yield  # ← application runs here

    # ── Shutdown ─────────────────────────────────────────────────────────
    tg_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await tg_task
    logger.info("Telegram bot task stopped.")

    workflow_scheduler.shutdown()
    logger.info("Workflow scheduler stopped.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "env": settings.app_env}


@app.get("/api/health/db")
def health_db():
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as exc:
        return {"status": "error", "db": str(exc)}


@app.get("/api/health/redis")
def health_redis():
    try:
        from redis import Redis
        r = Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
        return {"status": "ok", "redis": "connected"}
    except Exception as exc:
        return {"status": "degraded", "redis": str(exc)}


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(agents.router)
app.include_router(workflows.router)
app.include_router(messages.router)
app.include_router(execution.router)
app.include_router(ws_handlers.router)
