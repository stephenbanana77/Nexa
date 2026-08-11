"""Workflow API tests."""


def _create_workflow(client, auth_headers, project_id):
    resp = client.post(f"/api/workflows", json={
        "project_id": project_id,
        "name": "My First WF",
        "description": "A test workflow",
        "steps": [
            {"type": "sql", "config": {"query": "SELECT * FROM data LIMIT 10"}, "sort_order": 0},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My First WF"
    assert "id" in data
    return data["id"]


def test_create_workflow(client, auth_headers, project_id):
    _create_workflow(client, auth_headers, project_id)


def test_list_workflows(client, auth_headers, project_id):
    _create_workflow(client, auth_headers, project_id)
    resp = client.get(f"/api/workflows/{project_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_get_workflow_detail(client, auth_headers, project_id):
    wf_id = _create_workflow(client, auth_headers, project_id)
    resp = client.get(f"/api/workflows/detail/{wf_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "My First WF"
    assert len(data["steps"]) == 1


def test_update_workflow(client, auth_headers, project_id):
    wf_id = _create_workflow(client, auth_headers, project_id)
    resp = client.put(f"/api/workflows/{wf_id}", json={
        "name": "Updated WF",
        "steps": [
            {"type": "sql", "config": {"query": "SELECT * FROM data"}, "sort_order": 0},
            {"type": "analyze", "config": {}, "sort_order": 1},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated WF"


def test_chat_to_workflow(client, auth_headers, project_id):
    resp = client.post(f"/api/workflows/chat-to-workflow", json={
        "project_id": project_id,
        "question": "Show top 5",
        "sql": "SELECT * FROM data LIMIT 5",
        "charts": [],
        "insight": "Top 5 items shown",
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert "Chat:" in data["name"]
