"""Check on push (S5-8): a webhook per Git project, for GitHub, Codeberg/Forgejo/Gitea and GitLab.

The webhook endpoint has no login; the signature is the permission (CLAUDE.md rule 11). Each
project has its own secret, stored encrypted with MASTER_KEY because the check needs it in clear.
Anything that does not verify (unknown project, no webhook, wrong signature) answers 404 like a
missing resource. A verified push to the default branch, or a tag, of the project's own
repository starts an ordinary Git check after the answer has gone out (GitHub waits 10 s at most),
at most one per minute and project, paid like a manual check.
"""

import contextlib
import hashlib
import hmac
import json
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from luibui_api import guthaben
from luibui_api.audit import audit
from luibui_api.auth import AnnahmeOffen, CurrentCaller, DbSession, SessionCaller, get_owned
from luibui_api.db import _sessionmaker
from luibui_api.errors import fehler
from luibui_api.models import Project, User
from luibui_api.settings import get_settings
from luibui_api.storage import master_key
from luibui_api.storage.crypto import DecryptionError, unwrap_key, wrap_key
from luibui_api.uploads import Upload, create_scan
from luibui_scan.intake.safe_git import canonical_url
from luibui_scan.scan import Eingabe

log = logging.getLogger(__name__)
router = APIRouter(tags=["webhooks"])

MAX_NUTZLAST = 5 * 1024 * 1024
ABSTAND = timedelta(minutes=1)
NULL_COMMIT = "0" * 40


def _kontext(project_id: uuid.UUID) -> str:
    return f"webhook:{project_id}"


def _geheimnis(p: Project) -> str | None:
    if p.webhook_secret_enc is None:
        return None
    try:
        return unwrap_key(master_key(), p.webhook_secret_enc, _kontext(p.id)).decode()
    except DecryptionError:
        return None


def signatur_ok(headers: dict[str, str], body: bytes, geheimnis: str) -> bool:
    """GitHub and Forgejo/Gitea sign the body with HMAC-SHA256; GitLab sends the secret itself."""
    erwartet = hmac.new(geheimnis.encode(), body, hashlib.sha256).hexdigest()
    gh = headers.get("x-hub-signature-256", "")
    if gh:
        return gh.startswith("sha256=") and hmac.compare_digest(gh[7:], erwartet)
    gitea = headers.get("x-forgejo-signature") or headers.get("x-gitea-signature") or ""
    if gitea:
        return hmac.compare_digest(gitea, erwartet)
    gitlab = headers.get("x-gitlab-token", "")
    if gitlab:
        return hmac.compare_digest(gitlab.encode(), geheimnis.encode())
    return False


def _ereignis(headers: dict[str, str]) -> str:
    for h in ("x-github-event", "x-forgejo-event", "x-gitea-event", "x-gitlab-event"):
        if headers.get(h):
            return headers[h].lower()
    return ""


def _repos_und_branch(daten: dict[str, Any]) -> tuple[set[str], str]:
    """Canonical repository URLs named in the payload, and the default branch."""
    urls: set[str] = set()
    default = ""
    for schluessel, felder in (
        ("repository", ("clone_url", "html_url", "git_http_url", "url")),
        ("project", ("git_http_url", "http_url", "web_url")),
    ):
        teil = daten.get(schluessel)
        if not isinstance(teil, dict):
            continue
        default = default or str(teil.get("default_branch") or "")
        for f in felder:
            wert = teil.get(f)
            if isinstance(wert, str):
                with contextlib.suppress(ValueError):  # not a URL we would ever clone
                    urls.add(canonical_url(wert))
    return urls, default


def ausloesend(daten: dict[str, Any], git_url: str) -> str | None:
    """Why this push does not trigger a check, or None if it does."""
    urls, default = _repos_und_branch(daten)
    if git_url not in urls:
        return "anderes Repository"
    if daten.get("deleted") is True or daten.get("after") == NULL_COMMIT:
        return "gelöschter Branch oder Tag"
    ref = str(daten.get("ref") or "")
    if ref.startswith("refs/tags/") or (default and ref == f"refs/heads/{default}"):
        return None
    return "nicht der Standard-Branch"


