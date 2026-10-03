"""Publishing to the register (S4-2) and the public read access that ``luibui install`` needs.

A version comes from one finished check of the owner: a package check (with ``luibui.json``) of
uploaded files, not locked. ``name`` and ``version`` come from the manifest; the namespace must
be one of the owner's. The stored files become a reproducible ZIP (sorted, fixed timestamps),
encrypted on the volume like project files, and luibui signs a canonical statement about it with
its Ed25519 key. Versions never change afterwards (database trigger); they can only be withdrawn.
"""

import base64
import hashlib
import io
import json
import re
import uuid
import zipfile
from datetime import UTC, datetime
from importlib import resources
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Response, status
from jsonschema import Draft202012Validator
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from luibui_api.audit import audit
from luibui_api.auth import CurrentCaller, DbSession, SessionCaller, get_owned
from luibui_api.diff import aenderungen as diff
from luibui_api.errors import fehler
from luibui_api.models import (
    Namespace,
    Package,
    PackageVersion,
    Project,
    ProjectVersion,
    Scan,
    StoredFile,
)
from luibui_api.register import PAKETNAME
from luibui_api.signatur import SignaturError, kanonisch, oeffentlicher_schluessel, signieren
from luibui_api.storage import blob_store, new_storage_key, project_data_key

router = APIRouter(tags=["register"])

MAX_PAKET = 50 * 1024 * 1024
"""Packages are built in memory; the upload limit for a selection is the same 50 MB."""
_ZIP_ZEIT = (1980, 1, 1, 0, 0, 0)
_LIZENZ = re.compile(r"^[A-Za-z0-9.+\-() ]+$")
_KEINE_LIZENZ = {"unlicensed", "proprietary", "none", "noassertion", "see license"}


def _manifest_validator() -> Draft202012Validator:
    schema = json.loads(
        resources.files("luibui_scan").joinpath("data/luibui.schema.json").read_text("utf-8")
    )
    return Draft202012Validator(schema)


class Veroeffentlichen(BaseModel):
    scan_id: uuid.UUID


class VersionInfo(BaseModel):
    id: uuid.UUID
    paket: str
    version: str
    archiv_sha256: str
    archiv_bytes: int
    veroeffentlicht_am: datetime
    zurueckgezogen_am: datetime | None
    scan_id: uuid.UUID


def _abbruch(code: str, text: str, http: int = status.HTTP_409_CONFLICT) -> HTTPException:
    return fehler(http, code, text)


def _dateien(db: DbSession, scan: Scan) -> tuple[Project, list[tuple[StoredFile, bytes]]]:
    project = db.get(Project, scan.project_id) if scan.project_id else None
    version = db.get(ProjectVersion, scan.version_id) if scan.version_id else None
    if project is None or version is None or project.quelle == "git":
        raise _abbruch(
            "keine_dateien",
            "Veröffentlichen geht aus Prüfungen hochgeladener Dateien; Git-Projekte folgen.",
        )
    if version.files_deleted_at is not None or project.data_key_enc is None:
        raise _abbruch("keine_dateien", "Die Dateien dieser Version wurden gelöscht.")
    if version.bytes > MAX_PAKET:
        raise _abbruch("zu_gross", "Pakete über 50 MB lassen sich nicht veröffentlichen.")
    data_key, _ = project_data_key(project.id, project.data_key_enc)
    rows = db.scalars(
        select(StoredFile)
        .where(StoredFile.version_id == version.id, StoredFile.owner_id == scan.owner_id)
        .order_by(StoredFile.path)
    )
    return project, [(f, b"".join(blob_store().open(f.storage_key, data_key))) for f in rows]


