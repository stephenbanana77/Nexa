"""Workflow and WorkflowStep models."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSON

from database.session import Base


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")  # draft | active | archived
    inputs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_from: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)  # run_id
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    created_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)

    steps: Mapped[list["WorkflowStep"]] = relationship(
        "WorkflowStep", back_populates="workflow", cascade="all, delete-orphan",
        order_by="WorkflowStep.sort_order"
    )


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("workflows.id"), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # sql | skill | analyze | visualize | insight | python
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    input_refs: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    output_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="steps")
