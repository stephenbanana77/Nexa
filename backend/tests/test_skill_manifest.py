"""Skill manifest validation tests."""
import json

from skills import skill_registry
from skills.builtin import register_builtin_skills


def _valid_definition():
    return {
        "name": "test-skill",
        "type": "analysis",
        "actions": [
            {"type": "sql", "description": "Run a query"},
            {"type": "chart", "description": "Show chart"},
        ],
    }


def test_skill_preview_valid_manifest(client, auth_headers):
    """A valid manifest should preview without errors."""
    resp = client.post("/api/skills/preview", json={
        "name": "test-skill",
        "title": "Test Skill",
        "definition": _valid_definition(),
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert len(data["permissions"]["action_types"]) >= 2
    assert data["permissions"]["has_dangerous"] is False


def test_skill_preview_missing_fields(client, auth_headers):
    """Missing required manifest keys should return 400."""
    resp = client.post("/api/skills/preview", json={
        "name": "bad-skill",
        "title": "Bad",
        "definition": {"name": "bare"},  # missing type and actions
    }, headers=auth_headers)
    assert resp.status_code == 400
    assert "Missing" in resp.json()["detail"]


def test_skill_preview_no_actions(client, auth_headers):
    """Empty actions list should return 400."""
    resp = client.post("/api/skills/preview", json={
        "name": "empty-skill",
        "title": "Empty",
        "definition": {"name": "empty", "type": "analysis", "actions": []},
    }, headers=auth_headers)
    assert resp.status_code == 400
    assert "step" in resp.json()["detail"].lower()


def test_skill_preview_unknown_action_type(client, auth_headers):
    """Unknown action type should return 400."""
    resp = client.post("/api/skills/preview", json={
        "name": "weird-skill",
        "title": "Weird",
        "definition": {"name": "w", "type": "analysis", "actions": [{"type": "shell_command"}]},
    }, headers=auth_headers)
    assert resp.status_code == 400
    assert "unknown" in resp.json()["detail"].lower()


def test_skill_install_dangerous_without_confirm(client, auth_headers):
    """Dangerous actions (http/python) without confirmation should be blocked."""
    defn = _valid_definition()
    defn["actions"].append({"type": "http", "description": "Call external API"})

    resp = client.post("/api/skills/install", json={
        "name": "danger-skill",
        "title": "Danger",
        "definition": defn,
    }, headers=auth_headers)
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert isinstance(detail, dict) or "dangerous" in str(detail).lower()


def test_skill_install_dangerous_with_confirm(client, auth_headers):
    """Dangerous actions WITH confirmation should install."""
    defn = _valid_definition()
    defn["actions"].append({"type": "http", "description": "Call API"})
    defn["__confirm_dangerous"] = True

    resp = client.post("/api/skills/install", json={
        "name": "danger-confirmed",
        "title": "Danger Confirmed",
        "definition": defn,
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "danger-confirmed"
    assert "permissions" in data


def test_skill_install_non_dict_definition(client, auth_headers):
    """Non-dict definition should return 400 or 422 (Pydantic rejection)."""
    resp = client.post("/api/skills/preview", json={
        "name": "string-skill",
        "title": "String",
        "definition": "not a dict",
    }, headers=auth_headers)
    assert resp.status_code in (400, 422)


def test_legacy_actions_are_normalized_to_executable_steps(client, auth_headers):
    response = client.post("/api/skills/install", json={
        "name": "legacy-skill",
        "title": "Legacy Skill",
        "definition": _valid_definition(),
    }, headers=auth_headers)
    assert response.status_code == 200, response.text

    detail = client.get(f"/api/skills/{response.json()['id']}", headers=auth_headers)
    assert [step["type"] for step in detail.json()["definition"]["steps"]] == ["sql", "visualize"]
    assert "actions" not in detail.json()["definition"]


def test_skill_execution_history_requires_project_ownership(
    client, auth_headers, project_id
):
    client.post(
        "/api/auth/register",
        json={"email": "skill-other@nexa.io", "password": "test1234", "name": "Other"},
    )
    login = client.post(
        "/api/auth/login",
        json={"email": "skill-other@nexa.io", "password": "test1234"},
    )
    other_headers = {"Authorization": f"Bearer {login.json()['token']}"}

    response = client.get(
        f"/api/skills/executions/{project_id}", headers=other_headers
    )
    assert response.status_code == 404


def test_builtin_catalog_only_exposes_executable_permissioned_skills():
    register_builtin_skills()
    skills = {item["name"]: item for item in skill_registry.list_all()}
    assert {"data_summary", "correlation_analysis", "top_bottom_finder", "trend_analysis"} <= set(skills)
    assert "schema_inspector" not in skills
    assert skills["data_summary"]["definition"]["steps"]
    assert skills["data_summary"]["permissions"]["read"] == ["schema", "data"]
