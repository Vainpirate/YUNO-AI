from __future__ import annotations

import json
import logging
from uuid import uuid4

logger = logging.getLogger(__name__)


class MessagingBus:
    """Redis-backed inter-agent message queue.

    The Redis connection is created lazily on first use so that the app can
    start and serve requests even when Redis is not running.  Operations
    gracefully log warnings rather than raising if Redis is unavailable.
    """

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._redis = None  # lazy connection

    def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            from redis import Redis
            self._redis = Redis.from_url(self._redis_url, decode_responses=True)
            self._redis.ping()  # fail fast if unreachable
            return self._redis
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis unavailable (%s) — messaging bus disabled", exc)
            self._redis = None
            return None

    def send_internal_message(
        self,
        from_agent_id: str,
        to_agent_id: str,
        message: str,
        workflow_id: str,
    ) -> dict:
        payload = {
            "id": str(uuid4()),
            "from": from_agent_id,
            "to": to_agent_id,
            "content": message,
            "workflow_id": workflow_id,
        }
        r = self._get_redis()
        if r:
            try:
                r.lpush(f"agent:{to_agent_id}:queue", json.dumps(payload))
            except Exception as exc:  # noqa: BLE001
                logger.warning("MessagingBus.send failed: %s", exc)
        return payload

    def receive_message(self, agent_id: str) -> dict | None:
        r = self._get_redis()
        if not r:
            return None
        try:
            raw = r.rpop(f"agent:{agent_id}:queue")
            return json.loads(raw) if raw else None
        except Exception as exc:  # noqa: BLE001
            logger.warning("MessagingBus.receive failed: %s", exc)
            return None
