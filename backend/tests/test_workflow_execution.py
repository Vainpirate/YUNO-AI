def test_workflow_execution(client):
    a1 = client.post(
        "/api/agents",
        json={
            "name": "AgentA",
            "role": "math",
            "system_prompt": "Compute",
            "model": "gemini-2.0-flash",
            "tools": ["calculator"],
            "channels": [],
            "memory_config": {},
            "guardrails": {},
        },
    ).json()

    a2 = client.post(
        "/api/agents",
        json={
            "name": "AgentB",
            "role": "echo",
            "system_prompt": "Summarize",
            "model": "gemini-2.0-flash",
            "tools": [],
            "channels": [],
            "memory_config": {},
            "guardrails": {},
        },
    ).json()

    wf = client.post(
        "/api/workflows",
        json={
            "name": "wf1",
            "description": "test",
            "agents": [a1["id"], a2["id"]],
            "graph": {"nodes": [a1["id"], a2["id"]], "edges": [[a1["id"], a2["id"]]]},
            "schedule": None,
            "template_name": "research_summarize",
        },
    )
    assert wf.status_code == 200
    wf_id = wf.json()["id"]

    executed = client.post(f"/api/workflows/{wf_id}/execute")
    assert executed.status_code == 200
    assert executed.json()["status"] == "completed"

    status = client.get(f"/api/workflows/{wf_id}/status")
    assert status.status_code == 200
    assert status.json()["status"] == "completed"
