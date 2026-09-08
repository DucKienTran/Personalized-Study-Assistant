"""add message resource json

Revision ID: a94b31f07d2e
Revises: c3f29a1e4b72
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a94b31f07d2e"
down_revision: str | None = "c3f29a1e4b72"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("resource_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "resource_json")
