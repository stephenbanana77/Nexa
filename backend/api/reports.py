"""Insight Report API."""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.project import AnalysisReport, Dataset, Project
from models.user import User
from services.analysis_reports import analysis_memory_context, generate_report, serialize_report
from services.auth import get_current_user

router = APIRouter(prefix="/api/reports", tags=["reports"])


class ReportCreate(BaseModel):
    project_id: str
    dataset_id: str | None = None
    title: str | None = None


def _assert_project(db: Session, project_id: str, user_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("", status_code=status.HTTP_201_CREATED)
def create_report(
    req: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _assert_project(db, req.project_id, current_user.id)
    dataset_query = db.query(Dataset).filter(Dataset.project_id == req.project_id)
    if req.dataset_id:
        dataset_query = dataset_query.filter(Dataset.id == req.dataset_id)
    dataset = dataset_query.order_by(Dataset.created_at.desc()).first()
    if not dataset:
        raise HTTPException(status_code=400, detail="No dataset available for report")
    report = generate_report(db, req.project_id, dataset, req.title)
    return serialize_report(report)


@router.post("/investigate", status_code=status.HTTP_201_CREATED)
def create_auto_investigation(
    req: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _assert_project(db, req.project_id, current_user.id)
    dataset_query = db.query(Dataset).filter(Dataset.project_id == req.project_id)
    if req.dataset_id:
        dataset_query = dataset_query.filter(Dataset.id == req.dataset_id)
    dataset = dataset_query.order_by(Dataset.created_at.desc()).first()
    if not dataset:
        raise HTTPException(status_code=400, detail="No dataset available for investigation")
    title = req.title or f"{dataset.name} Auto Investigation"
    report = generate_report(db, req.project_id, dataset, title)
    return serialize_report(report)


@router.get("/project/{project_id}")
def list_reports(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _assert_project(db, project_id, current_user.id)
    reports = (
        db.query(AnalysisReport)
        .filter(AnalysisReport.project_id == project_id)
        .order_by(AnalysisReport.created_at.desc())
        .all()
    )
    return [serialize_report(report) for report in reports]


@router.get("/{report_id}")
def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.query(AnalysisReport).filter(AnalysisReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    _assert_project(db, report.project_id, current_user.id)
    return serialize_report(report)


@router.post("/{report_id}/publish")
def publish_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Publish a report only after quality and metric approval gates pass."""
    from models.project import SemanticMetric
    from services.data_quality import check_dataset_quality

    report = db.query(AnalysisReport).filter(AnalysisReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    _assert_project(db, report.project_id, current_user.id)
    if report.status == "published":
        return serialize_report(report)
    if not report.dataset_id:
        raise HTTPException(status_code=400, detail="Report has no dataset to validate")
    dataset = db.query(Dataset).filter(
        Dataset.id == report.dataset_id,
        Dataset.project_id == report.project_id,
    ).first()
    if not dataset:
        raise HTTPException(status_code=400, detail="Report dataset not found")

    quality = check_dataset_quality(report.project_id, dataset)
    if quality["status"] == "fail":
        raise HTTPException(status_code=400, detail={"message": "Fix blocking data quality issues before publishing.", "quality": quality})

    approved_metric = db.query(SemanticMetric).filter(
        SemanticMetric.project_id == report.project_id,
        SemanticMetric.status == "approved",
        (SemanticMetric.dataset_id == report.dataset_id) | (SemanticMetric.dataset_id.is_(None)),
    ).first()
    if not approved_metric:
        raise HTTPException(status_code=400, detail="Approve at least one metric before publishing this report")

    now = datetime.now(UTC)
    report.status = "published"
    report.published_at = now
    report.published_by = current_user.id
    content = dict(report.content or {})
    content["publication"] = {
        "status": "published",
        "published_at": now.isoformat(),
        "published_by": current_user.id,
        "quality_status": quality["status"],
        "approved_metric": approved_metric.name,
    }
    report.content = content
    db.commit()
    db.refresh(report)
    return serialize_report(report)


@router.get("/project/{project_id}/memory")
def get_memory_context(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _assert_project(db, project_id, current_user.id)
    return {"context": analysis_memory_context(db, project_id)}
