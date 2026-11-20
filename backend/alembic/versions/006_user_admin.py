"""add workspace administrator flag"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("users") and "is_admin" not in {column["name"] for column in inspector.get_columns("users")}:
        op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
        users = sa.table("users", sa.column("id"), sa.column("created_at"), sa.column("is_admin"))
        first_user_id = op.get_bind().execute(sa.select(users.c.id).order_by(users.c.created_at.asc()).limit(1)).scalar()
        if first_user_id:
            op.get_bind().execute(users.update().where(users.c.id == first_user_id).values(is_admin=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("users") and "is_admin" in {column["name"] for column in inspector.get_columns("users")}:
        op.drop_column("users", "is_admin")
