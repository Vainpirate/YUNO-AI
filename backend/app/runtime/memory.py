from __future__ import annotations

from collections import defaultdict


class MemoryStore:
    """Per-agent in-process conversation memory with a sliding window.

    Messages are stored as plain strings in alternating user/assistant order.
    The ``as_messages`` helper converts them to the OpenAI chat-completion
    format so they can be forwarded directly to the LLM.
    """

    WINDOW: int = 20  # keep last N individual messages (10 turns)

    def __init__(self) -> None:
        self._store: dict[str, list[str]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def append(self, agent_id: str, message: str) -> None:
        buf = self._store[agent_id]
        buf.append(message)
        # Trim to window size to prevent unbounded growth
        if len(buf) > self.WINDOW:
            self._store[agent_id] = buf[-self.WINDOW :]

    def clear(self, agent_id: str) -> None:
        self._store.pop(agent_id, None)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, agent_id: str) -> list[str]:
        return list(self._store[agent_id])

    def as_messages(self, agent_id: str) -> list[dict[str, str]]:
        """Return history as an OpenAI-compatible message list.

        Messages alternate user / assistant starting from the oldest entry.
        The returned list can be prepended with a system message and sent
        directly to ``openai.chat.completions.create``.
        """
        history = self.get(agent_id)
        messages: list[dict[str, str]] = []
        for i, text in enumerate(history):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append({"role": role, "content": text})
        return messages
