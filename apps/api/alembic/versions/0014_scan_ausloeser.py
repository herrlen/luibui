"""what started a check (webhook push), so its new findings can be mailed (S5-9)

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-03 20:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("scans", sa.Column("ausloeser", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("scans", "ausloeser")
