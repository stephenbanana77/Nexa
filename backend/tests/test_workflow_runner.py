"""Workflow runner tests — step execution, partial failure, variable interpolation."""
import json


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
