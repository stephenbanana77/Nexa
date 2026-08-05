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
    pass


def downgrade() -> None:
    pass
