"""Demo project tests."""


def test_create_superstore_demo_project(client, auth_headers):
    resp = client.post("/api/demo/superstore", headers=auth_headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["project_id"]
    assert data["dataset_id"]
    assert data["report_id"]

    second = client.post("/api/demo/superstore", headers=auth_headers)
    assert second.status_code == 201
    assert second.json()["reused"] is True
