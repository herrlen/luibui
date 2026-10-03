"""namespaces for the register (S4-1)

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-03 13:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "namespaces",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=39), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "name ~ '^[a-z0-9](?:[a-z0-9]|-(?=[a-z0-9])){1,38}$'", name=op.f("ck_namespaces_name")
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_namespaces_owner_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_namespaces")),
    )
    op.create_index(op.f("ix_namespaces_owner_id"), "namespaces", ["owner_id"])
    op.create_index("uq_namespaces_name_lower", "namespaces", [sa.text("lower(name)")], unique=True)


def downgrade() -> None:
    op.drop_index("uq_namespaces_name_lower", table_name="namespaces")
    op.drop_index(op.f("ix_namespaces_owner_id"), table_name="namespaces")
    op.drop_table("namespaces")
