"""add semantic approval and report publication states"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table(table) and column.name not in {c["name"] for c in inspector.get_columns(table)}:
        op.add_column(table, column)


def upgrade() -> None:
    _add_column_if_missing("semantic_metrics", sa.Column("status", sa.String(20), nullable=False, server_default="draft"))
    _add_column_if_missing("semantic_metrics", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing("semantic_metrics", sa.Column("approved_by", sa.String(32), nullable=True))
    _add_column_if_missing("semantic_dimensions", sa.Column("status", sa.String(20), nullable=False, server_default="draft"))
    _add_column_if_missing("semantic_dimensions", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing("semantic_dimensions", sa.Column("approved_by", sa.String(32), nullable=True))
    _add_column_if_missing("analysis_reports", sa.Column("status", sa.String(20), nullable=False, server_default="draft"))
    _add_column_if_missing("analysis_reports", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing("analysis_reports", sa.Column("published_by", sa.String(32), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table, columns in {
        "analysis_reports": ("published_by", "published_at", "status"),
        "semantic_dimensions": ("approved_by", "approved_at", "status"),
        "semantic_metrics": ("approved_by", "approved_at", "status"),
    }.items():
        if inspector.has_table(table):
            existing = {c["name"] for c in inspector.get_columns(table)}
            for column in columns:
                if column in existing:
                    op.drop_column(table, column)
