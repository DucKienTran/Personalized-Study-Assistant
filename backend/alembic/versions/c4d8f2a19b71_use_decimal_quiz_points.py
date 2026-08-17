"""use decimal quiz points

Revision ID: c4d8f2a19b71
Revises: b019c33049c7
Create Date: 2026-08-10 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c4d8f2a19b71"
down_revision: Union[str, Sequence[str], None] = "b019c33049c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "quizzes",
        "target_total_points",
        existing_type=sa.Integer(),
        type_=sa.Numeric(12, 2),
        existing_nullable=False,
        existing_server_default=sa.text("100"),
    )
    op.alter_column(
        "quiz_questions",
        "points",
        existing_type=sa.Integer(),
        type_=sa.Numeric(12, 2),
        existing_nullable=False,
        existing_server_default=sa.text("1"),
    )
    op.alter_column(
        "quiz_attempts",
        "score",
        existing_type=sa.Float(),
        type_=sa.Numeric(12, 2),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "quiz_attempts",
        "score",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Float(),
        existing_nullable=True,
    )
    op.alter_column(
        "quiz_questions",
        "points",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Integer(),
        existing_nullable=False,
        existing_server_default=sa.text("1"),
    )
    op.alter_column(
        "quizzes",
        "target_total_points",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Integer(),
        existing_nullable=False,
        existing_server_default=sa.text("100"),
    )
