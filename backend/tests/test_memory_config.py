"""Tests for agent memory configuration."""
from app.runtime.memory import MemoryStore


def test_memory_store_default_window():
    """Default window size should be MemoryStore.WINDOW (20)."""
    store = MemoryStore()
    agent_id = "agent-test-1"
    for i in range(25):
        store.append(agent_id, f"message {i}")
    history = store.get(agent_id)
    assert len(history) == MemoryStore.WINDOW


def test_memory_store_custom_window():
    """Custom window size should cap the stored messages."""
    store = MemoryStore()
    agent_id = "agent-test-2"
    for i in range(30):
        store.append(agent_id, f"message {i}", window=6)
    history = store.get(agent_id)
    assert len(history) == 6
    assert history[-1] == "message 29"


def test_memory_store_small_window():
    """Window of 2 keeps only the last 2 messages."""
    store = MemoryStore()
    agent_id = "agent-test-3"
    store.append(agent_id, "first", window=2)
    store.append(agent_id, "second", window=2)
    store.append(agent_id, "third", window=2)
    history = store.get(agent_id)
    assert history == ["second", "third"]


def test_memory_store_clear():
    """Clear should remove all messages for an agent."""
    store = MemoryStore()
    agent_id = "agent-test-4"
    store.append(agent_id, "hello")
    store.clear(agent_id)
    assert store.get(agent_id) == []


def test_agent_memory_config_persisted(client):
    """memory_config with window_size should be stored and returned correctly."""
    payload = {
        "name": "MemAgent",
        "role": "test",
        "system_prompt": "Test",
        "model": "gemini-2.0-flash",
        "tools": [],
        "channels": [],
        "memory_config": {"window_size": 5, "memory_type": "sliding_window"},
        "guardrails": {},
        "skills": [],
        "interaction_rules": {},
    }
    agent = client.post("/api/agents", json=payload).json()
    assert agent["memory_config"]["window_size"] == 5
    assert agent["memory_config"]["memory_type"] == "sliding_window"

    fetched = client.get(f"/api/agents/{agent['id']}").json()
    assert fetched["memory_config"]["window_size"] == 5


def test_as_messages_format(client):
    """as_messages should return alternating user/assistant role dicts."""
    store = MemoryStore()
    agent_id = "agent-msg-fmt"
    store.append(agent_id, "user says hello")
    store.append(agent_id, "assistant says hi")
    store.append(agent_id, "user asks question")
    msgs = store.as_messages(agent_id)
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"
    assert msgs[2]["role"] == "user"
    assert msgs[0]["content"] == "user says hello"
