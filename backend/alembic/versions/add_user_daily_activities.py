"""add user daily activities

Revision ID: add_user_daily_activities
Revises: b019c33049c7
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "add_user_daily_activities"
down_revision: Union[str, Sequence[str], None] = "f63a291d7e41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_daily_activities",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("user_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("activity_date", sa.Date(), nullable=False),
        sa.Column("active_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "activity_date", name="uq_user_daily_activity_date"),
    )
    op.create_index("ix_user_daily_activities_id", "user_daily_activities", ["id"], unique=False)
    op.create_index("ix_user_daily_activities_user_id", "user_daily_activities", ["user_id"], unique=False)
    op.create_index("ix_user_daily_activities_activity_date", "user_daily_activities", ["activity_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_daily_activities_activity_date", table_name="user_daily_activities")
    op.drop_index("ix_user_daily_activities_user_id", table_name="user_daily_activities")
    op.drop_index("ix_user_daily_activities_id", table_name="user_daily_activities")
    op.drop_table("user_daily_activities")
