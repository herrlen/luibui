"""Data export and account deletion (S2-10; DSGVO Art. 15, 17 and 20).

Both need a browser session (never an API token), the password and, with two-factor login, the
code. The export is a ZIP with everything stored about the account: account data, sessions and
tokens (no secrets or hashes), credit, purchases, the own audit log, projects with their reports
and the stored files, decrypted. Deleting removes the account with all projects, reports and the
encrypted files on the volume. Receipts stay for ten years (§ 147 AO), without the account link.
"""

import json
import os
import re
import tempfile
import uuid
import zipfile
from datetime import UTC, date, datetime
from typing import Any

from fastapi import APIRouter, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from starlette.background import BackgroundTask

from luibui_api.audit import audit
from luibui_api.auth import DbSession, SessionCaller, cookie_name
from luibui_api.errors import fehler
from luibui_api.models import (
    AuditLog,
    CreditEntry,
    FindingStatus,
    Payment,
    Project,
    ProjectVersion,
    Scan,
    StoredFile,
    Token,
    User,
    UserSession,
)
from luibui_api.routes.auth import login_limiter
from luibui_api.security import PASSWORD_MAX, decrypt_totp_secret, verify_password, verify_totp
from luibui_api.settings import get_settings
from luibui_api.storage import blob_store, project_data_key

router = APIRouter(prefix="/api/v1/konto", tags=["konto"])

LOESCHWORT = "LÖSCHEN"


class Nachweis(BaseModel):
    passwort: str = Field(max_length=PASSWORD_MAX)
    code: str | None = Field(default=None, max_length=10)


class Loeschen(Nachweis):
    bestaetigung: str = Field(max_length=20)


def _pruefen(user: User, body: Nachweis) -> None:
    """Password and, if active, the two-factor code; failures count like failed logins."""
    limiter = login_limiter()
    key = f"konto:{user.id}"
    if limiter.blocked(key):
        raise fehler(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "zu_viele_versuche",
            "Zu viele Versuche, bitte später",
        )
    ok = verify_password(user.password_hash, body.passwort)
    if ok and user.totp_confirmed_at is not None:
        secret = decrypt_totp_secret(user.id, user.totp_secret_enc or b"")
        ok = secret is not None and bool(body.code) and verify_totp(secret, body.code or "")
    if not ok:
        limiter.hit(key)
        raise fehler(status.HTTP_400_BAD_REQUEST, "nachweis_falsch", "Passwort oder Code falsch")
    limiter.reset(key)


# --- export ------------------------------------------------------------------------------------


def _iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat(timespec="seconds") if value else None


def _name(text: str) -> str:
    """A safe folder name inside the ZIP."""
    return re.sub(r"[^\w.\- ]", "_", text).strip(". ")[:80] or "projekt"


def _json(zf: zipfile.ZipFile, name: str, data: Any) -> None:
    zf.writestr(name, json.dumps(data, ensure_ascii=False, indent=2, default=str))


def _konto(db: DbSession, user: User) -> dict[str, Any]:
    uid = user.id
    return {
        "konto": {
            "id": str(uid),
            "email": user.email,
            "registriert_am": _iso(user.created_at),
            "email_bestaetigt_am": _iso(user.email_verified_at),
            "letzte_anmeldung": _iso(user.last_login_at),
            "zwei_faktor_aktiv": user.totp_confirmed_at is not None,
        },
        "sitzungen": [
            {"angelegt": _iso(s.created_at), "zuletzt": _iso(s.last_seen_at),
             "gueltig_bis": _iso(s.expires_at)}
            for s in db.scalars(select(UserSession).where(UserSession.owner_id == uid))
        ],
        "api_tokens": [
            {"name": t.name, "anfang": t.prefix, "rechte": t.scopes, "angelegt": _iso(t.created_at),
             "zuletzt_benutzt": _iso(t.last_used_at), "gueltig_bis": _iso(t.expires_at),
             "widerrufen": _iso(t.revoked_at)}
            for t in db.scalars(select(Token).where(Token.owner_id == uid))
        ],
        "guthaben": [
            {"datum": _iso(c.created_at), "aenderung": c.delta, "grund": c.grund}
            for c in db.scalars(select(CreditEntry).where(CreditEntry.owner_id == uid))
        ],
        "kaeufe": [
            {"belegnummer": p.belegnummer, "paket": p.paket, "pruefungen": p.pruefungen,
             "betrag_cent": p.betrag_cent, "waehrung": p.waehrung, "status": p.status,
             "angelegt": _iso(p.created_at), "bezahlt_am": _iso(p.bezahlt_am)}
            for p in db.scalars(select(Payment).where(Payment.owner_id == uid))
        ],
        "protokoll": [
            {"datum": _iso(a.created_at), "aktion": a.action, "art": a.resource_type,
             "id": str(a.resource_id) if a.resource_id else None}
            for a in db.scalars(
                select(AuditLog).where(AuditLog.actor_id == uid).order_by(AuditLog.created_at)
            )
        ],
    }  # fmt: skip


