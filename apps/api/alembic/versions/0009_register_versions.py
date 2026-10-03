"""register: packages under namespaces, immutable signed versions (S4-2)

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-03 15:00:00

``packages`` and ``versions`` exist since 0001 but were never used, so they are empty and the new
NOT NULL columns need no default.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UNVERAENDERLICH = """
CREATE FUNCTION versions_unveraenderlich() RETURNS trigger AS $$
BEGIN
    IF (to_jsonb(NEW) - 'yanked_at') IS DISTINCT FROM (to_jsonb(OLD) - 'yanked_at') THEN
        RAISE EXCEPTION 'published versions are immutable' USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER versions_unveraenderlich BEFORE UPDATE ON versions
    FOR EACH ROW EXECUTE FUNCTION versions_unveraenderlich();
"""


def upgrade() -> None:
    op.drop_constraint(op.f("uq_packages_namespace"), "packages", type_="unique")
    op.drop_column("packages", "namespace")
    op.add_column("packages", sa.Column("namespace_id", sa.Uuid(), nullable=False))
    op.add_column("packages", sa.Column("data_key_enc", sa.LargeBinary(), nullable=True))
    op.create_foreign_key(
        op.f("fk_packages_namespace_id_namespaces"),
        "packages",
        "namespaces",
        ["namespace_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(op.f("ix_packages_namespace_id"), "packages", ["namespace_id"])
    op.create_unique_constraint(
        op.f("uq_packages_namespace_id"), "packages", ["namespace_id", "name"]
    )
    op.add_column("versions", sa.Column("archive_bytes", sa.BigInteger(), nullable=False))
    op.add_column("versions", sa.Column("storage_key", sa.String(length=100), nullable=False))
    op.add_column(
        "versions",
        sa.Column("manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )
    op.add_column("versions", sa.Column("statement", sa.Text(), nullable=False))
    op.create_unique_constraint(op.f("uq_versions_storage_key"), "versions", ["storage_key"])
    op.execute(UNVERAENDERLICH)


def downgrade() -> None:
    op.execute("DROP TRIGGER versions_unveraenderlich ON versions")
    op.execute("DROP FUNCTION versions_unveraenderlich()")
    op.execute("DELETE FROM versions")
    op.execute("DELETE FROM packages")
    op.drop_constraint(op.f("uq_versions_storage_key"), "versions", type_="unique")
    op.drop_column("versions", "statement")
    op.drop_column("versions", "manifest")
    op.drop_column("versions", "storage_key")
    op.drop_column("versions", "archive_bytes")
    op.drop_constraint(op.f("uq_packages_namespace_id"), "packages", type_="unique")
    op.drop_index(op.f("ix_packages_namespace_id"), table_name="packages")
    op.drop_constraint(op.f("fk_packages_namespace_id_namespaces"), "packages", type_="foreignkey")
    op.drop_column("packages", "data_key_enc")
    op.drop_column("packages", "namespace_id")
    op.add_column("packages", sa.Column("namespace", sa.String(length=40), nullable=False))
    op.create_unique_constraint(op.f("uq_packages_namespace"), "packages", ["namespace", "name"])
