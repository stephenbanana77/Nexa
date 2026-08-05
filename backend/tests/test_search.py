"""Search API tests."""
def test_search_projects(client, auth_headers, project_id):
    resp = client.get("/api/search?q=Test", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "Test"
    assert any(r["type"] == "project" and r["id"] == project_id for r in data["results"])


def test_search_no_results(client, auth_headers):
    resp = client.get("/api/search?q=zzzznonexistent", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 0


def test_search_empty_query(client, auth_headers):
    resp = client.get("/api/search?q=", headers=auth_headers)
    assert resp.status_code == 422  # FastAPI validation
