"""Telegram bot integration — Phase 4.

Architecture
-----------
* ``TelegramBotIntegration`` wraps python-telegram-bot (v21+, async API).
* The bot is started as a background asyncio task inside FastAPI's lifespan.
* Each incoming message is routed to the agent assigned to that Telegram user.
* Agent assignment is persisted in Redis (key: ``telegram_user:{user_id}:agent_id``).
  If Redis is unavailable or no assignment exists, the first available agent is used.
* Every inbound/outbound message is stored in the ``message_history`` table.
* WebSocket subscribers receive a real-time event after each agent response.

Commands
--------
/start          — Welcome message + current agent info
/agents         — List all agents available in the platform
/assign <name>  — Connect your chat to a specific agent
/config         — Show your current agent assignment details
"""
from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Agent, MessageHistory
from app.runtime.executor import runtime_executor
from app.websocket.broadcaster import broadcaster

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: agent→Telegram user mapping (Redis-backed, in-memory fallback)
# ---------------------------------------------------------------------------

# In-memory fallback used when Redis is unavailable — survives for the
# duration of the current server process.
_local_mapping: dict[int, str] = {}


def _get_agent_mapping(telegram_user_id: int) -> str | None:
    """Return agent_id string for a Telegram user, or None if not set."""
    try:
        from redis import Redis
        r = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)
        val = r.get(f"telegram_user:{telegram_user_id}:agent_id")
        if val:
            return val
    except Exception:
        pass
    # Redis unavailable — use in-process fallback
    return _local_mapping.get(telegram_user_id)


def _set_agent_mapping(telegram_user_id: int, agent_id: str) -> None:
    """Persist agent assignment for a Telegram user (Redis + in-memory fallback)."""
    # Always update local mapping so it works without Redis
    _local_mapping[telegram_user_id] = agent_id
    try:
        from redis import Redis
        r = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)
        r.set(f"telegram_user:{telegram_user_id}:agent_id", agent_id)
        logger.debug("Mapped Telegram user %s -> agent %s (Redis)", telegram_user_id, agent_id)
    except Exception:
        logger.debug("Redis unavailable — agent mapping saved in-memory only")


def _resolve_agent(db: Session, telegram_user_id: int) -> Agent | None:
    """Return the agent assigned to this user, or the first active agent as fallback."""
    agent_id_str = _get_agent_mapping(telegram_user_id)
    if agent_id_str:
        try:
            agent = db.get(Agent, UUID(agent_id_str))
            if agent:
                return agent
        except Exception:
            pass
    # Fallback: first agent created
    return db.scalar(select(Agent).order_by(Agent.created_at.asc()).limit(1))


def _store_history(
    db: Session,
    telegram_user_id: int,
    username: str | None,
    agent_id: UUID,
    direction: str,
    content: str,
    metadata: dict | None = None,
) -> None:
    row = MessageHistory(
        channel_user_id=f"telegram:{telegram_user_id}",
        agent_id=agent_id,
        direction=direction,
        content=content,
        metadata_json={
            "source": "telegram",
            "username": username or "",
            **(metadata or {}),
        },
    )
    db.add(row)
    db.commit()


# ---------------------------------------------------------------------------
# Main integration class
# ---------------------------------------------------------------------------

