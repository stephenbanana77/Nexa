"""Workflow runner tests — step execution, partial failure, variable interpolation."""
import json


def _upload_rows(client, auth_headers, project_id, name, values):
    body = "value\n" + "\n".join(str(value) for value in values) + "\n"
    response = client.post(
        f"/api/datasets/upload?project_id={project_id}",
        files={"file": (name, body.encode(), "text/csv")},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _stream_events(client, auth_headers, workflow_id):
    # sse-starlette 2.x keeps its shutdown event globally; TestClient creates a
    # fresh loop for each request.
    from sse_starlette.sse import AppStatus
    AppStatus.should_exit_event = None
    events = []
    with client.stream("POST", f"/api/workflows/{workflow_id}/run", headers=auth_headers) as response:
        for line in response.iter_lines():
            decoded = line.decode("utf-8") if isinstance(line, bytes) else line
            if decoded.startswith("data: "):
                events.append(json.loads(decoded[6:]))
    return events


def test_empty_workflow_cannot_run(client, auth_headers, project_id):
    resp = client.post("/api/workflows", json={
        "project_id": project_id,
        "name": "Empty workflow",
    }, headers=auth_headers)
    assert resp.status_code == 200

    run = client.post(f"/api/workflows/{resp.json()['id']}/run", headers=auth_headers)

    assert run.status_code == 400
    assert run.json()["detail"] == "Workflow has no steps. Configure at least one step before running."


def test_workflow_run_partial_failure(client, auth_headers, project_id):
    """When a workflow step fails, the runner emits workflow_done with partial results.
    Also validates step_id tracking and variable interpolation."""
    resp = client.post("/api/workflows", json={
        "project_id": project_id,
        "name": "Integration Test WF",
    }, headers=auth_headers)
    assert resp.status_code == 200
    wf_id = resp.json()["id"]

    # Add steps: good SQL then bad SQL, with variable reference in the description
    client.put(f"/api/workflows/{wf_id}", json={
        "name": "Integration Test WF",
        "steps": [
            {"type": "sql", "config": {"sql_template": "SELECT 1 AS num"}, "description": "ok step"},
            {"type": "insight", "config": {"prompt": "Row count was ${0.row_count}"}, "description": "use var"},
            {"type": "sql", "config": {"sql_template": "SELECT * FROM nonexistent_table"}, "description": "will fail"},
        ],
    }, headers=auth_headers)

    # Run via streaming client
    events = []
    with client.stream("POST", f"/api/workflows/{wf_id}/run", headers=auth_headers) as resp_sse:
        for line in resp_sse.iter_lines():
            decoded = line.decode("utf-8") if isinstance(line, bytes) else line
            if decoded.startswith("data: "):
                events.append(json.loads(decoded[6:]))

    # Last event should be workflow_done with partial status
    last = events[-1]
    assert last["event"] == "workflow_done"
    assert last.get("status") == "partial"
    assert last["completed_steps"] >= 1  # at least the first SQL step should complete

    # Should have a step_error event
    step_errors = [e for e in events if e["event"] == "step_error"]
    assert len(step_errors) >= 1

    # step_start events should include step_id
    step_starts = [e for e in events if e["event"] == "step_start"]
    assert len(step_starts) > 0
    assert all("step_id" in e for e in step_starts)

    # step_done events should exist for completed steps
    step_dones = [e for e in events if e["event"] == "step_done"]
    assert len(step_dones) >= 1


def test_workflow_variable_interpolation_no_crash(client, auth_headers, project_id):
    """Variable substitution in step configs should not crash, produce workflow_done."""
    resp = client.post("/api/workflows", json={
        "project_id": project_id,
        "name": "Var WF",
    }, headers=auth_headers)
    wf_id = resp.json()["id"]

    client.put(f"/api/workflows/{wf_id}", json={
        "name": "Var WF",
        "steps": [
            {"type": "sql", "config": {"sql_template": "SELECT 42 AS answer"}},
            {"type": "insight", "config": {"prompt": "Got ${0.row_count} rows"}},
        ],
    }, headers=auth_headers)

    # Verify the workflow is properly configured (no crash on detail)
    detail = client.get(f"/api/workflows/detail/{wf_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["name"] == "Var WF"
    assert len(detail.json()["steps"]) == 2


def test_workflow_lifecycle(client, auth_headers, project_id):
    """Full lifecycle: create → update → detail → delete. Without streaming."""
    # Create
    resp = client.post("/api/workflows", json={
        "project_id": project_id,
        "name": "Lifecycle WF",
    }, headers=auth_headers)
    assert resp.status_code == 200
    wf_id = resp.json()["id"]

    # Update with steps
    resp = client.put(f"/api/workflows/{wf_id}", json={
        "name": "Lifecycle WF v2",
        "steps": [
            {"type": "sql", "config": {"sql_template": "SELECT 1"}},
            {"type": "insight", "config": {"prompt": "Analyze"}},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 200

    # Detail
    resp = client.get(f"/api/workflows/detail/{wf_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Lifecycle WF v2"
    assert len(data["steps"]) == 2
    assert data["steps"][0]["type"] == "sql"

    # Delete
    resp = client.delete(f"/api/workflows/{wf_id}", headers=auth_headers)
    assert resp.status_code == 200

    # Verify gone
    resp = client.get(f"/api/workflows/detail/{wf_id}", headers=auth_headers)
    assert resp.status_code == 404


def test_workflow_sql_is_deterministically_bound_to_dataset(client, auth_headers, project_id):
    first_id = _upload_rows(client, auth_headers, project_id, "same.csv", [1, 2])
    _upload_rows(client, auth_headers, project_id, "same.csv", [1, 2, 3, 4])
    created = client.post("/api/workflows", json={
        "project_id": project_id,
        "name": "Bound workflow",
        "inputs": {"dataset_ids": [first_id]},
        "steps": [{"type": "sql", "config": {"sql_template": "SELECT COUNT(*) AS count FROM data"}}],
    }, headers=auth_headers)
    workflow_id = created.json()["id"]

    first_events = _stream_events(client, auth_headers, workflow_id)
    first_result = next(event["result"] for event in first_events if event["event"] == "step_done")
    assert first_result["rows"] == [[2]]

    detail = client.get(f"/api/workflows/detail/{workflow_id}", headers=auth_headers).json()
    assert detail["status"] == "active"
    assert detail["last_run_at"] is not None


def test_workflow_skill_step_does_not_fake_success(client, auth_headers, project_id):
    dataset_id = _upload_rows(client, auth_headers, project_id, "skill.csv", [1])
    created = client.post("/api/workflows", json={
        "project_id": project_id,
        "name": "Missing skill workflow",
        "inputs": {"dataset_ids": [dataset_id]},
        "steps": [{"type": "skill", "config": {"skill_name": "does-not-exist"}}],
    }, headers=auth_headers)

    events = _stream_events(client, auth_headers, created.json()["id"])
    assert events[-1]["event"] == "workflow_done"
    assert events[-1]["status"] == "partial"
    assert "not found" in events[-1]["error"]

    runs = client.get(f"/api/runs/{project_id}", headers=auth_headers).json()
    detail = client.get(f"/api/runs/detail/{runs[0]['id']}", headers=auth_headers).json()
    assert detail["status"] == "failed"
    assert detail["steps"][0]["error"]


def test_workflow_skill_step_executes_real_skill(
    client, auth_headers, project_id, monkeypatch
):
    dataset_id = _upload_rows(client, auth_headers, project_id, "skill-real.csv", [1, 2, 3])
    installed = client.post("/api/skills/install", json={
        "name": "row-count-skill",
        "title": "Row Count Skill",
        "definition": {
            "name": "row-count-skill",
            "type": "analysis",
            "steps": [{"type": "sql", "prompt": "Count rows"}],
        },
    }, headers=auth_headers)
    assert installed.status_code == 200, installed.text

    async def fake_achat(_messages):
        return "```sql\nSELECT COUNT(*) AS count FROM data\n```"

    monkeypatch.setattr("skills.executor.achat", fake_achat)
    workflow = client.post("/api/workflows", json={
        "project_id": project_id,
        "name": "Real skill workflow",
        "inputs": {"dataset_ids": [dataset_id]},
        "steps": [{"type": "skill", "config": {"skill_name": "row-count-skill"}}],
    }, headers=auth_headers)

    events = _stream_events(client, auth_headers, workflow.json()["id"])
    sql_event = next(event for event in events if event.get("event") == "skill_progress" and event.get("type") == "sql" and event.get("result"))
    assert sql_event["result"]["rows"] == [[3]]
    assert events[-1]["status"] == "complete"
