"""moderation of disputed findings (S3-7)

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
    op.add_column("finding_status", sa.Column("moderation", sa.String(length=20), nullable=True))
    op.add_column("finding_status", sa.Column("moderation_notiz", sa.Text(), nullable=True))
    op.add_column("finding_status", sa.Column("moderiert_von", sa.Uuid(), nullable=True))
    op.add_column(
        "finding_status", sa.Column("moderiert_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_foreign_key(
        op.f("fk_finding_status_moderiert_von_users"),
        "finding_status",
        "users",
        ["moderiert_von"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        op.f("ck_finding_status_moderation_wert"),
        "finding_status",
        "moderation IS NULL OR moderation IN ('bestritten', 'fehlalarm')",
    )
    op.create_index(
        "ix_finding_status_bestritten",
        "finding_status",
        ["updated_at"],
        postgresql_where=sa.text("status = 'bestritten'"),
    )


def downgrade() -> None:
    op.drop_index("ix_finding_status_bestritten", table_name="finding_status")
    op.drop_constraint(op.f("ck_finding_status_moderation_wert"), "finding_status", type_="check")
    op.drop_constraint(
        op.f("fk_finding_status_moderiert_von_users"), "finding_status", type_="foreignkey"
    )
    op.drop_column("finding_status", "moderiert_at")
    op.drop_column("finding_status", "moderiert_von")
    op.drop_column("finding_status", "moderation_notiz")
    op.drop_column("finding_status", "moderation")
