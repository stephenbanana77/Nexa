"""Global search across projects, datasets, insights, and workflows."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import get_db
from models.user import User
from models.project import Project, Dataset, Insight, Chart
from models.workflow import Workflow
from services.auth import get_current_user

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
def global_search(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search across all user content."""
    results = []

    # Projects
    projects = (
        db.query(Project)
        .filter(Project.user_id == current_user.id)
        .filter(Project.name.ilike(f"%{q}%"))
        .limit(5)
        .all()
    )
    for p in projects:
        results.append({"type": "project", "id": p.id, "title": p.name, "subtitle": "", "link": f"/project/{p.id}"})

    # Datasets
    datasets = (
        db.query(Dataset)
        .join(Project, Dataset.project_id == Project.id)
        .filter(Project.user_id == current_user.id)
        .filter(Dataset.name.ilike(f"%{q}%"))
        .limit(5)
        .all()
    )
    for d in datasets:
        results.append({"type": "dataset", "id": d.id, "title": d.name, "subtitle": f"{d.row_count} rows, {d.column_count} cols", "link": f"/project/{d.project_id}"})

    # Insights
    insights = (
        db.query(Insight)
        .join(Project, Insight.project_id == Project.id)
        .filter(Project.user_id == current_user.id)
        .filter(Insight.question.ilike(f"%{q}%"))
        .limit(5)
        .all()
    )
    for i in insights:
        results.append({"type": "insight", "id": i.id, "title": i.question[:80], "subtitle": "", "link": f"/project/{i.project_id}"})

    # Workflows
    workflows = (
        db.query(Workflow)
        .join(Project, Workflow.project_id == Project.id)
        .filter(Project.user_id == current_user.id)
        .filter(or_(Workflow.name.ilike(f"%{q}%"), Workflow.description.ilike(f"%{q}%")))
        .limit(5)
        .all()
    )
    for w in workflows:
        results.append({"type": "workflow", "id": w.id, "title": w.name, "subtitle": w.description or "", "link": f"/project/{w.project_id}"})

    return {"query": q, "results": results}
