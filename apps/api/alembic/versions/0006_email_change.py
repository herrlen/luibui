"""change of the account's e-mail address by a link to the new address (S2-10)

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-03 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("email_tokens", sa.Column("neue_email", sa.String(length=320), nullable=True))
    op.drop_constraint(op.f("ck_email_tokens_zweck"), "email_tokens", type_="check")
    op.create_check_constraint(
        op.f("ck_email_tokens_zweck"),
        "email_tokens",
        "zweck IN ('bestaetigung', 'passwort', 'email')",
    )
    op.create_check_constraint(
        op.f("ck_email_tokens_neue_email"),
        "email_tokens",
        "(zweck = 'email') = (neue_email IS NOT NULL)",
    )


def downgrade() -> None:
    op.execute("DELETE FROM email_tokens WHERE zweck = 'email'")
    op.drop_constraint(op.f("ck_email_tokens_neue_email"), "email_tokens", type_="check")
    op.drop_constraint(op.f("ck_email_tokens_zweck"), "email_tokens", type_="check")
    op.create_check_constraint(
        op.f("ck_email_tokens_zweck"), "email_tokens", "zweck IN ('bestaetigung', 'passwort')"
    )
    op.drop_column("email_tokens", "neue_email")
