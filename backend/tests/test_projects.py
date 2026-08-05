"""Project API tests."""
import os


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
