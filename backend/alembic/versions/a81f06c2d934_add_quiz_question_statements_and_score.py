"""add quiz question statements and awarded score

Revision ID: a81f06c2d934
Revises: d91e6f20a4c3
Create Date: 2026-08-10 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a81f06c2d934"
down_revision: Union[str, Sequence[str], None] = "d91e6f20a4c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("quiz_questions", sa.Column("statements", sa.JSON(), nullable=True))
    op.add_column(
        "quiz_progress",
        sa.Column("awarded_points", sa.Numeric(12, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("quiz_progress", "awarded_points")
    op.drop_column("quiz_questions", "statements")
