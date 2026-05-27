from __future__ import annotations

import asyncio
from collections import defaultdict

from fastapi import WebSocket


class WebSocketBroadcaster:
    def __init__(self) -> None:
        self._workflow_subs: dict[str, set[WebSocket]] = defaultdict(set)
        self._agent_subs: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe_workflow(self, workflow_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._workflow_subs[workflow_id].add(websocket)

    async def subscribe_agent(self, agent_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._agent_subs[agent_id].add(websocket)

    async def unsubscribe(self, websocket: WebSocket) -> None:
        async with self._lock:
            for bucket in (self._workflow_subs, self._agent_subs):
                for key in list(bucket.keys()):
                    bucket[key].discard(websocket)
                    if not bucket[key]:
                        del bucket[key]

    async def publish_workflow_log(self, workflow_id: str, payload: dict) -> None:
        for ws in list(self._workflow_subs.get(workflow_id, [])):
            await ws.send_json(payload)

    async def publish_agent_status(self, agent_id: str, payload: dict) -> None:
        for ws in list(self._agent_subs.get(agent_id, [])):
            await ws.send_json(payload)

    async def broadcast_telegram_event(self, payload: dict) -> None:
        """Push a Telegram channel event to all workflow and agent subscribers.

        Telegram messages are not tied to a single workflow, so we fan the
        event out to every active subscriber so the monitoring UI can display
        live Telegram activity regardless of which workflow view is open.
        """
        all_sockets: set = set()
        for bucket in (self._workflow_subs, self._agent_subs):
            for sockets in bucket.values():
                all_sockets.update(sockets)
        for ws in list(all_sockets):
            try:
                await ws.send_json(payload)
            except Exception:
                pass  # stale connection — unsubscribe will clean it up


broadcaster = WebSocketBroadcaster()
