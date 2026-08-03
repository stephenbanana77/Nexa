"""Skill registry — discover, register, and list skills."""
from typing import AsyncGenerator
from database.session import SessionLocal
from models.skill import Skill, SkillExecution
from datetime import datetime, timezone


class SkillRegistry:
    """Central registry for skills. Skills can be loaded from DB or registered at runtime."""

    def __init__(self):
        self._runtime_skills: dict[str, dict] = {}

    def register_runtime(self, name: str, definition: dict):
        """Register a skill at runtime (e.g., built-in skills)."""
        self._runtime_skills[name] = definition

    def list_all(self) -> list[dict]:
        """List all available skills (DB + runtime)."""
        skills = []
        for name, defn in self._runtime_skills.items():
            skills.append({"name": name, **defn})
        # Also load from DB
        db = SessionLocal()
        try:
            db_skills = db.query(Skill).all()
            for s in db_skills:
                skills.append({
                    "id": s.id,
                    "name": s.name,
                    "title": s.title,
                    "description": s.description,
                    "category": s.category,
                    "icon": s.icon,
                    "definition": s.definition,
                    "version": s.version,
                    "is_builtin": s.is_builtin,
                })
        finally:
            db.close()
        return skills

    def list_by_category(self, category: str) -> list[dict]:
        return [s for s in self.list_all() if s.get("category") == category]

    def get(self, name_or_id: str) -> dict | None:
        """Get a skill by name or ID."""
        # Check runtime first
        if name_or_id in self._runtime_skills:
            return {
                "name": name_or_id,
                **self._runtime_skills[name_or_id],
            }
        # Check DB
        db = SessionLocal()
        try:
            skill = db.query(Skill).filter(
                (Skill.name == name_or_id) | (Skill.id == name_or_id)
            ).first()
            if skill:
                return {
                    "id": skill.id,
                    "name": skill.name,
                    "title": skill.title,
                    "description": skill.description,
                    "category": skill.category,
                    "icon": skill.icon,
                    "definition": skill.definition,
                    "version": skill.version,
                    "is_builtin": skill.is_builtin,
                }
        finally:
            db.close()
        return None

    def create_execution(self, skill_id_or_name: str, project_id: str, inputs: dict = None) -> str:
        """Create a skill execution record. Auto-creates DB record for runtime skills."""
        db = SessionLocal()
        try:
            # If skill_id_or_name is not a UUID, try to find or create the skill in DB
            skill_record = db.query(Skill).filter(
                (Skill.id == skill_id_or_name) | (Skill.name == skill_id_or_name)
            ).first()

            if not skill_record:
                # Runtime skill — persist to DB
                runtime = self.get(skill_id_or_name)
                if runtime:
                    skill_record = Skill(
                        name=runtime["name"],
                        title=runtime["title"],
                        description=runtime.get("description", ""),
                        category=runtime.get("category", "analysis"),
                        icon=runtime.get("icon", "ExperimentOutlined"),
                        definition=runtime.get("definition", {}),
                        version=runtime.get("version", "1.0.0"),
                        is_builtin=runtime.get("is_builtin", True),
                    )
                    db.add(skill_record)
                    db.flush()

            if not skill_record:
                raise ValueError(f"Skill '{skill_id_or_name}' not found")

            execution = SkillExecution(
                skill_id=skill_record.id,
                project_id=project_id,
                status="running",
                inputs=inputs or {},
                started_at=datetime.now(timezone.utc),
            )
            db.add(execution)
            db.commit()
            return execution.id
        finally:
            db.close()

    def update_execution(self, execution_id: str, status: str, output: dict = None):
        """Update execution status and output."""
        db = SessionLocal()
        try:
            exec_record = db.query(SkillExecution).filter(SkillExecution.id == execution_id).first()
            if exec_record:
                exec_record.status = status
                if output:
                    exec_record.output = output
                if status in ("done", "failed"):
                    exec_record.finished_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()

    def get_executions(self, project_id: str) -> list[dict]:
        """Get execution history for a project."""
        db = SessionLocal()
        try:
            executions = (
                db.query(SkillExecution)
                .filter(SkillExecution.project_id == project_id)
                .order_by(SkillExecution.started_at.desc())
                .all()
            )
            return [
                {
                    "id": e.id,
                    "skill_id": e.skill_id,
                    "status": e.status,
                    "inputs": e.inputs,
                    "output": e.output,
                    "started_at": e.started_at.isoformat() if e.started_at else None,
                    "finished_at": e.finished_at.isoformat() if e.finished_at else None,
                }
                for e in executions
            ]
        finally:
            db.close()


# Singleton
skill_registry = SkillRegistry()
