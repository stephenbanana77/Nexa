"""Workflow API — CRUD, run, and Chat→Workflow conversion."""
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
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


def _get_owned_workflow(workflow_id: str, user_id: str, db: Session) -> Workflow:
    """Fetch workflow and verify it belongs to a project owned by user.

    Returns 404 (not 403) to avoid leaking existence of other users' workflows.
    """
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    project = (
        db.query(Project)
        .filter(Project.id == wf.project_id, Project.user_id == user_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


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
    project = db.query(Project).filter(
        Project.id == req.project_id, Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    wf = Workflow(name=req.name, description=req.description, project_id=req.project_id)
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return {"id": wf.id, "name": wf.name}


@router.get("/detail/{workflow_id}")
def get_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wf = _get_owned_workflow(workflow_id, current_user.id, db)
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
    wf = _get_owned_workflow(workflow_id, current_user.id, db)

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
def delete_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wf = _get_owned_workflow(workflow_id, current_user.id, db)
    db.delete(wf)
    db.commit()
    return {"status": "deleted"}


@router.post("/{workflow_id}/run")
async def run_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wf = _get_owned_workflow(workflow_id, current_user.id, db)

    steps = db.query(WorkflowStep).filter(
        WorkflowStep.workflow_id == workflow_id
    ).order_by(WorkflowStep.sort_order).all()

    tracker = RunTracker(run_type="workflow", project_id=wf.project_id, ref_id=workflow_id)
    tracker.start()

    from agents.llm import chat
    from agents.tools import execute_query, suggest_chart
    import re as _re

    # ── Variable interpolation ──
    _VAR_PATTERN = _re.compile(r"\$\{(\d+)\.(\w+)\}")

    def _resolve_vars(template: str, context: dict[int, dict]) -> str:
        """Replace ${N.field} references with values from previous step outputs."""
        def _replace(match):
            step_idx = int(match.group(1))
            field = match.group(2)
            val = context.get(step_idx, {}).get(field, match.group(0))
            # Convert nested objects to a brief representation
            if isinstance(val, (dict, list)):
                return json.dumps(val, ensure_ascii=False)[:500]
            return str(val)
        return _VAR_PATTERN.sub(_replace, template)

    # ── Build step context from previous results ──
    def _build_context_from_sql(qr) -> dict:
        """Extract useful fields from a QueryResult into context dict."""
        return {
            "sql": getattr(qr, "sql", ""),
            "row_count": getattr(qr, "row_count", 0),
            "columns": getattr(qr, "columns", []),
            "rows": getattr(qr, "rows", [])[:5],  # sample rows for prompts
        }

    async def event_stream():
        completed_steps = []       # list of completed step indices
        step_context: dict[int, dict] = {}  # {step_index: {field: value}}
        partial_error = None

        for step in steps:
            step_idx = step.sort_order
            sid = tracker.add_step(step.type)
            yield {
                "event": "step_start",
                "data": json.dumps({"event": "step_start", "type": step.type, "step": step_idx + 1, "step_id": sid}),
            }

            try:
                if step.type == "sql":
                    raw_sql = step.config.get("sql_template", "SELECT * FROM data LIMIT 10")
                    sql = _resolve_vars(raw_sql, step_context)
                    qr = execute_query(wf.project_id, sql)
                    tracker.complete_step(sid, sql=sql)
                    step_context[step_idx] = _build_context_from_sql(qr)
                    yield {
                        "event": "step_done",
                        "data": json.dumps({"event": "step_done", "type": "sql", "sql": sql, "result": qr}),
                    }

                elif step.type == "skill":
                    skill_name = step.config.get("skill_name", "")
                    yield {
                        "event": "step_done",
                        "data": json.dumps({"event": "step_done", "type": "skill", "message": f"Skill: {skill_name}"}),
                    }
                    step_context[step_idx] = {"skill": skill_name, "status": "completed"}

                elif step.type in ("analyze", "insight"):
                    raw_prompt = step.config.get("prompt", "Analyze the results.")
                    # Enrich prompt with previous step context
                    enriched_prompt = _resolve_vars(raw_prompt, step_context)
                    if step_context:
                        enriched_prompt += f"\n\nPrevious results: {json.dumps({k: v for k, v in list(step_context.items())[-3:]}, ensure_ascii=False, default=str)[:1500]}"
                    resp = chat([{"role": "user", "content": enriched_prompt}])
                    tracker.complete_step(sid, output_summary=resp[:200])
                    step_context[step_idx] = {"insight": resp[:1000], "prompt": enriched_prompt[:200]}
                    yield {
                        "event": "step_done",
                        "data": json.dumps({"event": "step_done", "type": step.type, "insight": resp}),
                    }

                elif step.type == "visualize":
                    # Use previous SQL results for intelligent chart suggestion
                    prev_result = None
                    for k in sorted(step_context.keys(), reverse=True):
                        if "columns" in step_context[k]:
                            prev_result = step_context[k]
                            break
                    chart = suggest_chart(
                        step.config.get("chart_type", ""),
                        {
                            "columns": prev_result.get("columns", []) if prev_result else [],
                            "rows": prev_result.get("rows", []) if prev_result else [],
                            "row_count": prev_result.get("row_count", 0) if prev_result else 0,
                        },
                    ) if prev_result else suggest_chart("", {"columns": [], "rows": [], "row_count": 0})

                    if chart:
                        tracker.complete_step(sid, chart_config=chart)
                    step_context[step_idx] = {"chart": chart, "chart_type": step.config.get("chart_type", "auto")}
                    yield {
                        "event": "step_done",
                        "data": json.dumps({"event": "step_done", "type": "visualize", "chart": chart}),
                    }

                else:
                    tracker.complete_step(sid, output_summary=f"Unknown step type: {step.type}")
                    yield {
                        "event": "step_done",
                        "data": json.dumps({"event": "step_done", "type": step.type, "warning": f"Unknown step type: {step.type}"}),
                    }

                completed_steps.append(step_idx)

            except Exception as step_err:
                # Partial failure: record error, preserve completed steps
                tracker.complete_step(sid, output_summary=f"ERROR: {str(step_err)[:200]}")
                partial_error = str(step_err)
                yield {
                    "event": "step_error",
                    "data": json.dumps({"event": "step_error", "type": step.type, "step": step_idx + 1, "message": str(step_err)}),
                }
                break  # Stop on first failure

        # Update workflow metadata
        wf.last_run_at = datetime.now(timezone.utc).replace(tzinfo=None)
        wf.status = "active"
        db.commit()

        token_estimate = len(json.dumps(step_context, default=str))
        if partial_error:
            tracker.fail(partial_error)
            yield {
                "event": "workflow_done",
                "data": json.dumps({
                    "event": "workflow_done",
                    "status": "partial",
                    "completed_steps": len(completed_steps),
                    "total_steps": len(steps),
                    "error": partial_error,
                }),
            }
        else:
            tracker.complete(token_estimate=token_estimate)
            yield {
                "event": "workflow_done",
                "data": json.dumps({
                    "event": "workflow_done",
                    "status": "complete",
                    "completed_steps": len(completed_steps),
                    "total_steps": len(steps),
                }),
            }

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

    # Verify the run's project belongs to the current user
    project = db.query(Project).filter(
        Project.id == wf.project_id, Project.user_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Run not found")

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
