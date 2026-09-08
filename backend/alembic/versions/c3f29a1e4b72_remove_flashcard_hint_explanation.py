"""remove flashcard hint and explanation

Revision ID: c3f29a1e4b72
Revises: b78fd66b4c37
Create Date: 2026-08-23

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3f29a1e4b72"
down_revision: Union[str, Sequence[str], None] = "b78fd66b4c37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("flashcards", "explanation")
    op.drop_column("flashcards", "hint")


def downgrade() -> None:
    op.add_column("flashcards", sa.Column("hint", sa.Text(), nullable=True))
    op.add_column("flashcards", sa.Column("explanation", sa.Text(), nullable=True))
