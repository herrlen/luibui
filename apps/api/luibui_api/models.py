"""Database schema (S0-8).

Rules that every table follows:
- Primary keys are UUIDs, never sequential.
- Every table holding user data has ``owner_id``; access checks always filter by it (S2-6).
- Passwords are stored only as Argon2 hashes. Session and API tokens are 256-bit random values
  and stored as SHA-256 hashes (decided 2026-09-26: Argon2 on every request would make the API
  easy to overload). Project files only encrypted (S2-7).
- The audit log stores metadata only, never file contents or findings.
"""

import uuid
from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    MetaData,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)
    type_annotation_map: ClassVar[dict[Any, Any]] = {
        dict[str, Any]: JSONB,
        datetime: DateTime(timezone=True),
    }


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))


def _created() -> Mapped[datetime]:
    return mapped_column(server_default=func.now())


def _owner(nullable: bool = False) -> Mapped[Any]:
    return mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=nullable, index=True)


def _enum(name: str, *values: str) -> Enum:
    return Enum(*values, name=name, native_enum=True, validate_strings=True)


PROJECT_TYP = _enum("project_typ", "skill", "mcp-server", "plugin", "tool", "einzeldatei")
QUELLE = _enum("quelle", "datei", "auswahl", "text", "zip", "git")
SCAN_ART = _enum("scan_art", "schnell", "intensiv", "lokal")
PRUEFUMFANG = _enum("pruefumfang", "paket", "auswahl", "einzeldatei")
SCAN_STATUS = _enum("scan_status", "wartend", "laeuft", "fertig", "fehlgeschlagen")
AMPEL_SICHERHEIT = _enum("ampel_sicherheit", "gruen", "gelb", "rot", "gesperrt")
AMPEL_DSGVO = _enum("ampel_dsgvo", "gruen", "gelb", "rot", "nicht_bewertet")
FREIGABE = _enum("freigabe", "freigegeben", "pruefung_noetig", "blockiert")
EBENE = _enum("ebene", "A", "B", "C", "D", "E", "F", "G", "H")
SCHWERE = _enum("schwere", "K", "H", "M", "N", "I")
ACHSE = _enum("achse", "sicherheit", "dsgvo")
NACHWEISGRAD = _enum(
    "nachweisgrad",
    "statisch_erkannt",
    "per_llm_bewertet",
    "in_sandbox_beobachtet",
    "im_test_beobachtet",
    "selbstauskunft",
)
BEFUND_STATUS = _enum("befund_status", "offen", "behoben", "akzeptiert", "bestritten")
JOB_STATUS = _enum("job_status", "queued", "running", "done", "failed")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(320))
    password_hash: Mapped[str] = mapped_column(Text)
    totp_secret_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    """Encrypted with MASTER_KEY, bound to the user ID. Pending until ``totp_confirmed_at``."""
    totp_confirmed_at: Mapped[datetime | None]
    is_admin: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    email_verified_at: Mapped[datetime | None]
    last_login_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = _created()

    __table_args__ = (Index("uq_users_email_lower", func.lower(email), unique=True),)


