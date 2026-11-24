"""Semantic layer and Insight Report tests."""
import json
from pathlib import Path

from database.session import SessionLocal
from services.semantic_layer import semantic_context_text


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


def _approve_sales_governance(client, project_id: str, dataset_id: str, auth_headers: dict) -> None:
    layer = client.get(f"/api/semantic/{project_id}", headers=auth_headers).json()
    metric = next(item for item in layer["metrics"] if item["dataset_id"] == dataset_id and item["name"] == "Total Sales")
    dimension = next(item for item in layer["dimensions"] if item["dataset_id"] == dataset_id and item["name"] == "Region")
    assert client.patch(
        f"/api/semantic/metrics/{metric['id']}/status",
        json={"status": "approved"}, headers=auth_headers,
    ).status_code == 200
    assert client.patch(
        f"/api/semantic/dimensions/{dimension['id']}/status",
        json={"status": "approved"}, headers=auth_headers,
    ).status_code == 200


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
    _approve_sales_governance(client, project_id, dataset_id, auth_headers)

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
    assert "证据块" in report["content"]["markdown"]
    assert "决策摘要" in report["content"]["markdown"]
    assert "诊断洞察" in report["content"]["markdown"]
    assert "假设验证" in report["content"]["markdown"]
    assert "分析图谱" in report["content"]["markdown"]
    assert "指标契约检查" in report["content"]["markdown"]
    assert "建议追问" in report["content"]["markdown"]
    assert "Executive Summary" not in report["content"]["markdown"]
    assert all("sql" in block and "policy" in block for block in report["content"]["blocks"])
    block_titles = {block["title"] for block in report["content"]["blocks"]}
    assert "贡献集中度" in block_titles
    assert "数值异常扫描" in block_titles

    list_resp = client.get(f"/api/reports/project/{project_id}", headers=auth_headers)
    assert list_resp.status_code == 200
    assert list_resp.json()[0]["id"] == report["id"]


def test_auto_investigation_creates_actionable_cards(client, project_id, auth_headers):
    dataset_id = _upload_sales_dataset(client, project_id, auth_headers)
    _approve_sales_governance(client, project_id, dataset_id, auth_headers)

    resp = client.post(
        "/api/reports/investigate",
        json={"project_id": project_id, "dataset_id": dataset_id},
        headers=auth_headers,
    )

    assert resp.status_code == 201, resp.text
    report = resp.json()
    assert report["title"].endswith("自动调查")
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


def test_retail_schema_suggests_revenue_and_report_uses_it_without_profit_claims(client, project_id, auth_headers):
    csv_path = Path("backend/test_storage/retail_fixture.csv")
    csv_path.parent.mkdir(exist_ok=True)
    csv_path.write_text(
        "InvoiceNo,StockCode,Description,Quantity,InvoiceDate,UnitPrice,CustomerID,Country\n"
        "10001,A1,Widget,2,2026-01-01,10.5,7,United Kingdom\n"
        "10002,A2,Gadget,-1,2026-01-02,5.0,8,France\n",
        encoding="utf-8",
    )
    with csv_path.open("rb") as handle:
        upload = client.post(
            f"/api/datasets/upload?project_id={project_id}",
            files={"file": ("retail_fixture.csv", handle, "text/csv")},
            headers=auth_headers,
        )
    assert upload.status_code == 200, upload.text
    dataset_id = upload.json()["id"]

    layer = client.get(f"/api/semantic/{project_id}", headers=auth_headers).json()
    revenue = next(item for item in layer["metrics"] if item["dataset_id"] == dataset_id and item["name"] == "销售额")
    assert revenue["expression"] == 'SUM("Quantity" * "UnitPrice")'
    suggested_dimensions = {
        item["name"] for item in layer["dimensions"] if item["dataset_id"] == dataset_id
    }
    assert "Country" in suggested_dimensions
    assert not {"InvoiceNo", "StockCode", "Description", "UnitPrice", "CustomerID"}.intersection(suggested_dimensions)

    country = next(item for item in layer["dimensions"] if item["dataset_id"] == dataset_id and item["name"] == "Country")
    assert client.patch(
        f"/api/semantic/metrics/{revenue['id']}/status",
        json={"status": "approved"}, headers=auth_headers,
    ).status_code == 200
    assert client.patch(
        f"/api/semantic/dimensions/{country['id']}/status",
        json={"status": "approved"}, headers=auth_headers,
    ).status_code == 200

    report_response = client.post(
        "/api/reports/investigate",
        json={"project_id": project_id, "dataset_id": dataset_id},
        headers=auth_headers,
    )
    assert report_response.status_code == 201, report_response.text
    report = report_response.json()
    total_block = next(block for block in report["content"]["blocks"] if block["title"] == "总计：销售额")
    assert '"Quantity" * "UnitPrice"' in total_block["sql"]
    assert "利润" not in json.dumps(report["content"], ensure_ascii=False)


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


