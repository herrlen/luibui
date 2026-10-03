"""what a version may do that the previous one did not (S4-6, H01)

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-03 16:00:00

Adding a column with a constant default does not run the immutability trigger (no UPDATE).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "versions",
        sa.Column(
            "aenderungen",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column("versions", sa.Column("vorversion", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("versions", "vorversion")
    op.drop_column("versions", "aenderungen")
