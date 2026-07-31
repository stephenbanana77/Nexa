"""Insight API."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from models.project import Project, Insight, Chart
from services.auth import get_current_user

router = APIRouter(prefix="/api/insights", tags=["insights"])


class InsightSave(BaseModel):
    project_id: str
    question: str
    content: dict


@router.post("/")
def save_insight(
    req: InsightSave,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(
        Project.id == req.project_id, Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    insight = Insight(project_id=req.project_id, question=req.question, content=req.content)
    db.add(insight)
    db.commit()
    db.refresh(insight)

    charts = req.content.get("charts", [])
    for c in charts:
        chart = Chart(insight_id=insight.id, chart_type=c.get("type", "bar"), config=c.get("config", {}))
        db.add(chart)
    db.commit()

    return {"id": insight.id, "created_at": insight.created_at.isoformat()}


@router.get("/project/{project_id}")
def list_insights(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(
        Project.id == project_id, Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    insights = (
        db.query(Insight)
        .filter(Insight.project_id == project_id)
        .order_by(Insight.created_at.desc())
        .all()
    )
    return [
        {
            "id": i.id,
            "question": i.question,
            "content": i.content,
            "created_at": i.created_at.isoformat(),
        }
        for i in insights
    ]