def _pruefen(project_id: uuid.UUID) -> None:
    """After the answer: book a credit and start an ordinary Git check of the project."""
    with _sessionmaker()() as db:
        project = db.get(Project, project_id)
        user = db.get(User, project.owner_id) if project else None
        if project is None or user is None or not project.git_url:
            return
        try:
            buchung = guthaben.pruefung_abbuchen(db, user)
            scan = create_scan(
                db,
                Upload(art=Eingabe.GIT, git_url=project.git_url),
                project=project,
                name=project.name,
            )
            scan.ausloeser = "webhook"
            if buchung is not None:
                buchung.scan_id = scan.id
            audit(db, user.id, "webhook.pruefung", "scan", scan.id)
            db.commit()
        except HTTPException as exc:
            db.rollback()
            log.info("webhook check for project %s not started: %s", project_id, exc.status_code)
        except Exception:
            db.rollback()
            log.exception("webhook check for project %s failed", project_id)


@router.post("/api/v1/webhooks/{project_id}", dependencies=[AnnahmeOffen])
async def webhook(
    project_id: uuid.UUID, request: Request, db: DbSession, hintergrund: BackgroundTasks
) -> dict[str, str]:
    nicht_gefunden = HTTPException(status.HTTP_404_NOT_FOUND, "Nicht gefunden")
    laenge = request.headers.get("content-length")
    if laenge is None or not laenge.isdigit() or int(laenge) > MAX_NUTZLAST:
        raise nicht_gefunden
    body = await request.body()
    project = db.get(Project, project_id)
    geheimnis = _geheimnis(project) if project else None
    headers = {k.lower(): v for k, v in request.headers.items()}
    if project is None or geheimnis is None or not signatur_ok(headers, body, geheimnis):
        raise nicht_gefunden
    ereignis = _ereignis(headers)
    if ereignis == "ping":
        return {"status": "ok"}
    if ereignis not in ("push", "push hook", "tag push hook", "create"):
        return {"status": "ignoriert", "grund": "kein Push"}
    try:
        daten = json.loads(body)
    except ValueError:
        return {"status": "ignoriert", "grund": "Nutzlast nicht lesbar"}
    if not isinstance(daten, dict) or not project.git_url:
        return {"status": "ignoriert", "grund": "Nutzlast nicht lesbar"}
    grund = ausloesend(daten, project.git_url)
    if grund:
        return {"status": "ignoriert", "grund": grund}
    jetzt = datetime.now(UTC)
    if project.webhook_letzter_lauf and jetzt - project.webhook_letzter_lauf < ABSTAND:
        return {"status": "ignoriert", "grund": "höchstens eine Prüfung pro Minute"}
    project.webhook_letzter_lauf = jetzt
    db.commit()
    hintergrund.add_task(_pruefen, project.id)
    return {"status": "geplant"}


# --- setting it up in the developer area -------------------------------------------------------


class WebhookInfo(BaseModel):
    aktiv: bool
    url: str
    letzter_lauf: datetime | None
    geheimnis: str | None = None
    """Only in the answer that creates it."""


def _url(project_id: uuid.UUID) -> str:
    return f"{get_settings().api_origin}/api/v1/webhooks/{project_id}"


def _git_projekt(db: Session, project_id: uuid.UUID, caller: Any) -> Project:
    p = get_owned(db, Project, project_id, caller)
    if p.quelle != "git" or not p.git_url:
        raise fehler(status.HTTP_409_CONFLICT, "kein_git", "Webhooks gibt es nur für Git-Projekte.")
    return p


@router.get("/api/v1/projects/{project_id}/webhook")
def webhook_info(project_id: uuid.UUID, caller: CurrentCaller, db: DbSession) -> WebhookInfo:
    p = get_owned(db, Project, project_id, caller)
    return WebhookInfo(
        aktiv=p.webhook_secret_enc is not None, url=_url(p.id), letzter_lauf=p.webhook_letzter_lauf
    )


@router.post("/api/v1/projects/{project_id}/webhook")
def webhook_einrichten(project_id: uuid.UUID, caller: SessionCaller, db: DbSession) -> WebhookInfo:
    """Creates a new secret; an existing one stops working at once."""
    p = _git_projekt(db, project_id, caller)
    geheimnis = secrets.token_urlsafe(32)
    p.webhook_secret_enc = wrap_key(master_key(), geheimnis.encode(), _kontext(p.id))
    audit(db, caller.user.id, "webhook.eingerichtet", "project", p.id)
    db.commit()
    return WebhookInfo(
        aktiv=True, url=_url(p.id), letzter_lauf=p.webhook_letzter_lauf, geheimnis=geheimnis
    )


@router.delete("/api/v1/projects/{project_id}/webhook", status_code=status.HTTP_204_NO_CONTENT)
def webhook_abschalten(project_id: uuid.UUID, caller: SessionCaller, db: DbSession) -> None:
    p = get_owned(db, Project, project_id, caller)
    p.webhook_secret_enc = None
    audit(db, caller.user.id, "webhook.abgeschaltet", "project", p.id)
    db.commit()
