"""webhook per Git project: encrypted secret and time of the last triggered check (S5-8)

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-03 19:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("webhook_secret_enc", sa.LargeBinary(), nullable=True))
    op.add_column(
        "projects", sa.Column("webhook_letzter_lauf", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("projects", "webhook_letzter_lauf")
    op.drop_column("projects", "webhook_secret_enc")
