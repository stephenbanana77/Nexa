"""Project API tests."""
import os

from tools.query_engine import SchemaColumn


def test_create_project(client, auth_headers):
    resp = client.post("/api/projects", json={"name": "My Project"}, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Project"
    assert "id" in data


def test_list_projects(client, auth_headers, project_id):
    resp = client.get("/api/projects", headers=auth_headers)
    assert resp.status_code == 200
    projects = resp.json()
    assert any(p["id"] == project_id for p in projects)


def test_get_project(client, auth_headers, project_id):
    resp = client.get(f"/api/projects/{project_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Project"


def test_upload_csv(client, auth_headers, project_id):
    csv_content = b"name,price\nItem A,10\nItem B,20\nItem C,30"
    resp = client.post(
        f"/api/datasets/upload?project_id={project_id}",
        files={"file": ("test.csv", csv_content, "text/csv")},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "test.csv"
    assert data["row_count"] == 3


def test_preview_csv(client, auth_headers):
    csv_content = b"name,price,qty\nA,10,100\nB,20,200"
    resp = client.post(
        "/api/datasets/preview",
        files={"file": ("preview.csv", csv_content, "text/csv")},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["columns"]) == 3
    assert len(data["preview_rows"]) == 2


def test_upload_unsupported_format(client, auth_headers, project_id):
    resp = client.post(
        f"/api/datasets/upload?project_id={project_id}",
        files={"file": ("test.txt", b"hello", "text/plain")},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_same_name_uploads_keep_immutable_file_contents(client, auth_headers, project_id):
    first = client.post(
        f"/api/datasets/upload?project_id={project_id}",
        files={"file": ("sales.csv", b"value\n1\n2\n", "text/csv")},
        headers=auth_headers,
    )
    second = client.post(
        f"/api/datasets/upload?project_id={project_id}",
        files={"file": ("sales.csv", b"value\n10\n20\n30\n", "text/csv")},
        headers=auth_headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] != second.json()["id"]

    first_count = client.post(
        f"/api/datasets/by-id/{first.json()['id']}/query",
        json={"sql": "SELECT COUNT(*) AS count FROM data"},
        headers=auth_headers,
    )
    second_count = client.post(
        f"/api/datasets/by-id/{second.json()['id']}/query",
        json={"sql": "SELECT COUNT(*) AS count FROM data"},
        headers=auth_headers,
    )
    assert first_count.json()["rows"] == [[2]]
    assert second_count.json()["rows"] == [[3]]


def test_dataset_list_includes_schema_and_preview_metadata(client, auth_headers, project_id):
    uploaded = client.post(
        f"/api/datasets/upload?project_id={project_id}",
        files={"file": ("schema.csv", b"day,value\n2026-01-01,1\n", "text/csv")},
        headers=auth_headers,
    )
    assert uploaded.status_code == 200

    listed = client.get(f"/api/datasets?project_id={project_id}", headers=auth_headers)
    item = next(row for row in listed.json() if row["id"] == uploaded.json()["id"])
    assert item["schema_info"]
    assert item["source_type"] == "csv"
    assert item["created_at"]


def test_mysql_connection_unwraps_secret_and_requires_table_selection(
    client, auth_headers, project_id, monkeypatch
):
    captured = {}

    class FakeConnector:
        def get_tables(self):
            return [{"name": "orders", "row_count": 12}]

        def get_schema(self, table_name):
            assert table_name == "orders"
            return [SchemaColumn(name="order_id", type="BIGINT")]

    def fake_register(project, host, port, user, password, database):
        captured["password"] = password

    monkeypatch.setattr("tools.register_mysql", fake_register)
    monkeypatch.setattr("tools.get_engine", lambda _project: FakeConnector())
    request = {
        "project_id": project_id,
        "host": "db.example.com",
        "port": 3306,
        "user": "analyst",
        "password": "secret-value",
        "database": "warehouse",
    }

    selection = client.post("/api/datasets/connect-mysql", json=request, headers=auth_headers)
    assert selection.status_code == 200, selection.text
    assert selection.json()["status"] == "select_table"
    assert captured["password"] == "secret-value"
    assert isinstance(captured["password"], str)

    connected = client.post(
        "/api/datasets/connect-mysql",
        json={**request, "table": "orders"},
        headers=auth_headers,
    )
    assert connected.status_code == 200, connected.text
    assert connected.json()["name"] == "mysql://warehouse/orders"
    assert connected.json()["row_count"] == 12
    assert connected.json()["schema_info"][0]["name"] == "order_id"
