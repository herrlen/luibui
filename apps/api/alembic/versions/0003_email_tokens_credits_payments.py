"""email confirmation, credits and payments

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-27 20:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NOW = sa.text("now()")
_UUID = sa.text("gen_random_uuid()")


def upgrade() -> None:
    op.create_table(
        "email_tokens",
        sa.Column("id", sa.Uuid(), server_default=_UUID, nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("secret_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_email_tokens_owner_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_tokens")),
        sa.UniqueConstraint("secret_hash", name=op.f("uq_email_tokens_secret_hash")),
    )
    op.create_index(op.f("ix_email_tokens_owner_id"), "email_tokens", ["owner_id"])

    status = postgresql.ENUM("angelegt", "bezahlt", "abgebrochen", name="zahlung_status")
    status.create(op.get_bind(), checkfirst=True)
    op.execute("CREATE SEQUENCE IF NOT EXISTS belegnummer START 1")
    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), server_default=_UUID, nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("order_id", sa.String(length=64), nullable=False),
        sa.Column("capture_id", sa.String(length=64), nullable=True),
        sa.Column("paket", sa.String(length=20), nullable=False),
        sa.Column("pruefungen", sa.Integer(), nullable=False),
        sa.Column("betrag_cent", sa.Integer(), nullable=False),
        sa.Column("waehrung", sa.String(length=3), server_default="EUR", nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(name="zahlung_status", create_type=False),
            server_default="angelegt",
            nullable=False,
        ),
        sa.Column("belegnummer", sa.BigInteger(), nullable=True),
        sa.Column("kaeufer_email", sa.String(length=320), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("bezahlt_am", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_payments_owner_id_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payments")),
        sa.UniqueConstraint("order_id", name=op.f("uq_payments_order_id")),
        sa.UniqueConstraint("belegnummer", name=op.f("uq_payments_belegnummer")),
    )
    op.create_index(op.f("ix_payments_owner_id"), "payments", ["owner_id"])

    op.create_table(
        "credit_entries",
        sa.Column("id", sa.Uuid(), server_default=_UUID, nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("grund", sa.String(length=20), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=True),
        sa.Column("payment_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.CheckConstraint(
            "grund IN ('start', 'kauf', 'pruefung', 'erstattung')",
            name=op.f("ck_credit_entries_grund"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_credit_entries_owner_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name=op.f("fk_credit_entries_scan_id_scans"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            name=op.f("fk_credit_entries_payment_id_payments"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_credit_entries")),
    )
    op.create_index(op.f("ix_credit_entries_owner_id"), "credit_entries", ["owner_id"])
    op.create_index(op.f("ix_credit_entries_scan_id"), "credit_entries", ["scan_id"])
    op.create_index(
        "uq_credit_entries_start",
        "credit_entries",
        ["owner_id"],
        unique=True,
        postgresql_where=sa.text("grund = 'start'"),
    )
    op.create_index(
        "uq_credit_entries_erstattung",
        "credit_entries",
        ["scan_id"],
        unique=True,
        postgresql_where=sa.text("grund = 'erstattung'"),
    )


def downgrade() -> None:
    op.drop_table("credit_entries")
    op.drop_table("payments")
    op.execute("DROP SEQUENCE IF EXISTS belegnummer")
    postgresql.ENUM(name="zahlung_status").drop(op.get_bind(), checkfirst=True)
    op.drop_table("email_tokens")
