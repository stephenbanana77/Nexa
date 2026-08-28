"""Skill API routes — browse, install, and execute skills."""
import asyncio
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from database import get_db
from database.session import SessionLocal
from models.user import User
from models.project import Dataset, Project
from models.skill import Skill, SkillExecution
from services.auth import get_current_user
from skills import skill_registry
from utils.config import settings

router = APIRouter(prefix="/api/skills", tags=["skills"])


class SkillInstallRequest(BaseModel):
    name: str
    title: str
    description: str = ""
    category: str = "analysis"
    icon: str = "ExperimentOutlined"
    definition: dict
    version: str = "1.0.0"

# ── Manifest schema (subset for validation) ──
REQUIRED_MANIFEST_KEYS = {"name", "type", "actions"}
ALLOWED_ACTION_TYPES = {"sql", "llm", "chart", "http", "python", "notebook", "skill"}
DANGEROUS_ACTION_TYPES = {"http", "python"}  # require explicit user confirmation


def _validate_manifest(definition: dict) -> tuple[bool, str, dict]:
    """Validate Skill manifest structure.

    Returns (is_valid, error_message, permissions_summary).
    """
    if not isinstance(definition, dict):
        return False, "definition must be a JSON object", {}

    missing = REQUIRED_MANIFEST_KEYS - set(definition.keys())
    if missing:
        return False, f"Missing required manifest fields: {', '.join(sorted(missing))}", {}

    actions = definition.get("actions", [])
    if not isinstance(actions, list) or len(actions) == 0:
        return False, "manifest must have at least one action", {}

    permissions_summary = {
        "skill_name": definition.get("name", "unknown"),
        "skill_type": definition.get("type", "unknown"),
        "total_actions": len(actions),
        "action_types": [],
        "dangerous_actions": [],
        "required_inputs": [],
    }

    seen_types = set()
    for i, action in enumerate(actions):
        if not isinstance(action, dict):
            return False, f"Action #{i+1} must be an object", {}
        atype = action.get("type", "")
        if atype not in ALLOWED_ACTION_TYPES:
            return False, f"Action #{i+1} has unknown type '{atype}'. Allowed: {', '.join(sorted(ALLOWED_ACTION_TYPES))}", {}
        seen_types.add(atype)
        if atype in DANGEROUS_ACTION_TYPES:
            permissions_summary["dangerous_actions"].append({
                "index": i + 1,
                "type": atype,
                "description": action.get("description", "") or f"Runs {atype} code",
            })

    permissions_summary["action_types"] = sorted(seen_types)
    permissions_summary["has_dangerous"] = len(permissions_summary["dangerous_actions"]) > 0

    return True, "", permissions_summary


class SkillExecuteRequest(BaseModel):
    project_id: str
    dataset_id: str | None = None
    params: dict = Field(default_factory=dict)


def _assert_project_and_dataset(db: Session, project_id: str, dataset_id: str | None, user_id: str) -> None:
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if dataset_id:
        dataset = db.query(Dataset).filter(
            Dataset.id == dataset_id,
            Dataset.project_id == project_id,
        ).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")


@router.get("")
def list_skills(current_user: User = Depends(get_current_user), category: str | None = None):
    """List all available skills, optionally filtered by category."""
    if category:
        skills = skill_registry.list_by_category(category)
    else:
        skills = skill_registry.list_all()
    return skills


@router.get("/categories")
def list_categories():
    """List all skill categories with counts."""
    skills = skill_registry.list_all()
    cats: dict[str, int] = {}
    for s in skills:
        cat = s.get("category", "other")
        cats[cat] = cats.get(cat, 0) + 1
    return [{"name": k, "count": v} for k, v in cats.items()]


@router.get("/{skill_id}")
def get_skill(skill_id: str, current_user: User = Depends(get_current_user)):
    skill = skill_registry.get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.post("/install")
