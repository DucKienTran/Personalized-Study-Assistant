"""drop username column from users

Revision ID: b680f5779d06
Revises: 7199df08c90c
Create Date: 2026-07-23 07:03:05.285603
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b680f5779d06"
down_revision: Union[str, Sequence[str], None] = "7199df08c90c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "username")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("username", sa.String(length=255), nullable=False),
    )
    op.create_index(
        "ix_users_username",
        "users",
        ["username"],
        unique=True,
    )