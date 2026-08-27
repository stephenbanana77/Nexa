"""add run lineage

Revision ID: 002
Revises: 001
Create Date: 2026-08-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("runs") and "lineage" not in {c["name"] for c in inspector.get_columns("runs")}:
        op.add_column("runs", sa.Column("lineage", sa.JSON(), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("runs") and "lineage" in {c["name"] for c in inspector.get_columns("runs")}:
        op.drop_column("runs", "lineage")
