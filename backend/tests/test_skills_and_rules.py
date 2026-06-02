"""Tests for agent skills and interaction rules."""


def _create_agent(client, name, skills=None, interaction_rules=None):
    payload = {
        "name": name,
        "role": "test",
        "system_prompt": "You are a test agent.",
        "model": "gemini-2.0-flash",
        "tools": [],
        "channels": [],
        "memory_config": {},
        "guardrails": {},
        "skills": skills or [],
        "interaction_rules": interaction_rules or {},
    }
    resp = client.post("/api/agents", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_skills_persisted(client):
    """Skills should be stored and returned correctly."""
    skills = [
        {"name": "summarize", "description": "Summarizes long text", "enabled": True},
        {"name": "translate", "description": "Translates text", "enabled": False},
    ]
    agent = _create_agent(client, "SkillAgent1", skills=skills)
    assert len(agent["skills"]) == 2
    assert agent["skills"][0]["name"] == "summarize"
    assert agent["skills"][1]["enabled"] is False


def test_skills_update(client):
    """Skills should be updatable via PUT."""
    agent = _create_agent(client, "SkillAgent2", skills=[
        {"name": "old_skill", "description": "Old", "enabled": True}
    ])
    updated = client.put(f"/api/agents/{agent['id']}", json={
        "skills": [{"name": "new_skill", "description": "New", "enabled": True}]
    }).json()
    assert len(updated["skills"]) == 1
    assert updated["skills"][0]["name"] == "new_skill"


def test_interaction_rules_persisted(client):
    """Interaction rules should be stored and returned correctly."""
    rules = {
        "response_format": "json",
        "language": "Spanish",
        "temperature": 0.5,
        "max_turns": 5,
    }
    agent = _create_agent(client, "RulesAgent1", interaction_rules=rules)
    assert agent["interaction_rules"]["response_format"] == "json"
    assert agent["interaction_rules"]["language"] == "Spanish"
    assert agent["interaction_rules"]["temperature"] == 0.5
    assert agent["interaction_rules"]["max_turns"] == 5


def test_interaction_rules_update(client):
    """Interaction rules should be updatable via PUT."""
    agent = _create_agent(client, "RulesAgent2", interaction_rules={"response_format": "text"})
    updated = client.put(f"/api/agents/{agent['id']}", json={
        "interaction_rules": {"response_format": "markdown", "temperature": 0.9}
    }).json()
    assert updated["interaction_rules"]["response_format"] == "markdown"
    assert updated["interaction_rules"]["temperature"] == 0.9


def test_empty_skills_and_rules_defaults(client):
    """Agents without skills/rules should default to empty list/dict."""
    payload = {
        "name": "DefaultAgent",
        "role": "test",
        "system_prompt": "Test",
        "model": "gemini-2.0-flash",
        "tools": [], "channels": [],
        "memory_config": {}, "guardrails": {},
    }
    resp = client.post("/api/agents", json=payload)
    assert resp.status_code == 200
    agent = resp.json()
    assert agent["skills"] == []
    assert agent["interaction_rules"] == {}


def test_disabled_skill_not_blocking(client):
    """An agent with a disabled skill should still execute normally."""
    skills = [{"name": "translate", "description": "Translates", "enabled": False}]
    agent = _create_agent(client, "SkillAgent3", skills=skills)

    wf = client.post("/api/workflows", json={
        "name": f"skill_wf_{agent['id'][:8]}",
        "description": "skill test",
        "agents": [agent["id"]],
        "graph": {"nodes": [agent["id"]], "edges": []},
        "schedule": None, "max_iterations": 10, "template_name": None,
    }).json()

    result = client.post(f"/api/agents/{agent['id']}/execute",
                         json={"input": "hello", "workflow_id": wf["id"]})
    assert result.status_code == 200