class TelegramBotIntegration:
    """Bridges Telegram messages to the YUNO agent runtime."""

    def __init__(self, bot_token: str) -> None:
        self.bot_token = bot_token
        self._app = None  # built lazily

    # ------------------------------------------------------------------
    # PTB Application (built lazily so import errors don't crash startup)
    # ------------------------------------------------------------------

    def _build_app(self):
        from telegram.ext import (
            Application,
            CommandHandler,
            MessageHandler,
            filters,
        )
        app = (
            Application.builder()
            .token(self.bot_token)
            .connect_timeout(30)
            .read_timeout(30)
            .write_timeout(30)
            .pool_timeout(30)
            .build()
        )
        app.add_handler(CommandHandler("start", self._handle_start))
        app.add_handler(CommandHandler("agents", self._handle_list_agents))
        app.add_handler(CommandHandler("assign", self._handle_assign))
        app.add_handler(CommandHandler("config", self._handle_config))
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )
        return app

    def _get_app(self):
        if self._app is None:
            self._app = self._build_app()
        return self._app

    # ------------------------------------------------------------------
    # Command: /start
    # ------------------------------------------------------------------

    async def _handle_start(self, update, context) -> None:
        user_id = update.effective_user.id
        db = SessionLocal()
        try:
            agent = _resolve_agent(db, user_id)
            if agent:
                await update.message.reply_text(
                    f"Welcome to YUNO AI!\n\n"
                    f"You are connected to agent: {agent.name}\n"
                    f"Role: {agent.role or 'General assistant'}\n\n"
                    f"Just send a message to start chatting.\n"
                    f"/agents - list all agents\n"
                    f"/assign <name> - switch agent\n"
                    f"/config - show your current config",
                )
            else:
                await update.message.reply_text(
                    "Welcome to YUNO AI!\n\n"
                    "No agents have been created yet.\n"
                    f"Please create an agent at the web UI first:\n{settings.frontend_url}",
                )
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Command: /agents
    # ------------------------------------------------------------------

    async def _handle_list_agents(self, update, context) -> None:
        db = SessionLocal()
        try:
            agents = list(db.scalars(select(Agent).order_by(Agent.name)))
            if not agents:
                await update.message.reply_text(
                    "No agents found. Create one at:\n" + settings.frontend_url
                )
                return
            lines = ["Available Agents:\n"]
            for a in agents:
                tools_str = ", ".join(a.tools) if a.tools else "none"
                lines.append(f"- {a.name} ({a.role or 'No role'}) | tools: {tools_str}")
            lines.append("\nUse /assign <name> to connect to an agent.")
            await update.message.reply_text("\n".join(lines))
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Command: /assign <name>
    # ------------------------------------------------------------------

    async def _handle_assign(self, update, context) -> None:
        if not context.args:
            await update.message.reply_text("Usage: /assign <agent_name>")
            return

        agent_name = " ".join(context.args)
        db = SessionLocal()
        try:
            agent = db.scalar(select(Agent).where(Agent.name == agent_name))
            if not agent:
                await update.message.reply_text(
                    f"Agent '{agent_name}' not found.\nUse /agents to see available agents."
                )
                return

            user_id = update.effective_user.id
            _set_agent_mapping(user_id, str(agent.id))
            await update.message.reply_text(
                f"You are now connected to: {agent.name}\n"
                f"Role: {agent.role or '-'}\n"
                f"Tools: {', '.join(agent.tools) if agent.tools else 'none'}\n\n"
                "Start chatting!"
            )
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Command: /config
    # ------------------------------------------------------------------

    async def _handle_config(self, update, context) -> None:
        user_id = update.effective_user.id
        db = SessionLocal()
        try:
            agent = _resolve_agent(db, user_id)
            if not agent:
                await update.message.reply_text("No agent assigned. Use /agents then /assign <name>.")
                return
            await update.message.reply_text(
                f"Your Current Config\n\n"
                f"Agent: {agent.name}\n"
                f"Role: {agent.role or '-'}\n"
                f"Model: {agent.model or 'default'}\n"
                f"Tools: {', '.join(agent.tools) if agent.tools else 'none'}\n\n"
                "Use /assign <name> to switch agents.",
            )
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Main message handler
    # ------------------------------------------------------------------

    async def _handle_message(self, update, context) -> None:
        """Route incoming text to the assigned agent and reply."""
        user_id = update.effective_user.id
        username = update.effective_user.username
        text = update.message.text

        db = SessionLocal()
        try:
            agent = _resolve_agent(db, user_id)
            if not agent:
                await update.message.reply_text(
                    "No agents configured.\n"
                    f"Please create one at: {settings.frontend_url}"
                )
                return

            # Persist inbound
            _store_history(db, user_id, username, agent.id, "inbound", text)

            # Show typing indicator (best-effort — timeout must not block the reply)
            try:
                await context.bot.send_chat_action(
                    chat_id=update.effective_chat.id, action="typing"
                )
            except Exception:
                pass

            # Execute agent
            try:
                result = await runtime_executor.execute_agent(
                    db=db,
                    agent=agent,
                    user_input=text,
                    workflow_id=None,
                )
                response_text: str = result.get("response", "") or "(no response)"
                tokens_used: int = result.get("tokens_used", 0)
                cost: float = result.get("cost", 0.0)
            except Exception as exc:
                logger.exception("Agent execution error for Telegram message")
                response_text = f"Agent error: {exc}"
                tokens_used = 0
                cost = 0.0

            # Reply
            await update.message.reply_text(response_text)

            # Persist outbound
            _store_history(
                db, user_id, username, agent.id, "outbound", response_text,
                {"tokens_used": tokens_used, "cost": cost},
            )

            # Broadcast to WebSocket subscribers (live monitoring in UI)
            await broadcaster.broadcast_telegram_event({
                "type": "telegram_message",
                "telegram_user_id": user_id,
                "telegram_username": username or "",
                "agent_id": str(agent.id),
                "agent_name": agent.name,
                "input": text,
                "response": response_text,
                "tokens_used": tokens_used,
                "cost": cost,
            })

        except Exception as exc:
            logger.exception("Unhandled error in Telegram message handler")
            try:
                await update.message.reply_text("An unexpected error occurred. Please try again.")
            except Exception:
                pass
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Start long-polling with automatic restart on transient errors."""
        if not self.bot_token:
            logger.info("TELEGRAM_BOT_TOKEN not configured -- Telegram integration disabled.")
            return

        retry_delay = 5  # seconds between restart attempts
        while True:
            logger.info("Starting Telegram bot (long polling)...")
            try:
                self._app = None  # force fresh build on each attempt
                app = self._get_app()
                async with app:
                    await app.start()
                    await app.updater.start_polling(drop_pending_updates=True)
                    logger.info("Telegram bot is live. Send /start to your bot to begin.")
                    stop_event = asyncio.Event()
                    await stop_event.wait()
            except asyncio.CancelledError:
                logger.info("Telegram bot polling stopped (task cancelled).")
                break
            except Exception as exc:
                logger.warning("Telegram bot error: %s — retrying in %ds", exc, retry_delay)
                self._app = None
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)  # exponential back-off, cap at 60s
                continue
            finally:
                try:
                    if self._app and self._app.updater.running:
                        await self._app.updater.stop()
                    if self._app and self._app.running:
                        await self._app.stop()
                except Exception:
                    pass
                self._app = None


# ---------------------------------------------------------------------------
# Module-level singleton — imported by main.py lifespan
# ---------------------------------------------------------------------------
telegram_bot = TelegramBotIntegration(bot_token=settings.telegram_bot_token)
