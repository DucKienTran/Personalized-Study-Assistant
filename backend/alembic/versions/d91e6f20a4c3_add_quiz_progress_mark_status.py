"""add quiz progress mark status

Revision ID: d91e6f20a4c3
Revises: c4d8f2a19b71
Create Date: 2026-08-10 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d91e6f20a4c3"
down_revision: Union[str, Sequence[str], None] = "c4d8f2a19b71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "quiz_progress",
        sa.Column("mark_status", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("quiz_progress", "mark_status")