def _zip(dateien: list[tuple[StoredFile, bytes]]) -> bytes:
    """Same files, same bytes: no timestamps, no system attributes, sorted by path."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f, inhalt in sorted(dateien, key=lambda x: x[0].path):
            info = zipfile.ZipInfo(f.path, date_time=_ZIP_ZEIT)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            info.create_system = 3
            zf.writestr(info, inhalt)
    return buf.getvalue()


def _manifest(dateien: list[tuple[StoredFile, bytes]]) -> dict[str, Any]:
    roh = next((inhalt for f, inhalt in dateien if f.path == "luibui.json"), None)
    try:
        manifest = json.loads(roh or b"")
    except ValueError:
        manifest = None
    if not isinstance(manifest, dict) or any(_manifest_validator().iter_errors(manifest)):
        raise _abbruch(
            "manifest_ungueltig",
            "luibui.json fehlt oder entspricht nicht dem Schema (siehe Doku).",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    lizenz = str(manifest["lizenz"]).strip()
    if not _LIZENZ.match(lizenz) or lizenz.lower() in _KEINE_LIZENZ:
        raise _abbruch(
            "lizenz_fehlt",
            "Veröffentlicht werden nur Pakete mit einer SPDX-Lizenz, etwa MIT oder Apache-2.0.",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    return manifest


def _info(p: Package, ns: Namespace, v: PackageVersion) -> VersionInfo:
    return VersionInfo(
        id=v.id,
        paket=f"{ns.name}/{p.name}",
        version=v.version,
        archiv_sha256=v.archive_sha256,
        archiv_bytes=v.archive_bytes,
        veroeffentlicht_am=v.published_at,
        zurueckgezogen_am=v.yanked_at,
        scan_id=v.scan_id,
    )


@router.post("/api/v1/register/veroeffentlichen", status_code=status.HTTP_201_CREATED)
def veroeffentlichen(body: Veroeffentlichen, caller: SessionCaller, db: DbSession) -> VersionInfo:
    scan = get_owned(db, Scan, body.scan_id, caller)
    if scan.status != "fertig" or scan.report is None:
        raise _abbruch("nicht_fertig", "Die Prüfung ist noch nicht fertig.")
    if scan.ampel_gesamt == "gesperrt":
        raise _abbruch("gesperrt", "Gesperrte Pakete lassen sich nicht veröffentlichen.")
    if scan.pruefumfang != "paket":
        raise _abbruch(
            "kein_paket",
            "Veröffentlichen geht nur mit einer Paket-Prüfung, also mit luibui.json im Paket.",
        )
    try:
        oeffentlicher_schluessel()
    except SignaturError:
        raise _abbruch(
            "nicht_eingerichtet",
            "Das Register ist gerade nicht eingerichtet. Bitte später erneut.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from None
    project, dateien = _dateien(db, scan)
    manifest = _manifest(dateien)
    ns_name, paket_name = str(manifest["name"]).split("/", 1)
    version = str(manifest["version"])
    ns = db.scalar(
        select(Namespace).where(Namespace.name == ns_name, Namespace.owner_id == caller.user.id)
    )
    if ns is None:
        raise _abbruch(
            "namespace_fehlt",
            f"Der Namespace „{ns_name[:39]}“ aus luibui.json gehört nicht zu deinem Konto. "
            "Lege ihn im Konto an.",
        )
    if not PAKETNAME.match(paket_name):
        raise _abbruch(
            "name_ungueltig",
            "Der Paketname in luibui.json ist ungültig.",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    paket = db.scalar(
        select(Package).where(Package.namespace_id == ns.id, Package.name == paket_name)
    )
    if paket is None:
        paket = Package(
            owner_id=caller.user.id,
            namespace_id=ns.id,
            name=paket_name,
            source_project_id=project.id,
        )
        db.add(paket)
        db.flush()
    elif db.scalar(
        select(PackageVersion.id).where(
            PackageVersion.package_id == paket.id, PackageVersion.version == version
        )
    ):
        raise _abbruch(
            "version_vorhanden",
            f"Version {version[:40]} gibt es schon. Veröffentlichte Versionen sind unveränderlich; "
            "erhöhe die Version in luibui.json.",
        )
    vorige = db.scalar(
        select(PackageVersion)
        .where(PackageVersion.package_id == paket.id, PackageVersion.yanked_at.is_(None))
        .order_by(PackageVersion.published_at.desc())
        .limit(1)
    )
    neu = diff(vorige.manifest if vorige else None, manifest)
    archiv = _zip(dateien)
    sha = hashlib.sha256(archiv).hexdigest()
    jetzt = datetime.now(UTC)  # exact: versions in the same second must keep their order
    aussage = {
        "schema": "luibui-veroeffentlichung/1",
        "paket": f"{ns.name}/{paket.name}",
        "version": version,
        "archiv_sha256": sha,
        "archiv_bytes": len(archiv),
        "bericht_sha256": hashlib.sha256(kanonisch(scan.report)).hexdigest(),
        "scan_id": str(scan.id),
        "ampel": scan.ampel_gesamt,
        "note": scan.note,
        "veroeffentlicht_am": jetzt.replace(microsecond=0).isoformat(),
        "vorversion": vorige.version if vorige else None,
        "aenderungen": neu,
    }
    data_key, data_key_enc = project_data_key(paket.id, paket.data_key_enc)
    paket.data_key_enc = data_key_enc
    key = new_storage_key()
    blob_store().put(key, io.BytesIO(archiv), data_key)
    v = PackageVersion(
        owner_id=caller.user.id,
        package_id=paket.id,
        version=version,
        scan_id=scan.id,
        archive_sha256=sha,
        archive_bytes=len(archiv),
        storage_key=key,
        manifest=manifest,
        aenderungen=neu,
        vorversion=vorige.version if vorige else None,
        statement=kanonisch(aussage).decode(),
        signature=signieren(aussage),
        published_at=jetzt,
    )
    db.add(v)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        blob_store().delete(key)
        raise _abbruch("version_vorhanden", f"Version {version[:40]} gibt es schon.") from None
    audit(db, caller.user.id, "paket.veroeffentlicht", "version", v.id)
    db.commit()
    return _info(paket, ns, v)


@router.get("/api/v1/register/meine")
def meine(caller: CurrentCaller, db: DbSession) -> list[VersionInfo]:
    rows = db.execute(
        select(Package, Namespace, PackageVersion)
        .join(Namespace, Namespace.id == Package.namespace_id)
        .join(PackageVersion, PackageVersion.package_id == Package.id)
        .where(Package.owner_id == caller.user.id)
        .order_by(Namespace.name, Package.name, PackageVersion.published_at.desc())
    )
    return [_info(p, ns, v) for p, ns, v in rows]


@router.post("/api/v1/register/versionen/{paketversion_id}/zurueckziehen")
def zurueckziehen(paketversion_id: uuid.UUID, caller: SessionCaller, db: DbSession) -> VersionInfo:
    """A withdrawn version stays listed (so nobody else can take the number) but is no longer
    offered for installation."""
    v = get_owned(db, PackageVersion, paketversion_id, caller)
    if v.yanked_at is None:
        v.yanked_at = datetime.now(UTC)
        audit(db, caller.user.id, "paket.zurueckgezogen", "version", v.id)
    paket = db.get(Package, v.package_id)
    ns = db.get(Namespace, paket.namespace_id) if paket else None
    db.commit()
    if paket is None or ns is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nicht gefunden")
    return _info(paket, ns, v)


# --- public: what `luibui install` needs ------------------------------------------------------


class Schluessel(BaseModel):
    algorithmus: str = "ed25519"
    oeffentlicher_schluessel: str


@router.get("/api/v1/register/schluessel")
def schluessel() -> Schluessel:
    try:
        return Schluessel(oeffentlicher_schluessel=oeffentlicher_schluessel())
    except SignaturError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "nicht eingerichtet") from None


class OeffentlicheVersion(BaseModel):
    version: str
    archiv_sha256: str
    archiv_bytes: int
    veroeffentlicht_am: datetime
    zurueckgezogen: bool
    vorversion: str | None
    aenderungen: list[dict[str, str]]
    """New rights, endpoints and data compared with ``vorversion`` (H01)."""
    aussage: str
    """The signed statement, exactly as signed."""
    signatur: str
    """Ed25519 signature of ``aussage``, base64."""
    manifest: dict[str, Any]


class OeffentlichesPaket(BaseModel):
    paket: str
    versionen: list[OeffentlicheVersion]


def _paket(db: DbSession, namespace: str, name: str) -> tuple[Package, Namespace]:
    row = db.execute(
        select(Package, Namespace)
        .join(Namespace, Namespace.id == Package.namespace_id)
        .where(Namespace.name == namespace.lower(), Package.name == name.lower())
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nicht gefunden")
    return row[0], row[1]


class PaketEintrag(BaseModel):
    paket: str
    version: str
    beschreibung: str | None
    typ: str | None
    ziele: list[str]
    rechte: list[str]
    """Rights the manifest declares: netzwerk, dateien, shell, zugangsdaten, drittland."""
    ampel: str | None
    note: int | None
    veroeffentlicht_am: datetime


EWR = frozenset(
    {
        "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR", "HU", "IE",
        "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK", "IS", "LI", "NO",
    }
)  # fmt: skip
RECHTE = ("netzwerk", "dateien", "shell", "zugangsdaten", "drittland")
TYPEN = ("skill", "mcp-server", "plugin", "tool")
ZIELE = ("claude", "chatgpt", "gemini", "mistral", "openwebui", "mcp")
AMPELN = ("gruen", "gelb", "rot")


def _dict(wert: object) -> dict[str, Any]:
    return wert if isinstance(wert, dict) else {}


def rechte_von(manifest: dict[str, Any]) -> list[str]:
    """Same rules as the rights label on the package page (apps/web/lib/rechte.ts)."""
    r = _dict(manifest.get("rechte"))
    dateien = _dict(r.get("dateien"))
    roh = manifest.get("endpunkte")
    endpunkte = [e for e in roh if isinstance(e, dict)] if isinstance(roh, list) else []
    an = {
        "netzwerk": r.get("netzwerk") is True,
        "dateien": bool(dateien.get("lesen") or dateien.get("schreiben")),
        "shell": r.get("shell") is True,
        "zugangsdaten": r.get("zugangsdaten") is True or bool(r.get("umgebungsvariablen")),
        "drittland": any(str(e.get("land", "")).upper() not in EWR for e in endpunkte),
    }
    return [k for k in RECHTE if an[k]]


@router.get("/api/v1/register/pakete")
def pakete(
    db: DbSession,
    q: Annotated[str, Query(max_length=100)] = "",
    typ: str | None = None,
    ziel: str | None = None,
    ampel: str | None = None,
    ohne: Annotated[list[str] | None, Query()] = None,
) -> list[PaketEintrag]:
    """Packages with their newest version that is not withdrawn, newest first, at most 200.
    ``q`` searches name and description; ``ohne`` excludes declared rights (S4-4)."""
    suche = q.strip().casefold()
    rows = db.execute(
        select(Package, Namespace, PackageVersion, Scan)
        .join(Namespace, Namespace.id == Package.namespace_id)
        .join(PackageVersion, PackageVersion.package_id == Package.id)
        .join(Scan, Scan.id == PackageVersion.scan_id)
        .where(PackageVersion.yanked_at.is_(None))
        .order_by(PackageVersion.published_at.desc())
    )
    gesehen: set[uuid.UUID] = set()
    eintraege = []
    for p, ns, v, scan in rows:
        if p.id in gesehen:
            continue
        gesehen.add(p.id)
        m = v.manifest
        name = f"{ns.name}/{p.name}"
        beschreibung = str(m.get("beschreibung"))[:300] if m.get("beschreibung") else None
        ziele = (
            [z for z in (m.get("ziele") or []) if z in ZIELE]
            if isinstance(m.get("ziele"), list)
            else []
        )
        rechte = rechte_von(m)
        if suche and suche not in name and suche not in (beschreibung or "").casefold():
            continue
        if typ and m.get("typ") != typ:
            continue
        if ziel and ziel not in ziele:
            continue
        if ampel and scan.ampel_gesamt != ampel:
            continue
        if any(o in rechte for o in ohne or []):
            continue
        eintraege.append(
            PaketEintrag(
                paket=name,
                version=v.version,
                beschreibung=beschreibung,
                typ=str(m.get("typ")) if m.get("typ") else None,
                ziele=ziele,
                rechte=rechte,
                ampel=scan.ampel_gesamt,
                note=scan.note,
                veroeffentlicht_am=v.published_at,
            )
        )
        if len(eintraege) >= 200:
            break
    return eintraege


@router.get("/api/v1/register/pakete/{namespace}/{name}")
def paket(namespace: str, name: str, db: DbSession) -> OeffentlichesPaket:
    p, ns = _paket(db, namespace, name)
    versionen = db.scalars(
        select(PackageVersion)
        .where(PackageVersion.package_id == p.id)
        .order_by(PackageVersion.published_at.desc())
    )
    return OeffentlichesPaket(
        paket=f"{ns.name}/{p.name}",
        versionen=[
            OeffentlicheVersion(
                version=v.version,
                archiv_sha256=v.archive_sha256,
                archiv_bytes=v.archive_bytes,
                veroeffentlicht_am=v.published_at,
                zurueckgezogen=v.yanked_at is not None,
                vorversion=v.vorversion,
                aenderungen=v.aenderungen,
                aussage=v.statement,
                signatur=base64.b64encode(v.signature or b"").decode(),
                manifest=v.manifest,
            )
            for v in versionen
        ],
    )


class VersionKurz(BaseModel):
    version: str
    veroeffentlicht_am: datetime
    zurueckgezogen: bool
    aenderungen: list[dict[str, str]]


class PaketDetail(BaseModel):
    """One version for the public package page (S4-3)."""

    paket: str
    version: str
    veroeffentlicht_am: datetime
    zurueckgezogen: bool
    manifest: dict[str, Any]
    vorversion: str | None
    aenderungen: list[dict[str, str]]
    bericht: dict[str, Any] | None
    """The report of the check this version was published from, as it was then."""
    readme: str | None
    """README (or SKILL.md) from the archive as plain text, at most 64 KB; shown as text only."""
    readme_datei: str | None
    archiv_sha256: str
    archiv_bytes: int
    aussage: str
    signatur: str
    versionen: list[VersionKurz]


MAX_README = 64 * 1024
_README = ("readme.md", "readme", "readme.txt", "readme.rst", "skill.md")


def _readme(archiv: bytes) -> tuple[str | None, str | None]:
    with zipfile.ZipFile(io.BytesIO(archiv)) as zf:
        namen = {n.lower(): n for n in zf.namelist() if "/" not in n}
        for kandidat in _README:
            if kandidat in namen:
                roh = zf.read(namen[kandidat])[:MAX_README]
                try:
                    return roh.decode("utf-8"), namen[kandidat]
                except UnicodeDecodeError:
                    return None, namen[kandidat]
    return None, None


@router.get("/api/v1/register/pakete/{namespace}/{name}/{version}")
def paket_version(namespace: str, name: str, version: str, db: DbSession) -> PaketDetail:
    """``version`` may be ``neueste``: the newest version that is not withdrawn."""
    p, ns = _paket(db, namespace, name)
    alle = list(
        db.scalars(
            select(PackageVersion)
            .where(PackageVersion.package_id == p.id)
            .order_by(PackageVersion.published_at.desc())
        )
    )
    if version == "neueste":
        v = next((x for x in alle if x.yanked_at is None), alle[0] if alle else None)
    else:
        v = next((x for x in alle if x.version == version), None)
    if v is None or p.data_key_enc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nicht gefunden")
    scan = db.get(Scan, v.scan_id)
    data_key, _ = project_data_key(p.id, p.data_key_enc)
    readme, readme_datei = _readme(b"".join(blob_store().open(v.storage_key, data_key)))
    return PaketDetail(
        paket=f"{ns.name}/{p.name}",
        version=v.version,
        veroeffentlicht_am=v.published_at,
        zurueckgezogen=v.yanked_at is not None,
        manifest=v.manifest,
        vorversion=v.vorversion,
        aenderungen=v.aenderungen,
        bericht=scan.report if scan else None,
        readme=readme,
        readme_datei=readme_datei,
        archiv_sha256=v.archive_sha256,
        archiv_bytes=v.archive_bytes,
        aussage=v.statement,
        signatur=base64.b64encode(v.signature or b"").decode(),
        versionen=[
            VersionKurz(
                version=x.version,
                veroeffentlicht_am=x.published_at,
                zurueckgezogen=x.yanked_at is not None,
                aenderungen=x.aenderungen,
            )
            for x in alle
        ],
    )


@router.get(
    "/api/v1/register/pakete/{namespace}/{name}/{version}/archiv.zip",
    response_class=Response,
    responses={200: {"content": {"application/octet-stream": {}}}},
)
def archiv(namespace: str, name: str, version: str, db: DbSession) -> Response:
    p, ns = _paket(db, namespace, name)
    v = db.scalar(
        select(PackageVersion).where(
            PackageVersion.package_id == p.id, PackageVersion.version == version
        )
    )
    if v is None or v.yanked_at is not None or p.data_key_enc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nicht gefunden")
    data_key, _ = project_data_key(p.id, p.data_key_enc)
    inhalt = b"".join(blob_store().open(v.storage_key, data_key))
    if hashlib.sha256(inhalt).hexdigest() != v.archive_sha256:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Archiv beschädigt")
    datei = f"{ns.name}-{p.name}-{v.version}.zip"
    return Response(
        content=inhalt,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{datei}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
