"""finding status: what the finding was, and the outcome of a dispute (S3-7)

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-01 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("finding_status", sa.Column("rule_id", sa.String(length=200), nullable=True))
    op.add_column("finding_status", sa.Column("titel", sa.Text(), nullable=True))
    op.add_column("finding_status", sa.Column("datei", sa.Text(), nullable=True))
    op.add_column("finding_status", sa.Column("zeile", sa.Integer(), nullable=True))
    op.add_column("finding_status", sa.Column("moderation", sa.String(length=20), nullable=True))
    op.add_column(
        "finding_status", sa.Column("moderiert_am", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("finding_status", sa.Column("moderiert_von", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_finding_status_moderiert_von_users"),
        "finding_status",
        "users",
        ["moderiert_von"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        op.f("ck_finding_status_moderation_werte"),
        "finding_status",
        "moderation IS NULL OR moderation IN ('fehlalarm', 'bestritten')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_finding_status_moderation_werte"), "finding_status", type_="check")
    op.drop_constraint(
        op.f("fk_finding_status_moderiert_von_users"), "finding_status", type_="foreignkey"
    )
    for spalte in (
        "moderiert_von",
        "moderiert_am",
        "moderation",
        "zeile",
        "datei",
        "titel",
        "rule_id",
    ):
        op.drop_column("finding_status", spalte)
