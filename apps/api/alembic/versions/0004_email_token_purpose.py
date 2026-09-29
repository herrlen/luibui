"""purpose of one-time e-mail links: confirmation or password reset

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-29 15:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing links are all confirmation links.
    op.add_column(
        "email_tokens",
        sa.Column("zweck", sa.String(length=20), server_default="bestaetigung", nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_email_tokens_zweck"), "email_tokens", "zweck IN ('bestaetigung', 'passwort')"
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_email_tokens_zweck"), "email_tokens", type_="check")
    op.drop_column("email_tokens", "zweck")
