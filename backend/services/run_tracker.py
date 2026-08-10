"""Run tracker — records execution traces for Agent, Skill, and Workflow runs."""
from datetime import datetime, timezone
from database.session import SessionLocal
from models.run import Run, RunStep


def _utcnow():
    from datetime import datetime as _dt, timezone as _tz
    return _dt.now(_tz.utc).replace(tzinfo=None)


class RunTracker:
    """Tracks a single execution run with its steps."""

    def __init__(self, run_type: str, project_id: str, ref_id: str = None, created_by: str = None):
        self.run_type = run_type
        self.project_id = project_id
        self.ref_id = ref_id
        self.created_by = created_by
        self.run_id = None
        self._step_order = 0

    def start(self, plan: list[str] = None) -> str:
        """Start a new run, return the run_id."""
        db = SessionLocal()
        try:
            run = Run(
                type=self.run_type,
                ref_id=self.ref_id,
                project_id=self.project_id,
                status="running",
                plan=plan or [],
                started_at=_utcnow(),
                created_by=self.created_by,
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            self.run_id = run.id
            return run.id
        finally:
            db.close()

    def add_step(self, step_type: str, input_summary: str = None) -> str:
        """Add a new step, return step_id."""
        if not self.run_id:
            self.start()
        self._step_order += 1
        db = SessionLocal()
        try:
            step = RunStep(
                run_id=self.run_id,
                sort_order=self._step_order,
                type=step_type,
                input_summary=input_summary,
                started_at=_utcnow(),
            )
            db.add(step)
            db.commit()
            db.refresh(step)
            return step.id
        finally:
            db.close()

    def complete_step(self, step_id: str, output_summary: str = None, sql: str = None, chart_config: dict = None, duration_ms: int = None):
        """Mark a step as completed."""
        db = SessionLocal()
        try:
            step = db.query(RunStep).filter(RunStep.id == step_id).first()
            if step:
                step.output_summary = output_summary or step.output_summary
                step.sql = sql or step.sql
                step.chart_config = chart_config or step.chart_config
                step.finished_at = _utcnow()
                if step.started_at:
                    step.duration_ms = int((step.finished_at - step.started_at).total_seconds() * 1000)
                if duration_ms is not None:
                    step.duration_ms = duration_ms
                db.commit()
        finally:
            db.close()

    def update_lineage(self, patch: dict):
        """Merge a lineage patch into the current run."""
        if not self.run_id:
            return
        db = SessionLocal()
        try:
            run = db.query(Run).filter(Run.id == self.run_id).first()
            if run:
                run.lineage = _deep_merge(dict(run.lineage or {}), patch)
                db.commit()
        finally:
            db.close()

    def fail_step(self, step_id: str, error: str):
        """Mark a step as failed."""
        db = SessionLocal()
        try:
            step = db.query(RunStep).filter(RunStep.id == step_id).first()
            if step:
                step.error = error
                step.finished_at = _utcnow()
                if step.started_at:
                    step.duration_ms = int((step.finished_at - step.started_at).total_seconds() * 1000)
                db.commit()
        finally:
            db.close()

    def complete(self, token_estimate: int = None):
        """Complete the entire run."""
        if not self.run_id:
            return
        db = SessionLocal()
        try:
            run = db.query(Run).filter(Run.id == self.run_id).first()
            if run:
                run.status = "done"
                run.finished_at = _utcnow()
                if run.started_at:
                    run.duration_ms = int((run.finished_at - run.started_at).total_seconds() * 1000)
                if token_estimate is not None:
                    run.token_estimate = token_estimate
                db.commit()
        finally:
            db.close()

    def fail(self, error: str = None):
        """Mark the run as failed."""
        if not self.run_id:
            return
        db = SessionLocal()
        try:
            run = db.query(Run).filter(Run.id == self.run_id).first()
            if run:
                run.status = "failed"
                run.finished_at = _utcnow()
                if run.started_at:
                    run.duration_ms = int((run.finished_at - run.started_at).total_seconds() * 1000)
                db.commit()
        finally:
            db.close()


def get_run_history(project_id: str, limit: int = 20) -> list[dict]:
    """Get recent run history for a project."""
    db = SessionLocal()
    try:
        runs = (
            db.query(Run)
            .filter(Run.project_id == project_id)
            .order_by(Run.started_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "type": r.type,
                "ref_id": r.ref_id,
                "status": r.status,
                "plan": r.plan,
                "lineage": _lineage_summary(r.lineage),
                "duration_ms": r.duration_ms,
                "token_estimate": r.token_estimate,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            }
            for r in runs
        ]
    finally:
        db.close()


def get_run_detail(run_id: str) -> dict | None:
    """Get a run with its steps."""
    db = SessionLocal()
    try:
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            return None
        steps = (
            db.query(RunStep)
            .filter(RunStep.run_id == run_id)
            .order_by(RunStep.sort_order)
            .all()
        )
        return {
            "id": run.id,
            "type": run.type,
            "ref_id": run.ref_id,
            "project_id": run.project_id,
            "status": run.status,
            "plan": run.plan,
            "lineage": run.lineage or {},
            "duration_ms": run.duration_ms,
            "token_estimate": run.token_estimate,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "steps": [
                {
                    "id": s.id,
                    "sort_order": s.sort_order,
                    "type": s.type,
                    "input_summary": s.input_summary,
                    "output_summary": s.output_summary,
                    "sql": s.sql,
                    "error": s.error,
                    "duration_ms": s.duration_ms,
                    "chart_config": s.chart_config,
                }
                for s in steps
            ],
        }
    finally:
        db.close()


def _deep_merge(base: dict, patch: dict) -> dict:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_merge(dict(base[key]), value)
        elif isinstance(value, list) and isinstance(base.get(key), list):
            base[key] = [*base[key], *value]
        else:
            base[key] = value
    return base


def _lineage_summary(lineage: dict | None) -> dict | None:
    if not lineage:
        return None
    result = lineage.get("result") or {}
    return {
        "question": lineage.get("question"),
        "final_sql": lineage.get("final_sql"),
        "row_count": result.get("row_count"),
        "sql_attempt_count": len(lineage.get("sql_attempts") or []),
        "error_count": len(lineage.get("errors") or []),
    }
