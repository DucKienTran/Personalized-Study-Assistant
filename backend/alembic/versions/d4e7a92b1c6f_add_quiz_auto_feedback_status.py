"""add quiz auto feedback status

Revision ID: d4e7a92b1c6f
Revises: a94b31f07d2e
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d4e7a92b1c6f"
down_revision: str | None = "a94b31f07d2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "quizzes",
        sa.Column(
            "auto_feedback_status",
            sa.String(length=16),
            server_default="pending",
            nullable=False,
        ),
    )
    op.execute(
        sa.text(
            """
            UPDATE quizzes
            SET auto_feedback_status = 'skipped'
            WHERE EXISTS (
                SELECT 1
                FROM quiz_attempts
                WHERE quiz_attempts.quiz_id = quizzes.id
                  AND quiz_attempts.attempt_status = 'completed'
            )
            """
        )
    )


def downgrade() -> None:
    op.drop_column("quizzes", "auto_feedback_status")
