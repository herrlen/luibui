"""nightly re-check of published versions (S4-7 part 1, H02)

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-03 17:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("scans", sa.Column("paketversion_id", sa.Uuid(), nullable=True))
    op.add_column(
        "scans", sa.Column("nachpruefung_ausgewertet_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("scans", sa.Column("nachpruefung_neu", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_scans_paketversion_id_versions"),
        "scans",
        "versions",
        ["paketversion_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_scans_paketversion_id"), "scans", ["paketversion_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_scans_paketversion_id"), table_name="scans")
    op.drop_constraint(op.f("fk_scans_paketversion_id_versions"), "scans", type_="foreignkey")
    op.drop_column("scans", "nachpruefung_neu")
    op.drop_column("scans", "nachpruefung_ausgewertet_at")
    op.drop_column("scans", "paketversion_id")
