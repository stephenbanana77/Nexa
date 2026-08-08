"""Project and Dataset API routes."""
import os
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, SecretStr
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
    # Check file size before reading into memory
    if file.size and file.size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")
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
    safe_name = "".join(c for c in file.filename if c.isalnum() or c in "._-")
    safe_name = safe_name.strip(". ") or "upload"
    file_path = os.path.join(settings.STORAGE_PATH, f"{project_id}_{safe_name}")
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


@router.get("/datasets/by-id/{dataset_id}")
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


@router.get("/datasets/by-id/{dataset_id}/preview")
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


@router.post("/datasets/by-id/{dataset_id}/query")
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
    from agents.tools import _validate_sql

    # Enforce the same SQL safety policy as the Chat Agent
    is_safe, result = _validate_sql(req.sql)
    if not is_safe:
        raise HTTPException(status_code=400, detail=result)
    safe_sql = result

    load_dataset(project.id, dataset.file_path, dataset.source_type)
    engine = get_engine(project.id)

    try:
        return engine.query(safe_sql)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query error: {str(e)}")


@router.get("/datasets/relationships")
def get_dataset_relationships(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Detect potential join keys between datasets in a project.

    Finds columns with matching names/types across datasets and suggests JOIN paths.
    """
    project = db.query(Project).filter(
        Project.id == project_id, Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    datasets = db.query(Dataset).filter(Dataset.project_id == project_id).all()
    if len(datasets) < 2:
        return {"relationships": [], "hint": "Need at least 2 datasets to detect relationships"}

    from tools import get_engine, load_dataset

    # Load all datasets and collect schemas
    schemas: list[dict] = []
    for ds in datasets:
        load_dataset(project.id, ds.file_path, ds.source_type)
        engine = get_engine(project.id, table_name=ds.table_name)
        cols = engine.get_schema(ds.table_name)
        schemas.append({
            "dataset_id": ds.id,
            "dataset_name": ds.name,
            "table_name": ds.table_name,
            "columns": {c.name: c.type for c in cols},
            "row_count": ds.row_count,
        })

    # Find common column names with compatible types
    relationships = []
    for i in range(len(schemas)):
        for j in range(i + 1, len(schemas)):
            a, b = schemas[i], schemas[j]
            common = []
            for col_name, col_type in a["columns"].items():
                if col_name in b["columns"]:
                    common.append({
                        "column": col_name,
                        "type_a": col_type,
                        "type_b": b["columns"][col_name],
                        "compatible": _types_compatible(col_type, b["columns"][col_name]),
                    })

            if common:
                # Score by number of compatible keys
                compatible_keys = [c for c in common if c["compatible"]]
                score = len(compatible_keys)
                # Heuristic: columns ending in _id are strong candidates
                strong_keys = [c for c in compatible_keys if c["column"].endswith("_id") or c["column"] == "id"]
                score += len(strong_keys) * 2

                relationships.append({
                    "source": {"id": a["dataset_id"], "name": a["dataset_name"], "rows": a["row_count"]},
                    "target": {"id": b["dataset_id"], "name": b["dataset_name"], "rows": b["row_count"]},
                    "common_columns": common,
                    "compatible_keys": [c["column"] for c in compatible_keys],
                    "strong_keys": [c["column"] for c in strong_keys],
                    "suggested_join": f"FROM {a['table_name']} JOIN {b['table_name']} ON {a['table_name']}.{compatible_keys[0]['column']} = {b['table_name']}.{compatible_keys[0]['column']}" if compatible_keys else None,
                    "score": score,
                })

    # Sort by score descending
    relationships.sort(key=lambda r: r["score"], reverse=True)

    return {
        "relationships": relationships,
        "datasets": [{"id": s["dataset_id"], "name": s["dataset_name"], "table": s["table_name"], "rows": s["row_count"]} for s in schemas],
    }


def _types_compatible(t1: str, t2: str) -> bool:
    """Check if two SQL types can be joined."""
    numeric = {"INTEGER", "BIGINT", "INT", "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC", "REAL"}
    text = {"VARCHAR", "TEXT", "STRING", "CHAR"}
    t1u, t2u = t1.upper(), t2.upper()
    if t1u == t2u:
        return True
    if t1u in numeric and t2u in numeric:
        return True
    if t1u in text and t2u in text:
        return True
    return False


class MySQLConnectRequest(BaseModel):
    project_id: str
    host: str
    port: int = 3306
    user: str
    password: SecretStr
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


@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a project and all associated data (datasets, files, DuckDB cache)."""
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Clean up uploaded files
    import glob
    pattern = os.path.join(settings.STORAGE_PATH, f"{project_id}_*")
    for fp in glob.glob(pattern):
        try:
            os.remove(fp)
        except OSError:
            pass

    # Remove DuckDB engine from registry
    from tools.query_engine import engine_registry
    engine_registry.remove(project_id)

    # Delete project (ORM cascades datasets, conversations, messages, etc.)
    db.delete(project)
    db.commit()
    return {"ok": True, "deleted": project_id}