def _scan(s: Scan) -> dict[str, Any]:
    return {
        "id": str(s.id),
        "angelegt": _iso(s.created_at),
        "fertig": _iso(s.finished_at),
        "status": s.status,
        "scan_art": s.scan_art,
        "bericht": s.report,
    }


def _export(db: DbSession, user: User, ziel: str) -> None:
    uid = user.id
    with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as zf:
        _json(zf, "konto.json", _konto(db, user))
        einzeln = db.scalars(
            select(Scan)
            .join(Project, Scan.project_id == Project.id)
            .where(Scan.owner_id == uid, Project.is_einzelpruefungen)
        )
        _json(zf, "einzelpruefungen.json", [_scan(s) for s in einzeln])
        for p in db.scalars(select(Project).where(Project.owner_id == uid)):
            if p.is_einzelpruefungen:
                continue
            ordner = f"projekte/{_name(p.name)}-{str(p.id)[:8]}"
            versionen = list(
                db.scalars(select(ProjectVersion).where(ProjectVersion.project_id == p.id))
            )
            status_liste = db.scalars(select(FindingStatus).where(FindingStatus.project_id == p.id))
            _json(zf, f"{ordner}/projekt.json", {
                "name": p.name, "typ": p.typ, "quelle": p.quelle, "git_url": p.git_url,
                "angelegt": _iso(p.created_at), "nach_pruefung_loeschen": p.delete_files_after_scan,
                "versionen": [{"nummer": v.number, "angelegt": _iso(v.created_at),
                               "dateien": v.file_count, "bytes": v.bytes} for v in versionen],
                "befund_status": [{"fingerprint": f.fingerprint, "status": f.status,
                                   "begruendung": f.begruendung} for f in status_liste],
            })  # fmt: skip
            scans = db.scalars(select(Scan).where(Scan.project_id == p.id))
            _json(zf, f"{ordner}/pruefungen.json", [_scan(s) for s in scans])
            if p.data_key_enc is None:
                continue
            data_key, _ = project_data_key(p.id, p.data_key_enc)
            for v in versionen:
                dateien = db.scalars(select(StoredFile).where(StoredFile.version_id == v.id))
                for f in dateien:
                    with zf.open(f"{ordner}/dateien/v{v.number}/{f.path}", "w") as out:
                        for teil in blob_store().open(f.storage_key, data_key):
                            out.write(teil)


@router.post("/export")
def export(body: Nachweis, caller: SessionCaller, db: DbSession) -> FileResponse:
    user = db.merge(caller.user)
    _pruefen(user, body)
    get_settings().scratch_root.mkdir(parents=True, exist_ok=True)
    fd, ziel = tempfile.mkstemp(prefix="export-", suffix=".zip", dir=get_settings().scratch_root)
    os.close(fd)
    try:
        _export(db, user, ziel)
    except BaseException:
        os.unlink(ziel)
        raise
    audit(db, user.id, "konto.exportiert", "user", user.id)
    db.commit()
    return FileResponse(
        ziel,
        media_type="application/zip",
        filename=f"luibui-export-{date.today().isoformat()}.zip",
        background=BackgroundTask(os.unlink, ziel),
    )


# --- delete ------------------------------------------------------------------------------------


@router.post("/loeschen", status_code=status.HTTP_204_NO_CONTENT)
def loeschen(body: Loeschen, response: Response, caller: SessionCaller, db: DbSession) -> None:
    user = db.merge(caller.user)
    _pruefen(user, body)
    if body.bestaetigung.strip() != LOESCHWORT:
        raise fehler(
            status.HTTP_400_BAD_REQUEST, "bestaetigung_fehlt", f"Bitte „{LOESCHWORT}“ eintippen"
        )
    uid: uuid.UUID = user.id
    keys = list(db.scalars(select(StoredFile.storage_key).where(StoredFile.owner_id == uid)))
    db.delete(user)  # the database cascades: projects, versions, scans, findings, tokens …
    audit(db, None, "konto.geloescht", "user", uid)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise fehler(
            status.HTTP_409_CONFLICT,
            "veroeffentlicht",
            "Veröffentlichte Pakete verweisen auf Prüfungen dieses Kontos. "
            "Bitte zuerst zurückziehen.",
        ) from None
    # Only after the commit: a failed commit must not leave records without their files.
    for key in keys:
        blob_store().delete(key)
    response.delete_cookie(cookie_name(), path="/", secure=get_settings().session_cookie_secure)