class UserSession(Base):
    """Login session behind the host-only cookie on app.luibui.com. Only the hash is stored."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID] = _owner()
    secret_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = _created()
    last_seen_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime]


class Token(Base):
    """API token. Only the SHA-256 hash is stored; ``prefix`` lets the owner recognise it."""

    __tablename__ = "tokens"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID] = _owner()
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    prefix: Mapped[str] = mapped_column(String(16), unique=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String(50)), server_default="{}")
    expires_at: Mapped[datetime]
    last_used_at: Mapped[datetime | None]
    revoked_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = _created()


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID] = _owner()
    name: Mapped[str] = mapped_column(String(200))
    typ: Mapped[str] = mapped_column(PROJECT_TYP)
    quelle: Mapped[str] = mapped_column(QUELLE)
    git_url: Mapped[str | None] = mapped_column(String(500))
    delete_files_after_scan: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    is_einzelpruefungen: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    data_key_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    """Per-project data key, encrypted with MASTER_KEY (S2-7)."""
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("owner_id", "name"),)


class ProjectVersion(Base):
    __tablename__ = "project_versions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID] = _owner()
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    number: Mapped[int] = mapped_column(Integer)
    label: Mapped[str | None] = mapped_column(String(100))
    commit_sha: Mapped[str | None] = mapped_column(String(64))
    inventory_sha256: Mapped[str | None] = mapped_column(String(64))
    file_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    bytes: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
    files_deleted_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = _created()

    __table_args__ = (UniqueConstraint("project_id", "number"),)


class Namespace(Base):
    """The ``org`` in ``org/paket`` (S4-1). An account may own several; names are unique
    regardless of case and checked against look-alikes (``register.verwechslung``)."""

    __tablename__ = "namespaces"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID] = _owner()
    name: Mapped[str] = mapped_column(String(39))
    created_at: Mapped[datetime] = _created()

    __table_args__ = (
        Index("uq_namespaces_name_lower", func.lower(name), unique=True),
        CheckConstraint("name ~ '^[a-z0-9](?:[a-z0-9]|-(?=[a-z0-9])){1,38}$'", name="name"),
    )


class StoredFile(Base):
    """One encrypted file of a project version. ``storage_key`` names the blob on the volume."""

    __tablename__ = "stored_files"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID] = _owner()
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project_versions.id", ondelete="CASCADE"), index=True
    )
    path: Mapped[str] = mapped_column(String(1024))
    size: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = _created()

    __table_args__ = (UniqueConstraint("version_id", "path"),)


class Scan(Base):
    """A scan. Quick scans have no owner and expire after 7 days."""

    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID | None] = _owner(nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("project_versions.id", ondelete="SET NULL"), index=True
    )
    scan_art: Mapped[str] = mapped_column(SCAN_ART)
    pruefumfang: Mapped[str] = mapped_column(PRUEFUMFANG)
    status: Mapped[str] = mapped_column(SCAN_STATUS, server_default="wartend")
    ampel_sicherheit: Mapped[str | None] = mapped_column(AMPEL_SICHERHEIT)
    ampel_dsgvo: Mapped[str | None] = mapped_column(AMPEL_DSGVO)
    ampel_gesamt: Mapped[str | None] = mapped_column(AMPEL_SICHERHEIT)
    note: Mapped[int | None] = mapped_column(SmallInteger)
    freigabe: Mapped[str | None] = mapped_column(FREIGABE)
    report: Mapped[dict[str, Any] | None]
    fortschritt: Mapped[dict[str, Any] | None]
    """While running: {"schritt", "von", "titel"} from the worker (S2-9); cleared at the end."""
    engine_version: Mapped[str | None] = mapped_column(String(50))
    share_token_hash: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = _created()
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    expires_at: Mapped[datetime | None]

    __table_args__ = (
        CheckConstraint("note IS NULL OR note BETWEEN 0 AND 100", name="note_range"),
        CheckConstraint(
            "scan_art = 'schnell' OR owner_id IS NOT NULL", name="owner_unless_quickscan"
        ),
        CheckConstraint(
            "scan_art <> 'schnell' OR expires_at IS NOT NULL", name="quickscan_expires"
        ),
    )


class FindingRow(Base):
    """A finding of one scan; columns mirror spec/finding.schema.json."""

    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID | None] = _owner(nullable=True)
    scan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"), index=True
    )
    rule_id: Mapped[str] = mapped_column(String(200))
    ebene: Mapped[str] = mapped_column(EBENE)
    schwere: Mapped[str] = mapped_column(SCHWERE)
    achse: Mapped[str] = mapped_column(ACHSE)
    titel: Mapped[str] = mapped_column(String(200))
    erklaerung: Mapped[str] = mapped_column(Text)
    datei: Mapped[str | None] = mapped_column(String(1024))
    zeile: Mapped[int | None] = mapped_column(Integer)
    beleg: Mapped[str | None] = mapped_column(Text)
    nachweisgrad: Mapped[str] = mapped_column(NACHWEISGRAD)
    normbezug: Mapped[list[str]] = mapped_column(ARRAY(String(100)), server_default="{}")
    fix: Mapped[str] = mapped_column(Text)
    fix_prompt: Mapped[str] = mapped_column(Text)
    analyzer: Mapped[str | None] = mapped_column(String(100))
    fingerprint: Mapped[str | None] = mapped_column(String(64), index=True)
    hochgestuft_von: Mapped[str | None] = mapped_column(SCHWERE)

    __table_args__ = (CheckConstraint("zeile IS NULL OR zeile >= 1", name="zeile_positive"),)


class FindingStatus(Base):
    """Status of a finding across scans of a project, keyed by fingerprint (S3-7)."""

    __tablename__ = "finding_status"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID] = _owner()
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(BEFUND_STATUS, server_default="offen")
    begruendung: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    moderation: Mapped[str | None] = mapped_column(String(20))
    """Decision on a dispute: ``bestritten`` (stays "disputed by the author") or ``fehlalarm``
    ("false alarm, rule adjusted"). Cleared whenever the owner changes the status."""
    moderation_notiz: Mapped[str | None] = mapped_column(Text)
    moderiert_von: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    moderiert_at: Mapped[datetime | None]

    __table_args__ = (
        UniqueConstraint("project_id", "fingerprint"),
        CheckConstraint(
            "status NOT IN ('akzeptiert', 'bestritten') OR begruendung IS NOT NULL",
            name="begruendung_required",
        ),
        CheckConstraint(
            "moderation IS NULL OR moderation IN ('bestritten', 'fehlalarm')",
            name="moderation_wert",
        ),
        Index(
            "ix_finding_status_bestritten",
            "updated_at",
            postgresql_where=text("status = 'bestritten'"),
        ),
    )


class Job(Base):
    """Work queue, consumed with SELECT … FOR UPDATE SKIP LOCKED (S0-9)."""

    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID | None] = _owner(nullable=True)
    kind: Mapped[str] = mapped_column(String(50))
    scan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"), index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    status: Mapped[str] = mapped_column(JOB_STATUS, server_default="queued")
    attempts: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    max_attempts: Mapped[int] = mapped_column(SmallInteger, server_default=text("1"))
    timeout_seconds: Mapped[int] = mapped_column(Integer, server_default=text("300"))
    run_after: Mapped[datetime] = mapped_column(server_default=func.now())
    locked_at: Mapped[datetime | None]
    locked_by: Mapped[str | None] = mapped_column(String(100))
    error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = _created()
    finished_at: Mapped[datetime | None]

    __table_args__ = (
        Index(
            "ix_jobs_queue",
            "run_after",
            postgresql_where=text("status = 'queued'"),
        ),
    )


class Package(Base):
    """Registry package ``namespace/name`` (S4-2). A namespace with packages cannot be deleted."""

    __tablename__ = "packages"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID] = _owner()
    namespace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("namespaces.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(50))
    source_project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL")
    )
    data_key_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    """Encrypts the archives of this package on the volume (CLAUDE.md rule 10)."""
    created_at: Mapped[datetime] = _created()

    __table_args__ = (UniqueConstraint("namespace_id", "name"),)


class PackageVersion(Base):
    """Immutable, signed package version (S4-2). A database trigger refuses any change except
    withdrawing it (``yanked_at``)."""

    __tablename__ = "versions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID] = _owner()
    package_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("packages.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[str] = mapped_column(String(100))
    scan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scans.id", ondelete="RESTRICT"))
    archive_sha256: Mapped[str] = mapped_column(String(64))
    archive_bytes: Mapped[int] = mapped_column(BigInteger)
    storage_key: Mapped[str] = mapped_column(String(100), unique=True)
    manifest: Mapped[dict[str, Any]]
    aenderungen: Mapped[list[dict[str, str]]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb")
    )
    """New rights, endpoints and data compared with ``vorversion`` (S4-6, H01); signed too."""
    vorversion: Mapped[str | None] = mapped_column(String(100))
    statement: Mapped[str] = mapped_column(Text)
    """The canonical JSON that was signed, byte for byte."""
    signature: Mapped[bytes | None] = mapped_column(LargeBinary)
    published_at: Mapped[datetime] = _created()
    yanked_at: Mapped[datetime | None]

    __table_args__ = (UniqueConstraint("package_id", "version"),)


class AuditLog(Base):
    """Metadata only: who did what to which resource. No contents, no findings, no secrets."""

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = _uuid_pk()
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(100))
    resource_type: Mapped[str | None] = mapped_column(String(50))
    resource_id: Mapped[uuid.UUID | None]
    meta: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = _created()

    __table_args__ = (Index("ix_audit_log_created_at", "created_at"),)


class EmailToken(Base):
    """One-time link by e-mail: confirm the address, reset the password or change the address.
    Only the SHA-256 hash is stored, and a link only works for its own ``zweck``."""

    __tablename__ = "email_tokens"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID] = _owner()
    secret_hash: Mapped[str] = mapped_column(String(64), unique=True)
    zweck: Mapped[str] = mapped_column(String(20), server_default="bestaetigung")
    neue_email: Mapped[str | None] = mapped_column(String(320))
    """Only for ``zweck='email'``: the address that becomes the account's after the click."""
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = _created()

    __table_args__ = (
        CheckConstraint("zweck IN ('bestaetigung', 'passwort', 'email')", name="zweck"),
        CheckConstraint("(zweck = 'email') = (neue_email IS NOT NULL)", name="neue_email"),
    )


