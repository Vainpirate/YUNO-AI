"""Tests for guardrails enforcement at runtime."""


def _make_agent(client, name, guardrails, tools=None):
    payload = {
        "name": name,
        "role": "test",
        "system_prompt": "You are a test agent.",
        "model": "gemini-2.0-flash",
        "tools": tools or [],
        "channels": [],
        "memory_config": {},
        "guardrails": guardrails,
        "skills": [],
        "interaction_rules": {},
    }
    resp = client.post("/api/agents", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _make_workflow(client, agent_id):
    resp = client.post(
        "/api/workflows",
        json={
            "name": f"wf_{agent_id[:8]}",
            "description": "guardrail test",
            "agents": [agent_id],
            "graph": {"nodes": [agent_id], "edges": []},
            "schedule": None,
            "max_iterations": 10,
            "template_name": None,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_banned_keyword_blocks_input(client):
    """Agent with banned keyword 'violence' should block inputs containing that word."""
    agent = _make_agent(
        client,
        "GuardAgent1",
        guardrails={"banned_keywords": ["violence"], "blocked_topics": []},
    )
    wf = _make_workflow(client, agent["id"])

    result = client.post(
        f"/api/agents/{agent['id']}/execute",
        json={"input": "tell me about violence", "workflow_id": wf["id"]},
    )
    assert result.status_code == 200
    body = result.json()
    # Response should be a guardrail block message
    assert body["guardrail_blocked"] is True
    assert "Guardrail" in body["response"] or "guardrail" in body["response"].lower()


def test_clean_input_passes_guardrail(client):
    """Input without banned keywords should not be blocked."""
    agent = _make_agent(
        client,
        "GuardAgent2",
        guardrails={"banned_keywords": ["violence"], "blocked_topics": []},
        tools=["calculator"],
    )
    wf = _make_workflow(client, agent["id"])

    result = client.post(
        f"/api/agents/{agent['id']}/execute",
        json={"input": "2+2", "workflow_id": wf["id"]},
    )
    assert result.status_code == 200
    body = result.json()
    assert body.get("guardrail_blocked") is False
    assert body["response"] == "4"


def test_blocked_topic_blocks_input(client):
    """Blocked topics behave like banned keywords."""
    agent = _make_agent(
        client,
        "GuardAgent3",
        guardrails={"banned_keywords": [], "blocked_topics": ["gambling"]},
    )
    wf = _make_workflow(client, agent["id"])

    result = client.post(
        f"/api/agents/{agent['id']}/execute",
        json={"input": "How can I win at gambling?", "workflow_id": wf["id"]},
    )
    assert result.status_code == 200
    body = result.json()
    assert body["guardrail_blocked"] is True


def test_max_input_tokens_blocks_long_input(client):
    """Inputs that exceed max_input_tokens should be blocked."""
    agent = _make_agent(
        client,
        "GuardAgent4",
        guardrails={"max_input_tokens": 5},  # very low cap ~3 words
    )
    wf = _make_workflow(client, agent["id"])

    long_input = " ".join(["word"] * 20)  # 20 words ≈ 26 tokens >> 5
    result = client.post(
        f"/api/agents/{agent['id']}/execute",
        json={"input": long_input, "workflow_id": wf["id"]},
    )
    assert result.status_code == 200
    body = result.json()
    assert body["guardrail_blocked"] is True


def test_no_guardrails_passes_everything(client):
    """Agent with empty guardrails dict should not block any input."""
    agent = _make_agent(
        client,
        "GuardAgent5",
        guardrails={},
        tools=["calculator"],
    )
    wf = _make_workflow(client, agent["id"])

    result = client.post(
        f"/api/agents/{agent['id']}/execute",
        json={"input": "10*10", "workflow_id": wf["id"]},
    )
    assert result.status_code == 200
    body = result.json()
    assert body.get("guardrail_blocked") is False
    assert body["response"] == "100"


def test_guardrail_execution_log_status(client):
    """Blocked steps should record 'guardrail_blocked' status in execution logs."""
    agent = _make_agent(
        client,
        "GuardAgent6",
        guardrails={"banned_keywords": ["test_block_kw"]},
    )
    wf = _make_workflow(client, agent["id"])

    client.post(
        f"/api/agents/{agent['id']}/execute",
        json={"input": "test_block_kw in message", "workflow_id": wf["id"]},
    )

    logs = client.get(f"/api/execution/{wf['id']}/logs")
    assert logs.status_code == 200
    statuses = [log["status"] for log in logs.json()]
    assert "guardrail_blocked" in statuses
