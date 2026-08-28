"""Project and Dataset models."""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSON

from database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner = relationship("User", back_populates="projects")
    datasets = relationship("Dataset", back_populates="project", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="project", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="project", cascade="all, delete-orphan")


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    column_count: Mapped[int] = mapped_column(Integer, default=0)
    schema_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    project = relationship("Project", back_populates="datasets")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), default="New Conversation")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    project = relationship("Project", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("conversations.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    conversation = relationship("Conversation", back_populates="messages")


class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    project = relationship("Project", back_populates="insights")
    charts = relationship("Chart", back_populates="insight", cascade="all, delete-orphan")


class SemanticMetric(Base):
    __tablename__ = "semantic_metrics"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False
    )
    dataset_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("datasets.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    expression: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    format: Mapped[str] = mapped_column(String(50), default="number")
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    project = relationship("Project")
    dataset = relationship("Dataset")


class SemanticDimension(Base):
    __tablename__ = "semantic_dimensions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False
    )
    dataset_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("datasets.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    column: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    project = relationship("Project")
    dataset = relationship("Dataset")


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False
    )
    dataset_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("datasets.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    semantic_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    memory: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    project = relationship("Project")
    dataset = relationship("Dataset")


class Chart(Base):
    __tablename__ = "charts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    insight_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("insights.id"), nullable=False
    )
    chart_type: Mapped[str] = mapped_column(String(50), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    insight = relationship("Insight", back_populates="charts")


class Notebook(Base):
    __tablename__ = "notebooks"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), default="Untitled Notebook")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project = relationship("Project")
    cells = relationship("Cell", back_populates="notebook", cascade="all, delete-orphan",
                         order_by="Cell.sort_order")


class Cell(Base):
    __tablename__ = "cells"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    notebook_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("notebooks.id"), nullable=False
    )
    cell_type: Mapped[str] = mapped_column(String(20), nullable=False)  # markdown, sql, python
    content: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    notebook = relationship("Notebook", back_populates="cells")
