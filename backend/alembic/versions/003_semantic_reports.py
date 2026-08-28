"""add semantic layer and analysis reports

Revision ID: 003
Revises: 002
Create Date: 2026-08-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The initial baseline creates the complete metadata for new databases;
    # retain explicit table definitions for upgrades from the old baseline.
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("semantic_metrics"):
        op.create_table(
            "semantic_metrics",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("project_id", sa.UUID(), nullable=False),
            sa.Column("dataset_id", sa.UUID(), nullable=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("expression", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("format", sa.String(length=50), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("approved_by", sa.String(length=32), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if not inspector.has_table("semantic_dimensions"):
        op.create_table(
            "semantic_dimensions",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("project_id", sa.UUID(), nullable=False),
            sa.Column("dataset_id", sa.UUID(), nullable=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("column", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("approved_by", sa.String(length=32), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if not inspector.has_table("analysis_reports"):
        op.create_table(
            "analysis_reports",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("project_id", sa.UUID(), nullable=False),
            sa.Column("dataset_id", sa.UUID(), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("content", sa.JSON(), nullable=False),
            sa.Column("semantic_snapshot", sa.JSON(), nullable=True),
            sa.Column("memory", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("published_by", sa.String(length=32), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in ("analysis_reports", "semantic_dimensions", "semantic_metrics"):
        if inspector.has_table(table):
            op.drop_table(table)
