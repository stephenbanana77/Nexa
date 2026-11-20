from api import settings as settings_api
from utils.config import settings


def test_custom_openai_compatible_provider_is_admin_only(
    client, auth_headers, monkeypatch
):
    monkeypatch.setattr(settings_api, "_write_env_values", lambda _updates: None)
    monkeypatch.setattr(settings, "LLM_PROVIDER", settings.LLM_PROVIDER)
    monkeypatch.setattr(settings, "CUSTOM_API_KEY", settings.CUSTOM_API_KEY)
    monkeypatch.setattr(settings, "CUSTOM_BASE_URL", settings.CUSTOM_BASE_URL)
    monkeypatch.setattr(settings, "CUSTOM_MODEL", settings.CUSTOM_MODEL)

    updated = client.put(
        "/api/settings/llm",
        json={
            "provider": "custom",
            "api_key": "test-key",
            "base_url": "https://relay.example.com/v1",
            "model": "example-model",
        },
        headers=auth_headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["provider"] == "custom"
    assert updated.json()["has_key"] is True

    client.post(
        "/api/auth/register",
        json={"email": "settings-other@example.com", "password": "test1234"},
    )
    login = client.post(
        "/api/auth/login",
        json={"email": "settings-other@example.com", "password": "test1234"},
    )
    other_headers = {"Authorization": f"Bearer {login.json()['token']}"}
    forbidden = client.put(
        "/api/settings/llm",
        json={"provider": "deepseek"},
        headers=other_headers,
    )
    assert forbidden.status_code == 403

