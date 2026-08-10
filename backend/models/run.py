"""Run and RunStep models for execution observability."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSON

from database.session import Base


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # "chat" | "skill" | "workflow"
    ref_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # conversation_id / skill_execution_id / workflow_id
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")  # running | done | failed
    plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Agent plan steps
    lineage: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Question/schema/SQL/result provenance
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_estimate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    created_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)


class RunStep(Base):
    __tablename__ = "run_steps"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("runs.id"), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # sql | skill | analyze | visualize | understand | plan | select_skill | execute_skill
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    sql: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chart_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
