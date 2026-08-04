"""Workflow API — CRUD, run, and Chat→Workflow conversion."""
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from database import get_db
from database.session import SessionLocal
from models.user import User
from models.project import Project
from models.workflow import Workflow, WorkflowStep
from services.auth import get_current_user
from services.run_tracker import RunTracker, get_run_detail

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


class WorkflowCreate(BaseModel):
    name: str
    description: str = ""
    project_id: str


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    steps: list[dict] | None = None


@router.get("/{project_id}")
def list_workflows(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(
        Project.id == project_id, Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    workflows = (
        db.query(Workflow)
        .filter(Workflow.project_id == project_id)
        .order_by(Workflow.updated_at.desc())
        .all()
    )
    return [
        {
            "id": w.id,
            "name": w.name,
            "description": w.description,
            "status": w.status,
            "version": w.version,
            "step_count": len(w.steps) if w.steps else 0,
            "last_run_at": w.last_run_at.isoformat() if w.last_run_at else None,
            "created_at": w.created_at.isoformat() if w.created_at else None,
        }
        for w in workflows
    ]


@router.post("")
def create_workflow(
    req: WorkflowCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wf = Workflow(name=req.name, description=req.description, project_id=req.project_id)
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return {"id": wf.id, "name": wf.name}


@router.get("/detail/{workflow_id}")
def get_workflow(workflow_id: str, db: Session = Depends(get_db)):
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "id": wf.id,
        "name": wf.name,
        "description": wf.description,
        "project_id": wf.project_id,
        "status": wf.status,
        "steps": [
            {
                "id": s.id,
                "sort_order": s.sort_order,
                "type": s.type,
                "config": s.config,
                "input_refs": s.input_refs,
                "output_ref": s.output_ref,
                "description": s.description,
            }
            for s in (wf.steps or [])
        ],
    }


@router.put("/{workflow_id}")
def update_workflow(
    workflow_id: str,
    req: WorkflowUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if req.name is not None:
        wf.name = req.name
    if req.description is not None:
        wf.description = req.description
    if req.steps is not None:
        # Clear existing steps and rebuild
        db.query(WorkflowStep).filter(WorkflowStep.workflow_id == workflow_id).delete()
        for i, step in enumerate(req.steps):
            ws = WorkflowStep(
                workflow_id=workflow_id,
                sort_order=i,
                type=step.get("type", "sql"),
                config=step.get("config", {}),
                input_refs=step.get("input_refs", []),
                output_ref=step.get("output_ref"),
                description=step.get("description", ""),
            )
            db.add(ws)
        wf.version = (wf.version or 0) + 1

    db.commit()
    return {"status": "updated"}


@router.delete("/{workflow_id}")
def delete_workflow(workflow_id: str, db: Session = Depends(get_db)):
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db.delete(wf)
    db.commit()
    return {"status": "deleted"}


@router.post("/{workflow_id}/run")
async def run_workflow(workflow_id: str, db: Session = Depends(get_db)):
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    steps = db.query(WorkflowStep).filter(
        WorkflowStep.workflow_id == workflow_id
    ).order_by(WorkflowStep.sort_order).all()

    tracker = RunTracker(run_type="workflow", project_id=wf.project_id, ref_id=workflow_id)
    tracker.start()

    from agents.llm import chat
    from agents.tools import execute_query, suggest_chart

    async def event_stream():
        try:
            for step in steps:
                tracker.add_step(step.type)
                yield {"event": "step_start", "data": json.dumps({"event": "step_start", "type": step.type, "step": step.sort_order + 1})}

                if step.type == "sql":
                    sql = step.config.get("sql_template", "SELECT * FROM data LIMIT 10")
                    result = execute_query(wf.project_id, sql)
                    yield {"event": "step_done", "data": json.dumps({"event": "step_done", "type": "sql", "result": result})}

                elif step.type == "skill":
                    skill_name = step.config.get("skill_name", "")
                    yield {"event": "step_done", "data": json.dumps({"event": "step_done", "type": "skill", "message": f"Skill: {skill_name}"})}

                elif step.type == "analyze" or step.type == "insight":
                    prompt = step.config.get("prompt", "Analyze the results.")
                    resp = chat([{"role": "user", "content": prompt}])
                    yield {"event": "step_done", "data": json.dumps({"event": "step_done", "type": step.type, "insight": resp[:500]})}

                elif step.type == "visualize":
                    chart = suggest_chart("", {"columns": [], "rows": [], "row_count": 0})
                    yield {"event": "step_done", "data": json.dumps({"event": "step_done", "type": "visualize", "chart": chart})}

            # Update last_run_at
            wf.last_run_at = datetime.now(timezone.utc).replace(tzinfo=None)
            wf.status = "active"
            db.commit()

            tracker.complete()
            yield {"event": "workflow_done", "data": json.dumps({"event": "workflow_done", "message": "Workflow complete"})}

        except Exception as e:
            tracker.fail(str(e))
            yield {"event": "error", "data": json.dumps({"event": "error", "message": str(e)})}

    return EventSourceResponse(event_stream())


@router.post("/from-run/{run_id}")
def create_from_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Convert a chat analysis run into a Workflow draft."""
    detail = get_run_detail(run_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Run not found")

    wf = Workflow(
        name=f"Workflow from {detail['type']} analysis",
        project_id="",  # Will be set below
        created_from=run_id,
        status="draft",
    )
    # Extract project_id from the run steps' context — use the run's project_id from DB
    from models.run import Run
    run_rec = db.query(Run).filter(Run.id == run_id).first()
    if run_rec:
        wf.project_id = run_rec.project_id

    db.add(wf)
    db.flush()

    for i, step in enumerate(detail.get("steps", [])):
        step_type = step["type"]
        config = {}
        if step_type in ("sql", "execute"):
            step_type = "sql"
            config["sql_template"] = step.get("sql") or "SELECT * FROM data"
        elif step_type in ("analyze", "insight"):
            step_type = "insight"
            config["prompt"] = "Analyze the results and provide insights."
        elif step_type == "visualize":
            config["chart_type"] = "auto"

        ws = WorkflowStep(
            workflow_id=wf.id,
            sort_order=i,
            type=step_type,
            config=config,
            description=step.get("output_summary") or step.get("input_summary") or "",
        )
        db.add(ws)

    db.commit()

    # Register as Resource
    from resources.registry import register_resource
    register_resource(
        resource_type="workflow",
        resource_id=wf.id,
        name=wf.name,
        project_id=wf.project_id,
        description=f"{len(detail['steps'])} steps",
        ref_id=wf.id,
    )

    return {"id": wf.id, "name": wf.name, "step_count": len(detail["steps"])}
