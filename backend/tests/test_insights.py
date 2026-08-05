"""Insight API tests."""
def test_save_insight(client, auth_headers, project_id):
    resp = client.post(f"/api/insights?project_id={project_id}", json={
        "question": "What is the average price?",
        "content": {"summary": "Average price is 20", "sql": "SELECT AVG(price) FROM data", "row_count": 100},
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    return data["id"]


def test_list_insights(client, auth_headers, project_id):
    # Save one first
    client.post(f"/api/insights?project_id={project_id}", json={
        "question": "Test insight", "content": {"summary": "ok"},
    }, headers=auth_headers)

    resp = client.get(f"/api/insights/project/{project_id}", headers=auth_headers)
    assert resp.status_code == 200
    insights = resp.json()
    assert len(insights) >= 1


def test_delete_insight(client, auth_headers, project_id):
    insight_id = test_save_insight(client, auth_headers, project_id)
    resp = client.delete(f"/api/insights/{insight_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_delete_nonexistent_insight(client, auth_headers):
    resp = client.delete("/api/insights/nonexistent-id", headers=auth_headers)
    assert resp.status_code == 404
