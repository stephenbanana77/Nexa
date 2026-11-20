"""bind notebooks to datasets"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("notebooks") and "dataset_id" not in {column["name"] for column in inspector.get_columns("notebooks")}:
        op.add_column("notebooks", sa.Column("dataset_id", sa.String(32), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("notebooks") and "dataset_id" in {column["name"] for column in inspector.get_columns("notebooks")}:
        op.drop_column("notebooks", "dataset_id")
