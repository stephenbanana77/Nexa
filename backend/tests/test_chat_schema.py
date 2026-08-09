"""Chat multi-dataset schema context tests."""
import json


def test_chat_single_dataset_no_crash(client, auth_headers, project_id):
    """Chat with no datasets should return error, not crash."""
    resp = client.post("/api/chat/stream", json={
        "project_id": project_id,
        "message": "Hello",
    }, headers=auth_headers)
    # Should return 400 because no dataset uploaded
    assert resp.status_code == 400
    assert "dataset" in resp.json()["detail"].lower()


def test_chat_dataset_ids_edge_case(client, auth_headers, project_id):
    """Empty dataset_ids array should behave consistently."""
    resp = client.post("/api/chat/stream", json={
        "project_id": project_id,
        "message": "Show data",
        "dataset_ids": [],  # Explicitly empty
    }, headers=auth_headers)
    # Either 400 (no dataset) or 200 with error event — both are valid
    if resp.status_code == 400:
        assert "dataset" in resp.json()["detail"].lower()
    # If 200, it would stream, but we don't read SSE for this test
    assert resp.status_code in (200, 400)


def test_chat_dataset_id_legacy_param(client, auth_headers, project_id):
    """Legacy dataset_id parameter should still work (return error for nonexistent)."""
    resp = client.post("/api/chat/stream", json={
        "project_id": project_id,
        "message": "Show data",
        "dataset_id": "nonexistent",
    }, headers=auth_headers)
    assert resp.status_code in (200, 400, 422)
