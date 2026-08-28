"""Demo project tests."""


def test_create_superstore_demo_project(client, auth_headers):
    resp = client.post("/api/demo/superstore", headers=auth_headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["project_id"]
    assert data["project"]["id"] == data["project_id"]
    assert data["dataset_id"]
    assert data["dataset"]["id"] == data["dataset_id"]
    assert data["report_id"]
    assert data["report"]["id"] == data["report_id"]

    second = client.post("/api/demo/superstore", headers=auth_headers)
    assert second.status_code == 201
    assert second.json()["reused"] is True
    assert second.json()["project"]["id"] == data["project_id"]
    assert second.json()["dataset"]["id"] == data["dataset_id"]


def test_superstore_demo_report_contains_investigation_artifacts(client, auth_headers):
    resp = client.post("/api/demo/superstore", headers=auth_headers)
    data = resp.json()

    report_resp = client.get(f"/api/reports/{data['report_id']}", headers=auth_headers)
    assert report_resp.status_code == 200
    report = report_resp.json()
    assert report["content"]["decision_brief"]
    assert report["content"]["analysis_graph"]
    assert report["content"]["metric_contracts"]
    assert report["content"]["investigation_cards"]
    metric_names = {metric["name"] for metric in report["semantic_snapshot"]["metrics"]}
    assert "Total Row ID" not in metric_names
    assert "Total Postal Code" not in metric_names
    block_titles = {block["title"] for block in report["content"]["blocks"]}
    assert "Top Region by Sales" in block_titles
    assert "Top Order Date by Sales" not in block_titles