def test_notebook_cells_require_project_ownership(client, project_id, auth_headers):
    notebook = client.post(
        "/api/notebooks/",
        json={"project_id": project_id, "name": "Private notebook", "cells": [{"cell_type": "python", "content": "print(1)"}]},
        headers=auth_headers,
    ).json()
    cell_id = client.get(f"/api/notebooks/{notebook['id']}", headers=auth_headers).json()["cells"][0]["id"]

    client.post("/api/auth/register", json={"email": "other@nexa.io", "password": "test1234"})
    other_login = client.post("/api/auth/login", json={"email": "other@nexa.io", "password": "test1234"})
    other_headers = {"Authorization": f"Bearer {other_login.json()['token']}"}

    assert client.put(f"/api/notebooks/cells/{cell_id}", json={"content": "print(2)"}, headers=other_headers).status_code == 404
    assert client.post(f"/api/notebooks/cells/{cell_id}/execute", headers=other_headers).status_code == 404


def test_notebook_sql_and_python_use_bound_dataset(client, project_id, auth_headers):
    dataset_id = _upload_sales_dataset(client, project_id, auth_headers)
    notebook = client.post(
        "/api/notebooks/",
        json={
            "project_id": project_id,
            "dataset_id": dataset_id,
            "name": "Bound notebook",
            "cells": [
                {"cell_type": "sql", "content": "SELECT COUNT(*) AS count FROM data"},
                {"cell_type": "python", "content": "print(columns)\nprint(len(rows))", "sort_order": 1},
            ],
        },
        headers=auth_headers,
    )
    assert notebook.status_code == 200, notebook.text
    detail = client.get(f"/api/notebooks/{notebook.json()['id']}", headers=auth_headers).json()
    assert detail["dataset_id"] == dataset_id

    sql_result = client.post(f"/api/notebooks/cells/{detail['cells'][0]['id']}/execute", headers=auth_headers)
    assert sql_result.status_code == 200, sql_result.text
    assert sql_result.json()["rows"] == [[3]]

    python_result = client.post(f"/api/notebooks/cells/{detail['cells'][1]['id']}/execute", headers=auth_headers)
    assert python_result.status_code == 200, python_result.text
    assert "Region" in python_result.json()["output"]
    assert python_result.json()["output"].strip().endswith("3")


def test_notebook_python_timeout_does_not_block_worker(client, project_id, auth_headers):
    dataset_id = _upload_sales_dataset(client, project_id, auth_headers)
    notebook = client.post(
        "/api/notebooks/",
        json={
            "project_id": project_id,
            "dataset_id": dataset_id,
            "cells": [{"cell_type": "python", "content": "while True: pass"}],
        },
        headers=auth_headers,
    ).json()
    cell_id = client.get(f"/api/notebooks/{notebook['id']}", headers=auth_headers).json()["cells"][0]["id"]

    timed_out = client.post(f"/api/notebooks/cells/{cell_id}/execute", headers=auth_headers)
    assert timed_out.status_code == 408
    assert "5 second" in timed_out.json()["detail"]


