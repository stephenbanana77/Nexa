"""Resource model — unified URI-based references for all analysis artifacts."""
import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSON

from database.session import Base


class ResourceType(str, Enum):
    DATASET = "dataset"
    CHART = "chart"
    INSIGHT = "insight"
    NOTEBOOK = "notebook"
    WORKFLOW = "workflow"
    CONNECTION = "connection"
    TABLE = "table"


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    uri: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False, index=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True, default=dict)
    ref_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # FK to original entity (Dataset.id, Chart.id, etc.)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)


class ResourceReference(Base):
    """Tracks which resources reference which (e.g., chart -> dataset, insight -> chart)."""
    __tablename__ = "resource_references"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_uri: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    target_uri: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    relation: Mapped[str] = mapped_column(String(50), nullable=False, default="references")  # references, generates, depends_on
