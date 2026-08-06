"""Skill API routes — browse, install, and execute skills."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from database.session import SessionLocal
from models.user import User
from models.skill import Skill, SkillExecution
from services.auth import get_current_user
from skills import skill_registry

router = APIRouter(prefix="/api/skills", tags=["skills"])


class SkillInstallRequest(BaseModel):
    name: str
    title: str
    description: str = ""
    category: str = "analysis"
    icon: str = "ExperimentOutlined"
    definition: dict
    version: str = "1.0.0"


class SkillExecuteRequest(BaseModel):
    project_id: str
    params: dict = {}


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
    return {"id": skill.id, "name": skill.name, "title": skill.title}


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
):
    skill = skill_registry.get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    # Import here to avoid circular dependency
    from skills.executor import execute_skill as run_skill

    execution_id = skill_registry.create_execution(
        skill.get("id", skill_id), req.project_id, req.params
    )

    from sse_starlette.sse import EventSourceResponse

    async def event_stream():
        try:
            async for event in run_skill(skill, req.project_id, req.params):
                import json
                yield {"event": event.get("event", "step"), "data": json.dumps(event, default=str)}
            skill_registry.update_execution(execution_id, "done", {"result": "success"})
        except Exception as e:
            skill_registry.update_execution(execution_id, "failed", {"error": str(e)})
            yield {"event": "error", "data": json.dumps({"event": "error", "message": str(e)})}

    return EventSourceResponse(event_stream())


@router.get("/executions/{project_id}")
def list_executions(
    project_id: str,
    current_user: User = Depends(get_current_user),
):
    return skill_registry.get_executions(project_id)
