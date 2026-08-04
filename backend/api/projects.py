"""Project and Dataset API routes."""
import os
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from models.project import Project, Dataset
from services.auth import get_current_user
from utils.config import settings

router = APIRouter(prefix="/api", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str


class ProjectResponse(BaseModel):
    id: str
    name: str
    created_at: str


@router.get("/projects", response_model=list[ProjectResponse])
def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    projects = (
        db.query(Project)
        .filter(Project.user_id == current_user.id)
        .order_by(Project.updated_at.desc())
        .all()
    )
    return [
        ProjectResponse(id=p.id, name=p.name, created_at=p.created_at.isoformat())
        for p in projects
    ]


@router.post("/projects", response_model=ProjectResponse)
def create_project(
    req: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = Project(name=req.name, user_id=current_user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return ProjectResponse(
        id=project.id, name=project.name, created_at=project.created_at.isoformat()
    )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(
        id=project.id, name=project.name, created_at=project.created_at.isoformat()
    )


@router.post("/datasets/preview")
async def preview_dataset(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Preview first 10 rows + schema without saving."""
    ext = os.path.splitext(file.filename or "data.csv")[1].lower()
    if ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    import tempfile, contextlib
    contents = await file.read()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    try:
        tmp.write(contents)
        tmp.close()

        if ext == ".csv":
            import chardet
            with open(tmp.name, "rb") as raw:
                result = chardet.detect(raw.read(100000))
            encoding = result["encoding"] or "utf-8"
            confidence = round(result.get("confidence", 0) * 100)
            df = pd.read_csv(tmp.name, encoding=encoding, encoding_errors="replace", nrows=1000)
        else:
            encoding = "n/a"
            confidence = 100
            df = pd.read_excel(tmp.name, nrows=1000)

        preview_rows = df.head(10).fillna("").values.tolist()
        columns = [
            {"name": col, "type": str(df[col].dtype),
             "missing": int(df[col].isna().sum()), "missing_pct": round(df[col].isna().mean() * 100, 1)}
            for col in df.columns
        ]
        return {
            "file_name": file.filename, "file_size": len(contents),
            "encoding": encoding, "encoding_confidence": confidence,
            "columns": columns, "preview_rows": preview_rows, "total_rows_in_sample": len(df),
        }
    finally:
        with contextlib.suppress(OSError):
            os.unlink(tmp.name)


@router.post("/datasets/upload")
async def upload_dataset(
    project_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if file.size and file.size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB} MB",
        )

    ext = os.path.splitext(file.filename or "data.csv")[1].lower()
    if ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    os.makedirs(settings.STORAGE_PATH, exist_ok=True)
    file_path = os.path.join(settings.STORAGE_PATH, f"{project_id}_{file.filename}")
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    try:
        if ext == ".csv":
            # Auto-detect encoding (Kaggle datasets often use non-UTF-8)
            import chardet
            with open(file_path, "rb") as raw:
                result = chardet.detect(raw.read(100000))
            encoding = result["encoding"] or "utf-8"
            df = pd.read_csv(file_path, encoding=encoding, encoding_errors="replace")
        else:
            df = pd.read_excel(file_path)
    except Exception as e:
        # Clean up the saved file on parse failure
        try:
            os.remove(file_path)
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    schema_info = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        missing = int(df[col].isna().sum())
        missing_pct = round(missing / len(df) * 100, 1)
        schema_info.append({
            "name": col,
            "type": dtype,
            "missing_count": missing,
            "missing_pct": missing_pct,
        })

    dataset = Dataset(
        project_id=project_id,
        name=file.filename or "dataset",
        source_type=ext.lstrip("."),
        file_path=file_path,
        row_count=len(df),
        column_count=len(df.columns),
        schema_info=schema_info,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    from tools import load_dataset, get_engine

    load_dataset(project_id, file_path, dataset.source_type)
    engine = get_engine(project_id)

    # Register as Resource
    from resources.registry import register_resource
    register_resource(
        resource_type="dataset",
        resource_id=dataset.id,
        name=dataset.name,
        project_id=project_id,
        description=f"{dataset.row_count} rows, {dataset.column_count} columns",
        metadata={"row_count": dataset.row_count, "column_count": dataset.column_count, "source_type": dataset.source_type},
        ref_id=dataset.id,
    )

    return {
        "id": dataset.id,
        "name": dataset.name,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
        "schema_info": schema_info,
        "preview": engine.preview(limit=1000),
    }


@router.get("/datasets")
def list_datasets(
    project_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Dataset)
        .join(Project)
        .filter(Project.user_id == current_user.id)
    )
    if project_id:
        query = query.filter(Dataset.project_id == project_id)
    datasets = query.all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "project_id": d.project_id,
            "row_count": d.row_count,
            "column_count": d.column_count,
        }
        for d in datasets
    ]


@router.get("/datasets/{dataset_id}")
def get_dataset(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    project = (
        db.query(Project)
        .filter(Project.id == dataset.project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return {
        "id": dataset.id,
        "name": dataset.name,
        "source_type": dataset.source_type,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
        "schema_info": dataset.schema_info,
        "created_at": dataset.created_at.isoformat(),
    }


class QueryRequest(BaseModel):
    sql: str


@router.get("/datasets/{dataset_id}/preview")
def preview_dataset(
    dataset_id: str,
    limit: int = 1000,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    project = (
        db.query(Project)
        .filter(Project.id == dataset.project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Dataset not found")

    from tools import get_engine, load_dataset

    load_dataset(project.id, dataset.file_path, dataset.source_type)
    engine = get_engine(project.id)

    return engine.preview(limit=limit)


@router.post("/datasets/{dataset_id}/query")
def query_dataset(
    dataset_id: str,
    req: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    project = (
        db.query(Project)
        .filter(Project.id == dataset.project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Dataset not found")

    from tools import get_engine, load_dataset

    load_dataset(project.id, dataset.file_path, dataset.source_type)
    engine = get_engine(project.id)

    try:
        return engine.query(req.sql)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query error: {str(e)}")


class MySQLConnectRequest(BaseModel):
    project_id: str
    host: str
    port: int = 3306
    user: str
    password: str
    database: str


@router.post("/datasets/connect-mysql")
def connect_mysql(
    req: MySQLConnectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Connect a MySQL database as a data source."""
    project = (
        db.query(Project)
        .filter(Project.id == req.project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from tools import register_mysql, get_engine

    try:
        register_mysql(req.project_id, req.host, req.port, req.user, req.password, req.database)
        connector = get_engine(req.project_id)
        tables = connector.get_tables()

        # Create a virtual dataset entry for the MySQL connection
        dataset = Dataset(
            project_id=req.project_id,
            name=f"mysql://{req.database}",
            source_type="mysql",
            file_path="",
            row_count=sum(t["row_count"] for t in tables),
            column_count=0,
            schema_info=[
                {"name": t["name"], "type": "table", "missing_pct": 0, "missing_count": 0}
                for t in tables
            ],
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)

        return {
            "id": dataset.id,
            "name": dataset.name,
            "tables": tables,
            "row_count": dataset.row_count,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"MySQL connection failed: {str(e)}")
