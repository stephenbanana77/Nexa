"""Notebook API."""
import json
import subprocess
import sys

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from models.project import Project, Dataset, Notebook, Cell
from services.auth import get_current_user

router = APIRouter(prefix="/api/notebooks", tags=["notebooks"])


class CellCreate(BaseModel):
    cell_type: str
    content: str = ""
    sort_order: int = 0


class NotebookCreate(BaseModel):
    project_id: str
    dataset_id: str | None = None
    cells: list[CellCreate] | None = None
    name: str = "Untitled"


@router.post("/")
def create_notebook(
    req: NotebookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(
        Project.id == req.project_id, Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if req.dataset_id and not db.query(Dataset).filter(
        Dataset.id == req.dataset_id, Dataset.project_id == req.project_id
    ).first():
        raise HTTPException(status_code=404, detail="Dataset not found")

    nb = Notebook(project_id=req.project_id, dataset_id=req.dataset_id, name=req.name)
    db.add(nb)
    db.flush()

    for i, c in enumerate(req.cells or []):
        cell = Cell(notebook_id=nb.id, cell_type=c.cell_type, content=c.content, sort_order=c.sort_order or i)
        db.add(cell)

    db.commit()
    db.refresh(nb)
    return {"id": nb.id, "name": nb.name}


@router.get("/project/{project_id}")
def list_notebooks(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(
        Project.id == project_id, Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    notebooks = db.query(Notebook).filter(Notebook.project_id == project_id).all()
    return [{"id": n.id, "name": n.name, "dataset_id": n.dataset_id, "created_at": n.created_at.isoformat()} for n in notebooks]


@router.get("/{notebook_id}")
def get_notebook(
    notebook_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    nb = db.query(Notebook).filter(Notebook.id == notebook_id).first()
    if not nb:
        raise HTTPException(status_code=404, detail="Notebook not found")

    project = db.query(Project).filter(
        Project.id == nb.project_id, Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Not found")

    cells = db.query(Cell).filter(Cell.notebook_id == notebook_id).order_by(Cell.sort_order).all()
    return {
        "id": nb.id,
        "name": nb.name,
        "dataset_id": nb.dataset_id,
        "cells": [
            {"id": c.id, "cell_type": c.cell_type, "content": c.content, "sort_order": c.sort_order}
            for c in cells
        ],
    }


class CellUpdate(BaseModel):
    cell_type: str | None = None
    content: str | None = None


class NotebookUpdate(BaseModel):
    name: str | None = None
    dataset_id: str | None = None


@router.put("/{notebook_id}")
def update_notebook(
    notebook_id: str,
    req: NotebookUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notebook = _get_owned_notebook(db, notebook_id, current_user.id)
    if req.dataset_id is not None:
        dataset = db.query(Dataset).filter(
            Dataset.id == req.dataset_id,
            Dataset.project_id == notebook.project_id,
        ).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        notebook.dataset_id = req.dataset_id
    if req.name is not None:
        notebook.name = req.name
    db.commit()
    return {"id": notebook.id, "name": notebook.name, "dataset_id": notebook.dataset_id}


def _get_owned_notebook(db: Session, notebook_id: str, user_id: str) -> Notebook:
    notebook = db.query(Notebook).join(Project).filter(
        Notebook.id == notebook_id, Project.user_id == user_id
    ).first()
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return notebook


def _get_owned_cell(db: Session, cell_id: str, user_id: str) -> Cell:
    cell = db.query(Cell).join(Notebook).join(Project).filter(
        Cell.id == cell_id, Project.user_id == user_id
    ).first()
    if not cell:
        raise HTTPException(status_code=404, detail="Cell not found")
    return cell


@router.put("/cells/{cell_id}")
def update_cell(
    cell_id: str,
    req: CellUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cell = _get_owned_cell(db, cell_id, current_user.id)
    if req.cell_type is not None:
        cell.cell_type = req.cell_type
    if req.content is not None:
        cell.content = req.content
    db.commit()
    return {"status": "ok"}


@router.post("/{notebook_id}/cells")
def add_cell(
    notebook_id: str,
    req: CellCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    nb = _get_owned_notebook(db, notebook_id, current_user.id)
    cell = Cell(notebook_id=notebook_id, cell_type=req.cell_type, content=req.content, sort_order=req.sort_order)
    db.add(cell)
    db.commit()
    db.refresh(cell)
    return {"id": cell.id, "cell_type": cell.cell_type, "content": cell.content, "sort_order": cell.sort_order}


@router.delete("/cells/{cell_id}")
def delete_cell(cell_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cell = _get_owned_cell(db, cell_id, current_user.id)
    db.delete(cell)
    db.commit()
    return {"ok": True}


_PYTHON_RUNNER = r'''
import json, sys
payload = json.loads(sys.stdin.read())
safe_builtins = {
    "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
    "enumerate": enumerate, "filter": filter, "float": float, "int": int,
    "len": len, "list": list, "map": map, "max": max, "min": min,
    "print": print, "range": range, "round": round, "set": set,
    "sorted": sorted, "str": str, "sum": sum, "tuple": tuple, "zip": zip,
    "Exception": Exception, "ValueError": ValueError, "TypeError": TypeError,
}
scope = {"__builtins__": safe_builtins, "columns": payload["columns"], "rows": payload["rows"]}
exec(payload["code"], scope, scope)
'''


@router.post("/cells/{cell_id}/execute")
def execute_cell(
    cell_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Execute a SQL or Python cell against the notebook's bound dataset."""
    cell = _get_owned_cell(db, cell_id, current_user.id)
    notebook = cell.notebook
    if not notebook.dataset_id:
        raise HTTPException(status_code=400, detail="Choose a dataset for this notebook before running cells")
    dataset = db.query(Dataset).filter(
        Dataset.id == notebook.dataset_id,
        Dataset.project_id == notebook.project_id,
    ).first()
    if not dataset or not dataset.file_path:
        raise HTTPException(status_code=400, detail="Notebook dataset is not available")
    if dataset.source_type == "mysql":
        raise HTTPException(status_code=400, detail="MySQL notebook execution is not connected yet; use direct SQL from the data page")

    from services.dataset_tables import bind_default_table, dataset_table_name
    from services.sql_policy import QUERY_TIMEOUT_SEC, validate_sql
    from tools import get_engine, load_dataset

    table_name = dataset_table_name(dataset.id)
    load_dataset(notebook.project_id, dataset.file_path, dataset.source_type, table_name=table_name)
    engine = get_engine(notebook.project_id)

    if cell.cell_type == "sql":
        is_safe, sql_or_error = validate_sql(cell.content)
        if not is_safe:
            raise HTTPException(status_code=400, detail=sql_or_error)
        try:
            return engine.query(
                bind_default_table(sql_or_error, dataset.id),
                timeout_sec=QUERY_TIMEOUT_SEC,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Query error: {str(exc)}") from exc

    if cell.cell_type != "python":
        raise HTTPException(status_code=400, detail="Only SQL and Python cells can be executed")

    preview = engine.preview(table_name=table_name, limit=1000)
    payload = json.dumps({"code": cell.content, "columns": preview.columns, "rows": preview.rows}, default=str)
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-c", _PYTHON_RUNNER],
            input=payload,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=408, detail="Python cell exceeded the 5 second execution limit") from exc
    output = completed.stdout[:100_000]
    error = completed.stderr.strip()[:4_000] if completed.returncode else None
    return {"output": output, "error": error, "dataset_id": dataset.id, "sample_rows": len(preview.rows)}
