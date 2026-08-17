"""add quiz profile offset

Revision ID: b019c33049c7
Revises: 73a0a0a04afb
Create Date: 2026-08-07 03:16:16.079462

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b019c33049c7"
down_revision: Union[str, Sequence[str], None] = "73a0a0a04afb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    def table_exists(table_name: str) -> bool:
        return sa.inspect(bind).has_table(table_name)

    def column_exists(table_name: str, column_name: str) -> bool:
        return column_name in {
            column["name"] for column in sa.inspect(bind).get_columns(table_name)
        }

    if not table_exists("quiz_profile_offsets"):
        op.create_table(
            "quiz_profile_offsets",
            sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
            sa.Column("user_id", mysql.BIGINT(unsigned=True), nullable=False),
            sa.Column("difficulty_offset", sa.Float(), server_default="0", nullable=False),
            sa.Column("coverage_offset", sa.Float(), server_default="0", nullable=False),
            sa.Column("reasoning_depth_offset", sa.Float(), server_default="0", nullable=False),
            sa.Column("anti_repetition_offset", sa.Float(), server_default="0", nullable=False),
            sa.Column("relevance_offset", sa.Float(), server_default="0", nullable=False),
            sa.Column("time_per_question_offset", sa.Float(), server_default="0", nullable=False),
            sa.Column(
                "strict_source_grounding_offset",
                sa.Float(),
                server_default="0",
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id"),
        )

    offset_indexes = {
        index["name"] for index in sa.inspect(bind).get_indexes("quiz_profile_offsets")
    }
    if "ix_quiz_profile_offsets_id" not in offset_indexes:
        op.create_index(
            op.f("ix_quiz_profile_offsets_id"),
            "quiz_profile_offsets",
            ["id"],
            unique=False,
        )

    if not column_exists("quiz_attempts", "started_at"):
        op.add_column(
            "quiz_attempts",
            sa.Column(
                "started_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
        )
    if not column_exists("quiz_attempts", "submitted_at"):
        op.add_column(
            "quiz_attempts",
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not column_exists("quiz_attempts", "duration_seconds"):
        op.add_column(
            "quiz_attempts",
            sa.Column("duration_seconds", sa.Integer(), nullable=True),
        )
    if not column_exists("quiz_attempts", "question_order"):
        op.add_column(
            "quiz_attempts",
            sa.Column("question_order", sa.JSON(), nullable=True),
        )
        op.execute("UPDATE quiz_attempts SET question_order = JSON_ARRAY() WHERE question_order IS NULL")
        op.alter_column(
            "quiz_attempts",
            "question_order",
            existing_type=sa.JSON(),
            nullable=False,
        )
    if not column_exists("quiz_attempts", "updated_at"):
        op.add_column(
            "quiz_attempts",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
        )
    if not column_exists("quiz_progress", "time_spent_seconds"):
        op.add_column(
            "quiz_progress",
            sa.Column("time_spent_seconds", sa.Integer(), nullable=True),
        )
    if not column_exists("quizzes", "generation_strategy"):
        op.add_column(
            "quizzes",
            sa.Column(
                "generation_strategy",
                sa.String(length=30),
                server_default="manual",
                nullable=False,
            ),
        )
    if not column_exists("quizzes", "question_types"):
        op.add_column("quizzes", sa.Column("question_types", sa.JSON(), nullable=True))
    if not column_exists("quizzes", "difficulty_distribution"):
        op.add_column(
            "quizzes",
            sa.Column("difficulty_distribution", sa.JSON(), nullable=True),
        )
    if not column_exists("quizzes", "updated_at"):
        op.add_column(
            "quizzes",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
        )
    if column_exists("quizzes", "difficulty"):
        op.drop_column("quizzes", "difficulty")
    if column_exists("quizzes", "generation_mode"):
        op.drop_column("quizzes", "generation_mode")


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "quizzes",
        sa.Column(
            "generation_mode",
            mysql.VARCHAR(length=20),
            server_default=sa.text("'simple'"),
            nullable=False,
        ),
    )
    op.add_column("quizzes", sa.Column("difficulty", mysql.VARCHAR(length=20), nullable=True))
    op.drop_column("quizzes", "updated_at")
    op.drop_column("quizzes", "difficulty_distribution")
    op.drop_column("quizzes", "question_types")
    op.drop_column("quizzes", "generation_strategy")
    op.drop_column("quiz_progress", "time_spent_seconds")
    op.drop_column("quiz_attempts", "updated_at")
    op.drop_column("quiz_attempts", "question_order")
    op.drop_column("quiz_attempts", "duration_seconds")
    op.drop_column("quiz_attempts", "submitted_at")
    op.drop_column("quiz_attempts", "started_at")
    op.drop_index(op.f("ix_quiz_profile_offsets_id"), table_name="quiz_profile_offsets")
    op.drop_table("quiz_profile_offsets")
    # ### end Alembic commands ###