def test_readiness_probe_works_with_sqlalchemy_2(client):
    response = client.get("/api/health/ready")
    assert response.status_code == 200, response.text


def test_quality_and_report_publication_gates(client, project_id, auth_headers):
    dataset_id = _upload_sales_dataset(client, project_id, auth_headers)

    quality = client.get(f"/api/datasets/by-id/{dataset_id}/quality", headers=auth_headers)
    assert quality.status_code == 200, quality.text
    assert quality.json()["status"] == "pass"
    assert quality.json()["row_count"] == 3

    report = client.post(
        "/api/reports",
        json={"project_id": project_id, "dataset_id": dataset_id},
        headers=auth_headers,
    ).json()
    assert report["status"] == "draft"

    blocked = client.post(f"/api/reports/{report['id']}/publish", headers=auth_headers)
    assert blocked.status_code == 400
    assert "no approved metric" in blocked.json()["detail"]

    layer = client.get(f"/api/semantic/{project_id}", headers=auth_headers).json()
    metric_id = next(metric["id"] for metric in layer["metrics"] if metric["dataset_id"] == dataset_id)
    approved = client.patch(
        f"/api/semantic/metrics/{metric_id}/status",
        json={"status": "approved"},
        headers=auth_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    governed_report = client.post(
        "/api/reports",
        json={"project_id": project_id, "dataset_id": dataset_id},
        headers=auth_headers,
    ).json()
    published = client.post(f"/api/reports/{governed_report['id']}/publish", headers=auth_headers)
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"
    assert published.json()["published_at"]


def test_agent_semantic_context_only_contains_approved_definitions(client, project_id, auth_headers):
    dataset_id = _upload_sales_dataset(client, project_id, auth_headers)
    layer = client.get(f"/api/semantic/{project_id}", headers=auth_headers).json()
    sales_metric = next(metric for metric in layer["metrics"] if metric["dataset_id"] == dataset_id and metric["name"] == "Total Sales")

    with SessionLocal() as db:
        assert "Total Sales" not in semantic_context_text(db, project_id, dataset_id)

    approved = client.patch(
        f"/api/semantic/metrics/{sales_metric['id']}/status",
        json={"status": "approved"},
        headers=auth_headers,
    )
    assert approved.status_code == 200, approved.text
    with SessionLocal() as db:
        context = semantic_context_text(db, project_id, dataset_id)
    assert "Total Sales" in context
    assert "Region maps" not in context


def test_invalid_metric_cannot_be_approved(client, project_id, auth_headers):
    dataset_id = _upload_sales_dataset(client, project_id, auth_headers)
    created = client.post("/api/semantic/metrics", json={
        "project_id": project_id,
        "dataset_id": dataset_id,
        "name": "Invalid metric",
        "expression": 'SUM("Does Not Exist")',
    }, headers=auth_headers)
    assert created.status_code == 201

    approved = client.patch(
        f"/api/semantic/metrics/{created.json()['id']}/status",
        json={"status": "approved"},
        headers=auth_headers,
    )
    assert approved.status_code == 400
    assert "missing columns" in approved.json()["detail"]


def test_date_dataset_quality_and_report_are_json_safe(client, project_id, auth_headers):
    uploaded = client.post(
        f"/api/datasets/upload?project_id={project_id}",
        files={"file": (
            "daily.csv",
            b"event_date,cnt\n2026-01-01,3\n2026-01-02,5\n",
            "text/csv",
        )},
        headers=auth_headers,
    )
    assert uploaded.status_code == 200, uploaded.text
    dataset_id = uploaded.json()["id"]

    quality = client.get(f"/api/datasets/by-id/{dataset_id}/quality", headers=auth_headers)
    assert quality.status_code == 200, quality.text
    schema_check = next(check for check in quality.json()["checks"] if check["name"] == "schema_drift")
    assert schema_check["status"] == "pass"

    report = client.post(
        "/api/reports",
        json={"project_id": project_id, "dataset_id": dataset_id},
        headers=auth_headers,
    )
    assert report.status_code == 201, report.text
    assert report.json()["content"]["blocks"]
