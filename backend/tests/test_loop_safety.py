"""Tests for workflow loop / cycle safety."""


def _create_agent(client, name):
    resp = client.post("/api/agents", json={
        "name": name,
        "role": "test",
        "system_prompt": "Echo the input.",
        "model": "gemini-2.0-flash",
        "tools": [],
        "channels": [],
        "memory_config": {},
        "guardrails": {},
        "skills": [],
        "interaction_rules": {},
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_linear_workflow_completes(client):
    """A simple linear (acyclic) workflow should complete without issues."""
    a = _create_agent(client, "LinearA")
    b = _create_agent(client, "LinearB")

    wf = client.post("/api/workflows", json={
        "name": "linear_wf",
        "description": "linear",
        "agents": [a["id"], b["id"]],
        "graph": {"nodes": [a["id"], b["id"]], "edges": [[a["id"], b["id"]]]},
        "schedule": None,
        "max_iterations": 5,
        "template_name": None,
    }).json()

    result = client.post(f"/api/workflows/{wf['id']}/execute",
                         json={"input": "hello"})
    assert result.status_code == 200
    assert result.json()["status"] == "completed"


def test_cyclic_workflow_terminates(client):
    """A cyclic workflow (A→B→A) must terminate due to max_iterations, not hang."""
    a = _create_agent(client, "CycleA")
    b = _create_agent(client, "CycleB")

    # Build a cycle: A → B → A
    wf = client.post("/api/workflows", json={
        "name": "cyclic_wf",
        "description": "cycle",
        "agents": [a["id"], b["id"]],
        "graph": {
            "nodes": [a["id"], b["id"]],
            "edges": [[a["id"], b["id"]], [b["id"], a["id"]]],
        },
        "schedule": None,
        "max_iterations": 2,  # very low cap so test finishes quickly
        "template_name": None,
    }).json()

    result = client.post(f"/api/workflows/{wf['id']}/execute",
                         json={"input": "start"})
    # Should complete (not hang), regardless of whether it took the cycle
    assert result.status_code == 200
    assert result.json()["status"] == "completed"


def test_max_iterations_enforced(client):
    """When max_iterations=1, a back-edge node should be loop-terminated."""
    a = _create_agent(client, "IterA")

    # Self-loop: A → A
    wf = client.post("/api/workflows", json={
        "name": "selfloop_wf",
        "description": "self loop",
        "agents": [a["id"]],
        "graph": {
            "nodes": [a["id"]],
            "edges": [[a["id"], a["id"]]],
        },
        "schedule": None,
        "max_iterations": 1,
        "template_name": None,
    }).json()

    result = client.post(f"/api/workflows/{wf['id']}/execute",
                         json={"input": "loop me"})
    assert result.status_code == 200
    body = result.json()
    assert body["status"] == "completed"
    # The final output should mention loop termination
    assert "loop" in body["final_output"].lower() or body["steps"] <= 2


def test_workflow_with_max_iterations_set(client):
    """max_iterations is persisted and returned by the API."""
    a = _create_agent(client, "IterB")
    wf = client.post("/api/workflows", json={
        "name": "iter_wf",
        "description": "iter",
        "agents": [a["id"]],
        "graph": {"nodes": [a["id"]], "edges": []},
        "schedule": None,
        "max_iterations": 7,
        "template_name": None,
    }).json()
    assert wf["max_iterations"] == 7


def test_conditional_branching_still_works(client):
    """Conditional edges should still route correctly in a non-cyclic workflow."""
    a = _create_agent(client, "CondA")
    b = _create_agent(client, "CondB")

    wf = client.post("/api/workflows", json={
        "name": "cond_wf",
        "description": "cond",
        "agents": [a["id"], b["id"]],
        "graph": {
            "nodes": [a["id"], b["id"]],
            "edges": [[a["id"], b["id"], "hello"]],
        },
        "schedule": None,
        "max_iterations": 5,
        "template_name": None,
    }).json()

    result = client.post(f"/api/workflows/{wf['id']}/execute",
                         json={"input": "hello world"})
    assert result.status_code == 200
    assert result.json()["status"] == "completed"
