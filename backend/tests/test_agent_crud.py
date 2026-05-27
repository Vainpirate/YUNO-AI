def test_agent_crud(client):
    payload = {
        "name": "Researcher",
        "role": "research",
        "system_prompt": "Find facts",
        "model": "gpt-4o-mini",
        "tools": ["calculator"],
        "channels": ["telegram"],
        "memory_config": {},
        "guardrails": {},
    }
    created = client.post("/api/agents", json=payload)
    assert created.status_code == 200
    agent = created.json()
    agent_id = agent["id"]

    listed = client.get("/api/agents")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = client.put(f"/api/agents/{agent_id}", json={"role": "senior_research"})
    assert updated.status_code == 200
    assert updated.json()["role"] == "senior_research"

    tool_patch = client.patch(f"/api/agents/{agent_id}/tools", json={"tools": ["calculator", "web_search"]})
    assert tool_patch.status_code == 200
    assert "web_search" in tool_patch.json()["tools"]

    deleted = client.delete(f"/api/agents/{agent_id}")
    assert deleted.status_code == 200
