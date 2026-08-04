"""Notebook API."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from models.project import Project, Notebook, Cell
from services.auth import get_current_user

router = APIRouter(prefix="/api/notebooks", tags=["notebooks"])


class CellCreate(BaseModel):
    cell_type: str
    content: str = ""
    sort_order: int = 0


class NotebookCreate(BaseModel):
    project_id: str
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

    nb = Notebook(project_id=req.project_id, name=req.name)
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
    return [{"id": n.id, "name": n.name, "created_at": n.created_at.isoformat()} for n in notebooks]


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
        "cells": [
            {"id": c.id, "cell_type": c.cell_type, "content": c.content, "sort_order": c.sort_order}
            for c in cells
        ],
    }


class CellUpdate(BaseModel):
    cell_type: str | None = None
    content: str | None = None


@router.put("/cells/{cell_id}")
def update_cell(
    cell_id: str,
    req: CellUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cell = db.query(Cell).filter(Cell.id == cell_id).first()
    if not cell:
        raise HTTPException(status_code=404, detail="Cell not found")
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
    nb = db.query(Notebook).filter(Notebook.id == notebook_id).first()
    if not nb:
        raise HTTPException(status_code=404, detail="Notebook not found")
    cell = Cell(notebook_id=notebook_id, cell_type=req.cell_type, content=req.content, sort_order=req.sort_order)
    db.add(cell)
    db.commit()
    db.refresh(cell)
    return {"id": cell.id, "cell_type": cell.cell_type, "content": cell.content, "sort_order": cell.sort_order}


@router.delete("/cells/{cell_id}")
def delete_cell(cell_id: str, db: Session = Depends(get_db)):
    cell = db.query(Cell).filter(Cell.id == cell_id).first()
    if not cell:
        raise HTTPException(status_code=404, detail="Cell not found")
    db.delete(cell)
    db.commit()
    return {"ok": True}


@router.post("/cells/{cell_id}/execute")
def execute_python_cell(
    cell_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Execute a Python cell in a restricted sandbox."""
    cell = db.query(Cell).filter(Cell.id == cell_id).first()
    if not cell:
        raise HTTPException(status_code=404, detail="Cell not found")
    if cell.cell_type != "python":
        raise HTTPException(status_code=400, detail="Only Python cells can be executed")

    # Restricted builtins — only safe operations
    safe_builtins = {
        "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
        "enumerate": enumerate, "filter": filter, "float": float,
        "int": int, "len": len, "list": list, "map": map, "max": max,
        "min": min, "print": print, "range": range, "round": round,
        "set": set, "sorted": sorted, "str": str, "sum": sum, "tuple": tuple,
        "zip": zip, "True": True, "False": False, "None": None,
        "Exception": Exception, "ValueError": ValueError, "TypeError": TypeError,
    }

    import sys, io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    result = None
    error = None
    try:
        exec(cell.content, {"__builtins__": safe_builtins})
        result = sys.stdout.getvalue()
    except Exception as e:
        error = str(e)
    finally:
        sys.stdout = old_stdout

    return {"output": result, "error": error}