def install_skill(
    req: SkillInstallRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 1. Validate manifest schema
    is_valid, err_msg, perms = _validate_manifest(req.definition)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid skill manifest: {err_msg}")

    # 2. Block dangerous skills without explicit confirmation
    if perms["has_dangerous"] and not req.definition.get("__confirm_dangerous"):
        raise HTTPException(
            status_code=400,
            detail={
                "message": "This skill contains dangerous actions that require confirmation.",
                "dangerous_actions": perms["dangerous_actions"],
                "hint": "Set '__confirm_dangerous': true in definition to proceed.",
            }
        )

    existing = db.query(Skill).filter(Skill.name == req.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Skill already exists")

    skill = Skill(
        name=req.name,
        title=req.title,
        description=req.description,
        category=req.category,
        icon=req.icon,
        definition=req.definition,
        version=req.version,
        is_builtin=False,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return {"id": skill.id, "name": skill.name, "title": skill.title, "permissions": perms}


@router.post("/preview")
def preview_skill(req: SkillInstallRequest):
    """Preview a skill's permissions before installing. No DB write."""
    is_valid, err_msg, perms = _validate_manifest(req.definition)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid skill manifest: {err_msg}")
    return {
        "valid": True,
        "permissions": perms,
        "warnings": perms["dangerous_actions"] or ["This skill uses safe operation types only"] if not perms["dangerous_actions"] else [f"{len(perms['dangerous_actions'])} dangerous action(s) detected"],
    }


@router.delete("/{skill_id}")
def delete_skill(
    skill_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    if skill.is_builtin:
        raise HTTPException(status_code=400, detail="Cannot delete built-in skills")
    db.delete(skill)
    db.commit()
    return {"status": "deleted"}


@router.post("/{skill_id}/execute")
async def execute_skill(
    skill_id: str,
    req: SkillExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    skill = skill_registry.get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    effective_dataset_id = req.dataset_id or (req.params or {}).get("dataset_id")
    _assert_project_and_dataset(db, req.project_id, effective_dataset_id, current_user.id)
    allowed, reason = skill_registry.check_permissions(skill_id, {
        "available_resources": ["schema", "data"],
        "allowed_writes": ["insight", "chart"],
        "network_allowed": False,
        "llm_available": True,
    })
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    # Import here to avoid circular dependency
    from skills.executor import execute_skill as run_skill

    params = dict(req.params or {})
    if effective_dataset_id:
        params["dataset_id"] = effective_dataset_id
    execution_id = skill_registry.create_execution(skill.get("id", skill_id), req.project_id, params)

    from sse_starlette.sse import EventSourceResponse

    async def event_stream():
        failed = False
        try:
            async with asyncio.timeout(settings.SKILL_TIMEOUT_SEC):
                async for event in run_skill(skill, req.project_id, params):
                    import json
                    if event.get("event") in {"step_error", "skill_failed"}:
                        failed = True
                    yield {"event": event.get("event", "step"), "data": json.dumps(event, default=str)}
            if failed:
                skill_registry.update_execution(execution_id, "failed", {"error": "Skill step failed"})
            else:
                skill_registry.update_execution(execution_id, "done", {"result": "success"})
        except asyncio.CancelledError:
            skill_registry.update_execution(execution_id, "failed", {"error": "Skill execution cancelled"})
            raise
        except asyncio.TimeoutError:
            message = f"Skill exceeded the {settings.SKILL_TIMEOUT_SEC}s deadline"
            skill_registry.update_execution(execution_id, "failed", {"error": message})
            import json
            yield {"event": "timeout", "data": json.dumps({"event": "timeout", "message": message})}
        except Exception as e:
            skill_registry.update_execution(execution_id, "failed", {"error": str(e)})
            import json
            yield {"event": "error", "data": json.dumps({"event": "error", "message": str(e)})}

    return EventSourceResponse(event_stream())


@router.get("/executions/{project_id}")
def list_executions(
    project_id: str,
    current_user: User = Depends(get_current_user),
):
    return skill_registry.get_executions(project_id)
