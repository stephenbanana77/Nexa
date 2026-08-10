"""Semantic layer API."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.project import Dataset, Project, SemanticDimension, SemanticMetric
from models.user import User
from services.auth import get_current_user
from services.semantic_layer import list_semantic_layer, seed_semantic_layer_from_schema

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


def _assert_project(db: Session, project_id: str, user_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


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
