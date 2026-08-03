"""Run History API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from models.project import Project
from services.auth import get_current_user
from services.run_tracker import get_run_history, get_run_detail

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("/{project_id}")
def list_runs(
    project_id: str,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(
        Project.id == project_id, Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return get_run_history(project_id, limit)


@router.get("/detail/{run_id}")
def get_run(run_id: str):
    detail = get_run_detail(run_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Run not found")
    return detail
