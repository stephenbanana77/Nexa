"""Semantic layer API."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import UTC, datetime
import re

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.project import Dataset, Project, SemanticDimension, SemanticMetric
from models.user import User
from services.auth import get_current_user
from services.semantic_layer import list_semantic_layer, seed_semantic_layer_from_schema
from services.dataset_tables import dataset_table_name
from services.sql_policy import inspect_sql_policy
from tools import get_engine, load_dataset

router = APIRouter(prefix="/api/semantic", tags=["semantic"])


class MetricCreate(BaseModel):
    project_id: str
    dataset_id: str | None = None
    name: str = Field(min_length=1, max_length=255)
    expression: str = Field(min_length=1)
    description: str = ""
    format: str = "number"


class DimensionCreate(BaseModel):
    project_id: str
    dataset_id: str | None = None
    name: str = Field(min_length=1, max_length=255)
    column: str = Field(min_length=1, max_length=255)
    description: str = ""


class DefinitionStatusUpdate(BaseModel):
    status: str = Field(pattern="^(draft|approved|rejected)$")


def _assert_project(db: Session, project_id: str, user_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _resolve_dataset(db: Session, project_id: str, dataset_id: str | None) -> Dataset:
    query = db.query(Dataset).filter(Dataset.project_id == project_id)
    if dataset_id:
        dataset = query.filter(Dataset.id == dataset_id).first()
    else:
        matches = query.order_by(Dataset.created_at.desc()).limit(2).all()
        if len(matches) != 1:
            raise HTTPException(status_code=400, detail="Choose one dataset before approving this definition")
        dataset = matches[0]
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if not dataset.file_path:
        raise HTTPException(status_code=400, detail="This dataset cannot be validated by the local SQL engine")
    if dataset.source_type == "mysql":
        raise HTTPException(status_code=400, detail="MySQL semantic approval is not connected yet; import a snapshot before approving metrics")
    return dataset


def _validate_metric(db: Session, metric: SemanticMetric) -> Dataset:
    dataset = _resolve_dataset(db, metric.project_id, metric.dataset_id)
    schema_names = {str(item.get("name")) for item in (dataset.schema_info or [])}
    referenced = re.findall(r'"([^"]+)"', metric.expression or "")
    if not referenced:
        raise HTTPException(status_code=400, detail="Metric expression must quote at least one dataset column")
    missing = sorted(set(referenced) - schema_names)
    if missing:
        raise HTTPException(status_code=400, detail=f"Metric references missing columns: {', '.join(missing)}")

    table_name = dataset_table_name(dataset.id)
    sql = f'SELECT {metric.expression} AS metric_value FROM "{table_name}"'
    decision = inspect_sql_policy(sql)
    if not decision.is_safe:
        raise HTTPException(status_code=400, detail=f"Metric expression is not safe: {decision.reason}")
    load_dataset(dataset.project_id, dataset.file_path, dataset.source_type, table_name=table_name)
    try:
        get_engine(dataset.project_id).query(decision.final_sql or sql)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Metric expression failed validation: {str(exc)}") from exc
    return dataset


@router.get("/{project_id}")
def get_semantic_layer(
    project_id: str,
    dataset_id: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _assert_project(db, project_id, current_user.id)
    return list_semantic_layer(db, project_id, dataset_id)


@router.post("/metrics", status_code=status.HTTP_201_CREATED)
def create_metric(
    req: MetricCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _assert_project(db, req.project_id, current_user.id)
    if req.dataset_id:
        _resolve_dataset(db, req.project_id, req.dataset_id)
    metric = SemanticMetric(**req.model_dump())
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return {"id": metric.id, "created_at": metric.created_at.isoformat()}


@router.post("/dimensions", status_code=status.HTTP_201_CREATED)
def create_dimension(
    req: DimensionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _assert_project(db, req.project_id, current_user.id)
    if req.dataset_id:
        dataset = _resolve_dataset(db, req.project_id, req.dataset_id)
        if req.column not in {str(item.get("name")) for item in (dataset.schema_info or [])}:
            raise HTTPException(status_code=400, detail=f"Dimension column '{req.column}' does not exist in this dataset")
    dimension = SemanticDimension(**req.model_dump())
    db.add(dimension)
    db.commit()
    db.refresh(dimension)
    return {"id": dimension.id, "created_at": dimension.created_at.isoformat()}


@router.post("/{project_id}/seed")
def seed_semantic_layer(
    project_id: str,
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _assert_project(db, project_id, current_user.id)
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.project_id == project_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return seed_semantic_layer_from_schema(db, project_id, dataset_id, dataset.schema_info)


@router.delete("/metrics/{metric_id}")
def delete_metric(
    metric_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    metric = db.query(SemanticMetric).filter(SemanticMetric.id == metric_id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    _assert_project(db, metric.project_id, current_user.id)
    db.delete(metric)
    db.commit()
    return {"ok": True}


@router.delete("/dimensions/{dimension_id}")
def delete_dimension(
    dimension_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dimension = db.query(SemanticDimension).filter(SemanticDimension.id == dimension_id).first()
    if not dimension:
        raise HTTPException(status_code=404, detail="Dimension not found")
    _assert_project(db, dimension.project_id, current_user.id)
    db.delete(dimension)
    db.commit()
    return {"ok": True}


@router.patch("/metrics/{metric_id}/status")
def update_metric_status(
    metric_id: str,
    req: DefinitionStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    metric = db.query(SemanticMetric).filter(SemanticMetric.id == metric_id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    _assert_project(db, metric.project_id, current_user.id)
    if req.status == "approved":
        dataset = _validate_metric(db, metric)
        if metric.dataset_id is None:
            metric.dataset_id = dataset.id
    metric.status = req.status
    metric.approved_at = datetime.now(UTC) if req.status == "approved" else None
    metric.approved_by = current_user.id if req.status == "approved" else None
    db.commit()
    return {"id": metric.id, "status": metric.status, "approved_at": metric.approved_at.isoformat() if metric.approved_at else None}


@router.patch("/dimensions/{dimension_id}/status")
def update_dimension_status(
    dimension_id: str,
    req: DefinitionStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dimension = db.query(SemanticDimension).filter(SemanticDimension.id == dimension_id).first()
    if not dimension:
        raise HTTPException(status_code=404, detail="Dimension not found")
    _assert_project(db, dimension.project_id, current_user.id)
    if req.status == "approved":
        dataset = _resolve_dataset(db, dimension.project_id, dimension.dataset_id)
        schema_names = {str(item.get("name")) for item in (dataset.schema_info or [])}
        if dimension.column not in schema_names:
            raise HTTPException(status_code=400, detail=f"Dimension column '{dimension.column}' does not exist in this dataset")
        if dimension.dataset_id is None:
            dimension.dataset_id = dataset.id
    dimension.status = req.status
    dimension.approved_at = datetime.now(UTC) if req.status == "approved" else None
    dimension.approved_by = current_user.id if req.status == "approved" else None
    db.commit()
    return {"id": dimension.id, "status": dimension.status, "approved_at": dimension.approved_at.isoformat() if dimension.approved_at else None}
