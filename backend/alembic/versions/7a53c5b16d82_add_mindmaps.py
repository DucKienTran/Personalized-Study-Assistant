"""add mindmaps

Revision ID: 7a53c5b16d82
Revises: add_user_daily_activities
Create Date: 2026-08-18 11:31:29.642788

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = "7a53c5b16d82"
down_revision: Union[str, Sequence[str], None] = "add_user_daily_activities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "mindmaps",
        sa.Column(
            "id",
            mysql.BIGINT(unsigned=True),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("notebook_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("source_document_ids", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["notebook_id"],
            ["notebooks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mindmaps_id"), "mindmaps", ["id"], unique=False)
    op.create_index(
        op.f("ix_mindmaps_notebook_id"),
        "mindmaps",
        ["notebook_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_mindmaps_notebook_id"), table_name="mindmaps")
    op.drop_index(op.f("ix_mindmaps_id"), table_name="mindmaps")
    op.drop_table("mindmaps")
