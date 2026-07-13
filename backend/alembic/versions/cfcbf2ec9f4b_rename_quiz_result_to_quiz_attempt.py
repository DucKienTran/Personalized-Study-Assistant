"""rename quiz result to quiz attempt

Revision ID: cfcbf2ec9f4b
Revises: 0fae3783ff32
Create Date: 2026-07-13 02:17:08.047984

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "cfcbf2ec9f4b"
down_revision: Union[str, Sequence[str], None] = "0fae3783ff32"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("quiz_results", "quiz_attempts")

    op.add_column(
        "quiz_progress",
        sa.Column("attempt_id", mysql.BIGINT(unsigned=True), nullable=True),
    )

    op.execute("UPDATE quiz_progress SET attempt_id = result_id")

    op.alter_column(
        "quiz_progress",
        "attempt_id",
        existing_type=mysql.BIGINT(unsigned=True),
        nullable=False,
    )

    op.drop_constraint("fk_progress_result", "quiz_progress", type_="foreignkey")
    op.drop_constraint("uq_progress_per_attempt", "quiz_progress", type_="unique")

    op.create_foreign_key(
        "fk_progress_attempt",
        "quiz_progress",
        "quiz_attempts",
        ["attempt_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_progress_per_attempt", "quiz_progress", ["attempt_id", "question_id"]
    )

    op.drop_column("quiz_progress", "result_id")


def downgrade() -> None:
    op.add_column(
        "quiz_progress",
        sa.Column("result_id", mysql.BIGINT(unsigned=True), nullable=True),
    )

    op.execute("UPDATE quiz_progress SET result_id = attempt_id")

    op.alter_column(
        "quiz_progress",
        "result_id",
        existing_type=mysql.BIGINT(unsigned=True),
        nullable=False,
    )

    op.drop_constraint("fk_progress_attempt", "quiz_progress", type_="foreignkey")
    op.drop_constraint("uq_progress_per_attempt", "quiz_progress", type_="unique")

    op.drop_column("quiz_progress", "attempt_id")

    op.rename_table("quiz_attempts", "quiz_results")

    op.create_foreign_key(
        "fk_progress_result",
        "quiz_progress",
        "quiz_results",
        ["result_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_progress_per_attempt", "quiz_progress", ["result_id", "question_id"]
    )
