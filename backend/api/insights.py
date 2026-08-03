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

    # Register as Resource
    from resources.registry import register_resource, add_reference
    summary = req.content.get("summary", "")[:100]
    register_resource(
        resource_type="insight",
        resource_id=insight.id,
        name=req.question[:80] or "Insight",
        project_id=req.project_id,
        description=summary,
        metadata={"summary": summary, "sql": req.content.get("sql"), "row_count": req.content.get("row_count")},
        ref_id=insight.id,
    )

    charts = req.content.get("charts", [])
    for c in charts:
        chart = Chart(insight_id=insight.id, chart_type=c.get("type", "bar"), config=c.get("options", {}))
        db.add(chart)
        db.flush()

        # Register each chart as Resource
        chart_title = c.get("title", "Chart")
        chart_uri = register_resource(
            resource_type="chart",
            resource_id=chart.id,
            name=chart_title,
            project_id=req.project_id,
            description=f"{c.get('type', 'bar')} chart",
            metadata={"chart_type": c.get("type", "bar"), "title": chart_title},
            ref_id=chart.id,
        )
        # Link chart → insight
        add_reference(f"chart://{chart.id}", f"insight://{insight.id}", "belongs_to")
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
