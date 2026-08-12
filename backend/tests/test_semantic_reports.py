"""Semantic layer and Insight Report tests."""
from pathlib import Path


def _upload_sales_dataset(client, project_id: str, auth_headers: dict) -> str:
    csv_path = Path("backend/test_storage/sales_fixture.csv")
    csv_path.parent.mkdir(exist_ok=True)
    csv_path.write_text(
        "Region,Segment,Sales,Profit\n"
        "East,Consumer,100,20\n"
        "West,Consumer,200,50\n"
        "East,Corporate,150,10\n",
        encoding="utf-8",
    )
    with csv_path.open("rb") as handle:
        resp = client.post(
            f"/api/datasets/upload?project_id={project_id}",
            files={"file": ("sales_fixture.csv", handle, "text/csv")},
            headers=auth_headers,
        )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def test_semantic_layer_seed_and_crud(client, project_id, auth_headers):
    dataset_id = _upload_sales_dataset(client, project_id, auth_headers)

    layer = client.get(f"/api/semantic/{project_id}", headers=auth_headers).json()
    assert any(metric["name"] == "Total Sales" for metric in layer["metrics"])
    assert any(dim["name"] == "Region" for dim in layer["dimensions"])

    metric_resp = client.post(
        "/api/semantic/metrics",
        json={
            "project_id": project_id,
            "dataset_id": dataset_id,
            "name": "Profit Margin",
            "expression": 'SUM("Profit") / NULLIF(SUM("Sales"), 0)',
            "description": "Profit divided by sales.",
        },
        headers=auth_headers,
    )
    assert metric_resp.status_code == 201, metric_resp.text
    metric_id = metric_resp.json()["id"]

    layer = client.get(f"/api/semantic/{project_id}", headers=auth_headers).json()
    assert any(metric["name"] == "Profit Margin" for metric in layer["metrics"])

    delete_resp = client.delete(f"/api/semantic/metrics/{metric_id}", headers=auth_headers)
    assert delete_resp.status_code == 200


def test_report_generation_creates_sql_evidence(client, project_id, auth_headers):
    dataset_id = _upload_sales_dataset(client, project_id, auth_headers)

    resp = client.post(
        "/api/reports",
        json={"project_id": project_id, "dataset_id": dataset_id, "title": "Sales Quality Report"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    report = resp.json()

    assert report["title"] == "Sales Quality Report"
    assert report["content"]["highlights"]
    assert report["content"]["sections"]["executive_summary"]
    assert report["content"]["sections"]["key_metrics"]
    assert report["content"]["sections"]["diagnostic_insights"]
    assert report["content"]["investigation_cards"]
    assert report["content"]["decision_brief"]
    assert report["content"]["analysis_graph"]
    assert report["content"]["metric_contracts"]
    assert report["content"]["sections"]["risks"]
    assert report["content"]["sections"]["opportunities"]
    assert report["content"]["sections"]["recommended_follow_up_questions"]
    assert report["content"]["blocks"]
    assert "Evidence Blocks" in report["content"]["markdown"]
    assert "Decision Brief" in report["content"]["markdown"]
    assert "Diagnostic Insights" in report["content"]["markdown"]
    assert "Hypothesis Engine" in report["content"]["markdown"]
    assert "Analysis Graph" in report["content"]["markdown"]
    assert "Metric Contract Check" in report["content"]["markdown"]
    assert "Recommended Follow-up Questions" in report["content"]["markdown"]
    assert all("sql" in block and "policy" in block for block in report["content"]["blocks"])
    block_titles = {block["title"] for block in report["content"]["blocks"]}
    assert "Contribution concentration" in block_titles
    assert "Numeric outlier scan" in block_titles

    list_resp = client.get(f"/api/reports/project/{project_id}", headers=auth_headers)
    assert list_resp.status_code == 200
    assert list_resp.json()[0]["id"] == report["id"]


def test_auto_investigation_creates_actionable_cards(client, project_id, auth_headers):
    dataset_id = _upload_sales_dataset(client, project_id, auth_headers)

    resp = client.post(
        "/api/reports/investigate",
        json={"project_id": project_id, "dataset_id": dataset_id},
        headers=auth_headers,
    )

    assert resp.status_code == 201, resp.text
    report = resp.json()
    assert report["title"].endswith("Auto Investigation")
    cards = report["content"]["investigation_cards"]
    brief = report["content"]["decision_brief"]
    graph = report["content"]["analysis_graph"]
    contracts = report["content"]["metric_contracts"]
    assert cards
    assert brief["situation"] and brief["diagnosis"] and brief["recommendation"]
    assert brief["recommended_actions"]
    assert graph["nodes"] and graph["edges"]
    assert graph["entry_node"] == "dataset"
    assert graph["terminal_node"] == "decision_brief"
    assert contracts["contracts"]
    assert contracts["release_gate"]["can_answer"] is True
    assert any(contract["type"] == "metric" for contract in contracts["contracts"])
    assert all(card["finding"] and card["impact"] and card["next_question"] for card in cards)
    assert all(card["hypotheses"] for card in cards)
    assert all(hypothesis["validation"] for card in cards for hypothesis in card["hypotheses"])
    assert any(card["sql"] for card in cards)


def test_analysis_memory_context_includes_recent_report(client, project_id, auth_headers):
    dataset_id = _upload_sales_dataset(client, project_id, auth_headers)
    client.post(
        "/api/reports",
        json={"project_id": project_id, "dataset_id": dataset_id, "title": "Memory Seed Report"},
        headers=auth_headers,
    )

    resp = client.get(f"/api/reports/project/{project_id}/memory", headers=auth_headers)
    assert resp.status_code == 200
    assert "Memory Seed Report" in resp.json()["context"]
