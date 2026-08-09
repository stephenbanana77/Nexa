"""Skill manifest validation tests."""
import json


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
    assert "action" in resp.json()["detail"].lower()


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
