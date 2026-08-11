"""Local runtime settings API."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI
from pydantic import BaseModel

from models.user import User
from services.auth import get_current_user
from utils.config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])

ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class LLMSettingsUpdate(BaseModel):
    provider: str
    api_key: str | None = None
    model: str | None = None
    base_url: str | None = None


def _provider_fields(provider: str) -> tuple[str, str, str]:
    if provider == "moonshot":
        return "MOONSHOT_API_KEY", "MOONSHOT_BASE_URL", "MOONSHOT_MODEL"
    if provider == "deepseek":
        return "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL"
    raise HTTPException(status_code=400, detail="provider must be 'deepseek' or 'moonshot'")


def _read_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ROOT_ENV.exists():
        return values
    for line in ROOT_ENV.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _write_env_values(updates: dict[str, str]) -> None:
    values = _read_env_file()
    values.update({k: v for k, v in updates.items() if v is not None})
    ordered_keys = [
        "SECRET_KEY", "DATABASE_URL", "CORS_ORIGINS", "LLM_PROVIDER",
        "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL",
        "MOONSHOT_API_KEY", "MOONSHOT_BASE_URL", "MOONSHOT_MODEL",
        "STORAGE_PATH", "MAX_UPLOAD_SIZE_MB",
    ]
    lines = ["# Nexa local environment. This file is ignored by git.", ""]
    for key in ordered_keys:
        if key in values:
            lines.append(f"{key}={values[key]}")
        if key == "CORS_ORIGINS":
            lines.append("")
        if key == "LLM_PROVIDER":
            lines.append("")
        if key == "DEEPSEEK_MODEL":
            lines.append("")
        if key == "MOONSHOT_MODEL":
            lines.append("")
    ROOT_ENV.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _is_real_key(value: str | None) -> bool:
    return bool(value and value.strip() and not value.startswith("sk-your-"))


def _serialize_llm_settings() -> dict:
    return {
        "provider": settings.LLM_PROVIDER,
        "base_url": settings.LLM_BASE_URL,
        "model": settings.LLM_MODEL,
        "has_key": _is_real_key(settings.LLM_API_KEY),
        "providers": {
            "deepseek": {
                "base_url": settings.DEEPSEEK_BASE_URL,
                "model": settings.DEEPSEEK_MODEL,
                "has_key": _is_real_key(settings.DEEPSEEK_API_KEY),
            },
            "moonshot": {
                "base_url": settings.MOONSHOT_BASE_URL,
                "model": settings.MOONSHOT_MODEL,
                "has_key": _is_real_key(settings.MOONSHOT_API_KEY),
            },
        },
    }


@router.get("/llm")
def get_llm_settings(current_user: User = Depends(get_current_user)):
    del current_user
    return _serialize_llm_settings()


@router.put("/llm")
def update_llm_settings(req: LLMSettingsUpdate, current_user: User = Depends(get_current_user)):
    del current_user
    provider = req.provider.lower()
    key_field, base_field, model_field = _provider_fields(provider)
    updates = {"LLM_PROVIDER": provider}
    if req.api_key:
        updates[key_field] = req.api_key.strip()
    if req.base_url:
        updates[base_field] = req.base_url.strip()
    if req.model:
        updates[model_field] = req.model.strip()

    _write_env_values(updates)
    for key, value in updates.items():
        os.environ[key] = value
        setattr(settings, key, value)
    return _serialize_llm_settings()


@router.post("/llm/test")
def test_llm_settings(current_user: User = Depends(get_current_user)):
    del current_user
    if not _is_real_key(settings.LLM_API_KEY):
        raise HTTPException(status_code=400, detail="Current provider API key is not configured")
    try:
        client = OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": "Reply with OK."}],
            max_tokens=8,
            temperature=0,
            timeout=20,
        )
        return {"ok": True, "reply": response.choices[0].message.content or ""}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"LLM connection failed: {str(exc)}")
