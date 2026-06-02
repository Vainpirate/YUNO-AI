"""Pure-asyncio workflow scheduler.

Uses APScheduler's CronTrigger ONLY for cron expression parsing and computing
next-fire times.  The actual scheduling loop is a plain asyncio background task
so there are no event-loop conflicts with FastAPI/uvicorn's running loop.

Lifecycle
---------
Call ``await workflow_scheduler.start(db_factory)`` inside the FastAPI lifespan.
This registers all persisted workflow schedules and starts a lightweight
background task that wakes every 30 seconds to fire any due jobs.

When a workflow's schedule is updated via the API, call
``workflow_scheduler.reschedule(workflow_id, new_cron)`` to apply the change
immediately without restarting the server.

Cron syntax (standard 5-field):
    minute  hour  day_of_month  month  day_of_week
    e.g. "*/5 * * * *"  → every 5 minutes
         "0 9 * * 1-5"  → 09:00 every weekday
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

logger = logging.getLogger(__name__)


def _compute_next(cron_expr: str) -> datetime | None:
    """Return the next UTC fire time for *cron_expr*, or None on parse error."""
    try:
        from apscheduler.triggers.cron import CronTrigger  # type: ignore[import]
        trigger = CronTrigger.from_crontab(cron_expr, timezone="UTC")
        return trigger.get_next_fire_time(None, datetime.now(timezone.utc))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not parse cron expression '%s': %s", cron_expr, exc)
        return None


class WorkflowScheduler:
    """Asyncio-native workflow scheduler — no APScheduler event loop required."""

    def __init__(self) -> None:
        self._db_factory = None
        self._jobs: dict[str, str] = {}           # workflow_id → cron_expr
        self._next_run: dict[str, datetime] = {}   # workflow_id → next UTC fire time
        self._task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self, db_factory) -> None:
        """Load persisted schedules and begin the background tick loop.

        Must be awaited from inside a running asyncio event loop (e.g. FastAPI
        lifespan).  Safe to call from any async context.
        """
        self._db_factory = db_factory
        self._load_from_db()
        self._task = asyncio.create_task(self._tick_loop(), name="workflow-scheduler")
        logger.info("Workflow scheduler started (%d job(s) loaded).", len(self._jobs))

    def shutdown(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("Workflow scheduler stopped.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reschedule(self, workflow_id: str, cron_expr: str | None) -> None:
        """Add, update, or remove the cron job for *workflow_id*.

        Pass ``cron_expr=None`` or ``""`` to remove any existing schedule.
        """
        if not cron_expr or not cron_expr.strip():
            removed = workflow_id in self._jobs
            self._jobs.pop(workflow_id, None)
            self._next_run.pop(workflow_id, None)
            if removed:
                logger.info("Removed schedule for workflow %s", workflow_id)
            return

        parts = cron_expr.strip().split()
        if len(parts) != 5:
            logger.warning(
                "Invalid cron expression '%s' for workflow %s — must be 5 fields",
                cron_expr, workflow_id,
            )
            return

        next_run = _compute_next(cron_expr)
        if next_run is None:
            return

        self._jobs[workflow_id] = cron_expr
        self._next_run[workflow_id] = next_run
        logger.info(
            "Scheduled workflow %s with cron '%s' (next: %s)",
            workflow_id, cron_expr, next_run.isoformat(),
        )

    def list_scheduled(self) -> list[dict]:
        """Return info about all currently registered workflow jobs."""
        return [
            {
                "workflow_id": wf_id,
                "cron": self._jobs[wf_id],
                "next_run": self._next_run.get(wf_id, {}) and self._next_run[wf_id].isoformat(),
            }
            for wf_id in self._jobs
        ]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load_from_db(self) -> None:
        """Read workflows table and register all that have a non-null schedule."""
        if not self._db_factory:
            return
        try:
            from sqlalchemy import select
            from app.models import Workflow
            db = self._db_factory()
            try:
                workflows = list(db.scalars(
                    select(Workflow).where(Workflow.schedule.isnot(None))
                ))
                for wf in workflows:
                    if wf.schedule:
                        self.reschedule(str(wf.id), wf.schedule)
            finally:
                db.close()
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load workflow schedules from DB: %s", exc)

    async def _tick_loop(self) -> None:
        """Background loop — checks for due jobs every 30 seconds."""
        while True:
            try:
                await asyncio.sleep(30)
                await self._fire_due_jobs()
            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001
                logger.error("Scheduler tick error: %s", exc)

    async def _fire_due_jobs(self) -> None:
        """Execute all jobs whose next_run has passed."""
        now = datetime.now(timezone.utc)
        for wf_id in list(self._jobs.keys()):
            next_run = self._next_run.get(wf_id)
            if next_run is None or now < next_run:
                continue
            # Advance next_run BEFORE running so a slow job doesn't re-fire
            self._next_run[wf_id] = _compute_next(self._jobs[wf_id]) or now
            asyncio.create_task(
                self._run_workflow(wf_id),
                name=f"scheduled-wf-{wf_id[:8]}",
            )

    async def _run_workflow(self, workflow_id: str) -> None:
        """Execute a workflow by ID (called from the tick loop)."""
        logger.info("Scheduler triggering workflow %s", workflow_id)
        if not self._db_factory:
            return
        try:
            from app.models import Workflow
            from app.runtime.executor import runtime_executor
            db = self._db_factory()
            try:
                workflow = db.get(Workflow, UUID(workflow_id))
                if workflow:
                    await runtime_executor.execute_workflow(
                        db, workflow, initial_input="Scheduled execution"
                    )
                    logger.info("Scheduled execution of workflow %s completed", workflow_id)
                else:
                    logger.warning("Scheduled workflow %s not found in DB", workflow_id)
            finally:
                db.close()
        except Exception as exc:  # noqa: BLE001
            logger.error("Scheduled execution of workflow %s failed: %s", workflow_id, exc)


workflow_scheduler = WorkflowScheduler()
