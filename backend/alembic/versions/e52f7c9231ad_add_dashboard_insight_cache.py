"""add dashboard insight cache

Revision ID: e52f7c9231ad
Revises: a81f06c2d934
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision: str = "e52f7c9231ad"
down_revision: str | Sequence[str] | None = "a81f06c2d934"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dashboard_insight_caches",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("user_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("insight_text", sa.Text(), nullable=False),
        sa.Column("selected_stats", sa.JSON(), nullable=False),
        sa.Column("source_attempt_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(
        op.f("ix_dashboard_insight_caches_user_id"),
        "dashboard_insight_caches",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_dashboard_insight_caches_user_id"),
        table_name="dashboard_insight_caches",
    )
    op.drop_table("dashboard_insight_caches")
