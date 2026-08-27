"""initial

Revision ID: 001
Create Date: 2026-08-05

All tables created by create_all() in main.py.
This is the baseline migration for future schema changes.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The original baseline was empty even though production startup runs
    # `alembic upgrade head`. Create the complete current model baseline so a
    # brand-new database can be bootstrapped without relying on create_all().
    from database import Base
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    from database import Base
    Base.metadata.drop_all(bind=op.get_bind())
