def test_message_delivery_and_logs(client):
    agent = client.post(
        "/api/agents",
        json={
            "name": "Messenger",
            "role": "math",
            "system_prompt": "Compute",
            "model": "gpt-4o-mini",
            "tools": ["calculator"],
            "channels": [],
            "memory_config": {},
            "guardrails": {},
        },
    ).json()

    workflow = client.post(
        "/api/workflows",
        json={
            "name": "msg_wf",
            "description": "msg",
            "agents": [agent["id"]],
            "graph": {"nodes": [agent["id"]], "edges": []},
            "schedule": None,
            "template_name": None,
        },
    ).json()

    executed = client.post(
        f"/api/agents/{agent['id']}/execute",
        json={"input": "25*4", "workflow_id": workflow["id"]},
    )
    assert executed.status_code == 200
    assert executed.json()["response"] == "100"

    messages = client.get(f"/api/messages/{workflow['id']}")
    assert messages.status_code == 200
    assert len(messages.json()) >= 1

    logs = client.get(f"/api/execution/{workflow['id']}/logs")
    assert logs.status_code == 200
    assert len(logs.json()) >= 1