ZAHLUNG_STATUS = _enum("zahlung_status", "angelegt", "bezahlt", "abgebrochen")


class Payment(Base):
    """A credit purchase through PayPal. Kept 10 years (§ 147 AO); the owner link is dropped when
    the account is deleted, the receipt data stay."""

    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    order_id: Mapped[str] = mapped_column(String(64), unique=True)
    capture_id: Mapped[str | None] = mapped_column(String(64))
    paket: Mapped[str] = mapped_column(String(20))
    pruefungen: Mapped[int] = mapped_column(Integer)
    betrag_cent: Mapped[int] = mapped_column(Integer)
    waehrung: Mapped[str] = mapped_column(String(3), server_default="EUR")
    status: Mapped[str] = mapped_column(ZAHLUNG_STATUS, server_default="angelegt")
    belegnummer: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    kaeufer_email: Mapped[str | None] = mapped_column(String(320))
    """The account e-mail at the time of purchase, for the receipt."""
    created_at: Mapped[datetime] = _created()
    bezahlt_am: Mapped[datetime | None]


class CreditEntry(Base):
    """Credit ledger: the balance is the sum of ``delta``. +3 start credit once the e-mail is
    confirmed, +n per purchase, -1 per check, +1 back when a check fails on our side."""

    __tablename__ = "credit_entries"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID] = _owner()
    delta: Mapped[int] = mapped_column(Integer)
    grund: Mapped[str] = mapped_column(String(20))
    scan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scans.id", ondelete="SET NULL"), index=True
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = _created()

    __table_args__ = (
        CheckConstraint("grund IN ('start', 'kauf', 'pruefung', 'erstattung')", name="grund"),
        Index(
            "uq_credit_entries_start",
            "owner_id",
            unique=True,
            postgresql_where=text("grund = 'start'"),
        ),
        Index(
            "uq_credit_entries_erstattung",
            "scan_id",
            unique=True,
            postgresql_where=text("grund = 'erstattung'"),
        ),
    )
