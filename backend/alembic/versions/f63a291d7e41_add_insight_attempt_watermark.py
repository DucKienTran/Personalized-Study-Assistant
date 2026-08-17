"""add insight attempt watermark

Revision ID: f63a291d7e41
Revises: e52f7c9231ad
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision: str = "f63a291d7e41"
down_revision: str | Sequence[str] | None = "e52f7c9231ad"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "dashboard_insight_caches",
        sa.Column("source_attempt_id", mysql.BIGINT(unsigned=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("dashboard_insight_caches", "source_attempt_id")
