"""Tests for workflow schedule management."""


def _create_workflow(client, name, agents=None, schedule=None):
    agents = agents or []
    resp = client.post("/api/workflows", json={
        "name": name,
        "description": "schedule test",
        "agents": agents,
        "graph": {"nodes": agents, "edges": []},
        "schedule": schedule,
        "max_iterations": 10,
        "template_name": None,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_workflow_created_with_schedule(client):
    """Workflow schedule is persisted at creation time."""
    wf = _create_workflow(client, "SchedWF1", schedule="0 9 * * 1-5")
    assert wf["schedule"] == "0 9 * * 1-5"


def test_workflow_created_without_schedule(client):
    """Workflow with no schedule should have null schedule."""
    wf = _create_workflow(client, "SchedWF2", schedule=None)
    assert wf["schedule"] is None


def test_set_schedule_endpoint(client):
    """POST /{id}/schedule should update and persist the cron expression."""
    wf = _create_workflow(client, "SchedWF3")
    resp = client.post(f"/api/workflows/{wf['id']}/schedule",
                       json={"schedule": "*/10 * * * *"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["schedule"] == "*/10 * * * *"

    # Verify persisted
    fetched = client.get(f"/api/workflows/{wf['id']}").json()
    assert fetched["schedule"] == "*/10 * * * *"


def test_clear_schedule_endpoint(client):
    """Passing null/empty schedule should remove the schedule."""
    wf = _create_workflow(client, "SchedWF4", schedule="0 8 * * *")
    resp = client.post(f"/api/workflows/{wf['id']}/schedule",
                       json={"schedule": None})
    assert resp.status_code == 200

    fetched = client.get(f"/api/workflows/{wf['id']}").json()
    assert fetched["schedule"] is None


def test_schedule_update_via_put(client):
    """Schedule can be updated via the standard PUT endpoint."""
    wf = _create_workflow(client, "SchedWF5")
    updated = client.put(f"/api/workflows/{wf['id']}",
                         json={"schedule": "0 0 * * 0"}).json()
    assert updated["schedule"] == "0 0 * * 0"


def test_list_scheduled_workflows_endpoint(client):
    """GET /scheduled/list should return a list (may be empty in test env)."""
    resp = client.get("/api/workflows/scheduled/list")
    assert resp.status_code == 200
    body = resp.json()
    assert "scheduled" in body
    assert isinstance(body["scheduled"], list)


def test_max_iterations_default(client):
    """Workflow max_iterations should default to 10."""
    wf = _create_workflow(client, "SchedWF6")
    assert wf["max_iterations"] == 10


def test_max_iterations_custom(client):
    """Custom max_iterations should be persisted."""
    resp = client.post("/api/workflows", json={
        "name": "MaxIterWF",
        "description": "loop test",
        "agents": [],
        "graph": {"nodes": [], "edges": []},
        "schedule": None,
        "max_iterations": 3,
        "template_name": None,
    })
    assert resp.status_code == 200
    wf = resp.json()
    assert wf["max_iterations"] == 3
