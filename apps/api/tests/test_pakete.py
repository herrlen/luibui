"""S4-2: publishing a checked package to the register: only the owner's unlocked package checks,
name and version from luibui.json, reproducible archive, Ed25519-signed statement, versions that
never change."""

import base64
import hashlib
import io
import json
import zipfile
from typing import Any

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from .conftest import Api
from .test_scans import project, upload_zip

MARK = b"<!-- LUIBUI-TESTFIXTURE: entschaerft, nicht ausfuehren -->\n"


def manifest(**anders: Any) -> bytes:
    m = {
        "schema_version": "1",
        "name": "anna-tools/wetter",
        "version": "1.0.0",
        "typ": "skill",
        "beschreibung": "Zeigt das Wetter.",
        "lizenz": "MIT",
        "rechte": {
            "netzwerk": False,
            "dateien": {"lesen": [], "schreiben": []},
            "shell": False,
            "zugangsdaten": False,
            "umgebungsvariablen": [],
        },
        "endpunkte": [],
    }
    return json.dumps(m | anders).encode()


def fertig(url: str, sid: str, ampel: str = "gelb") -> None:
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE scans SET status = 'fertig', report = CAST(:r AS jsonb), note = 80, "
                "ampel_gesamt = CAST(:a AS ampel_sicherheit) WHERE id = :id"
            ),
            {"r": json.dumps({"befunde": [], "note": 80}), "a": ampel, "id": sid},
        )
    engine.dispose()


def pruefung(c: Any, url: str, files: dict[str, bytes] | None = None, **kw: Any) -> str:
    files = files or {"SKILL.md": MARK + b"# Wetter\n", "luibui.json": manifest()}
    sid: str = upload_zip(c, project(c, name=kw.pop("projekt", "wetter")), files).json()["id"]
    fertig(url, sid, **kw)
    return sid


@pytest.fixture
def anna(api: Api) -> Any:
    a = api.user("anna@example.org")
    assert a.post("/api/v1/namespaces", json={"name": "anna-tools"}).status_code == 201
    return a


def test_publish_signs_and_serves_the_package(api: Api, anna: Any, _migrated: str) -> None:
    r = anna.post("/api/v1/register/veroeffentlichen", json={"scan_id": pruefung(anna, _migrated)})
    assert r.status_code == 201, r.text
    assert (r.json()["paket"], r.json()["version"]) == ("anna-tools/wetter", "1.0.0")
    oeffentlich = api.client()  # no session: the register is public
    p = oeffentlich.get("/api/v1/register/pakete/anna-tools/wetter").json()
    (v,) = p["versionen"]
    archiv = oeffentlich.get("/api/v1/register/pakete/anna-tools/wetter/1.0.0/archiv.zip")
    assert archiv.headers["content-type"] == "application/octet-stream"
    assert hashlib.sha256(archiv.content).hexdigest() == v["archiv_sha256"]
    with zipfile.ZipFile(io.BytesIO(archiv.content)) as zf:
        assert zf.namelist() == ["SKILL.md", "luibui.json"]
        assert {i.date_time for i in zf.infolist()} == {(1980, 1, 1, 0, 0, 0)}
    schluessel = oeffentlich.get("/api/v1/register/schluessel").json()["oeffentlicher_schluessel"]
    pub = Ed25519PublicKey.from_public_bytes(base64.b64decode(schluessel))
    pub.verify(base64.b64decode(v["signatur"]), v["aussage"].encode())
    aussage = json.loads(v["aussage"])
    assert aussage["archiv_sha256"] == v["archiv_sha256"] and aussage["ampel"] == "gelb"
    with pytest.raises(InvalidSignature):
        pub.verify(base64.b64decode(v["signatur"]), v["aussage"].replace("gelb", "gruen").encode())
    assert [m["version"] for m in anna.get("/api/v1/register/meine").json()] == ["1.0.0"]


def test_the_archive_is_reproducible(api: Api, anna: Any, _migrated: str) -> None:
    files = {"b/x.md": MARK, "a.md": MARK, "luibui.json": manifest()}
    erste = pruefung(anna, _migrated, files)
    zweite = pruefung(anna, _migrated, dict(reversed(files.items())), projekt="nochmal")
    anna.post("/api/v1/register/veroeffentlichen", json={"scan_id": erste})
    r = anna.post("/api/v1/register/veroeffentlichen", json={"scan_id": zweite})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "version_vorhanden"
    sha = anna.get("/api/v1/register/meine").json()[0]["archiv_sha256"]
    with zipfile.ZipFile(io.BytesIO(api.client().get(
        "/api/v1/register/pakete/anna-tools/wetter/1.0.0/archiv.zip").content)) as zf:  # fmt: skip
        assert zf.namelist() == ["a.md", "b/x.md", "luibui.json"]
    assert len(sha) == 64


@pytest.mark.parametrize(
    ("files", "ampel", "code"),
    [
        (None, "gesperrt", "gesperrt"),
        ({"SKILL.md": MARK}, "gelb", "kein_paket"),
        ({"luibui.json": b"{kaputt"}, "gelb", "manifest_ungueltig"),
        ({"luibui.json": manifest(lizenz="UNLICENSED")}, "gelb", "lizenz_fehlt"),
        ({"luibui.json": manifest(name="bert/wetter")}, "gelb", "namespace_fehlt"),
    ],
)
def test_what_cannot_be_published(
    anna: Any, _migrated: str, files: dict[str, bytes] | None, ampel: str, code: str
) -> None:
    sid = pruefung(anna, _migrated, files, ampel=ampel)
    r = anna.post("/api/v1/register/veroeffentlichen", json={"scan_id": sid})
    assert r.status_code in (409, 422) and r.json()["detail"]["code"] == code
    assert anna.get("/api/v1/register/meine").json() == []


def test_unfinished_scans_and_a_missing_key(
    anna: Any, _migrated: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    sid = upload_zip(anna, project(anna), {"luibui.json": manifest()}).json()["id"]
    r = anna.post("/api/v1/register/veroeffentlichen", json={"scan_id": sid})
    assert r.json()["detail"]["code"] == "nicht_fertig"
    fertig(_migrated, sid)
    monkeypatch.setenv("REGISTER_SIGNING_KEY", "")
    from luibui_api.settings import get_settings

    get_settings.cache_clear()
    assert anna.post("/api/v1/register/veroeffentlichen", json={"scan_id": sid}).status_code == 503


def test_versions_are_immutable_but_can_be_withdrawn(api: Api, anna: Any, _migrated: str) -> None:
    v = anna.post(
        "/api/v1/register/veroeffentlichen", json={"scan_id": pruefung(anna, _migrated)}
    ).json()
    engine = create_engine(_migrated)
    with pytest.raises(DBAPIError, match="immutable"), engine.begin() as conn:
        conn.execute(
            text("UPDATE versions SET archive_sha256 = 'x' WHERE id = :id"), {"id": v["id"]}
        )
    engine.dispose()
    r = anna.post(f"/api/v1/register/versionen/{v['id']}/zurueckziehen")
    assert r.status_code == 200 and r.json()["zurueckgezogen_am"] is not None
    oeffentlich = api.client()
    assert oeffentlich.get("/api/v1/register/pakete/anna-tools/wetter").json()["versionen"][0][
        "zurueckgezogen"
    ]
    url = "/api/v1/register/pakete/anna-tools/wetter/1.0.0/archiv.zip"
    assert oeffentlich.get(url).status_code == 404


def test_other_users_and_namespaces_with_packages(api: Api, anna: Any, _migrated: str) -> None:
    sid = pruefung(anna, _migrated)
    b = api.user("bert@example.org")
    assert b.post("/api/v1/register/veroeffentlichen", json={"scan_id": sid}).status_code == 404
    v = anna.post("/api/v1/register/veroeffentlichen", json={"scan_id": sid}).json()
    assert b.post(f"/api/v1/register/versionen/{v['id']}/zurueckziehen").status_code == 404
    assert b.get("/api/v1/register/meine").json() == []
    (ns,) = anna.get("/api/v1/namespaces").json()
    r = anna.delete(f"/api/v1/namespaces/{ns['id']}")
    assert r.status_code == 409 and r.json()["detail"]["code"] == "hat_pakete"
    assert api.client().get("/api/v1/register/pakete/anna-tools/fremd").status_code == 404


def test_same_files_in_any_order_give_the_same_bytes() -> None:
    from types import SimpleNamespace

    from luibui_api.routes.pakete import _zip

    dateien = [(SimpleNamespace(path=p), p.encode() * 50) for p in ("b/x.md", "a.md", "c.json")]
    eins = _zip(dateien)  # type: ignore[arg-type]
    zwei = _zip(list(reversed(dateien)))  # type: ignore[arg-type]
    assert eins == zwei and hashlib.sha256(eins).digest() == hashlib.sha256(zwei).digest()


def test_public_version_page_data(api: Api, anna: Any, _migrated: str) -> None:
    files = {
        "README.md": MARK + b"# Wetter\n<script>alert(1)</script>\n",
        "SKILL.md": MARK,
        "luibui.json": manifest(),
    }
    sid = pruefung(anna, _migrated, files)
    anna.post("/api/v1/register/veroeffentlichen", json={"scan_id": sid})
    oeffentlich = api.client()
    d = oeffentlich.get("/api/v1/register/pakete/anna-tools/wetter/neueste").json()
    assert (d["paket"], d["version"], d["readme_datei"]) == (
        "anna-tools/wetter",
        "1.0.0",
        "README.md",
    )
    assert "<script>" in d["readme"]  # raw text; the page renders it as text
    assert d["bericht"]["note"] == 80 and d["manifest"]["lizenz"] == "MIT"
    assert [v["version"] for v in d["versionen"]] == ["1.0.0"]
    assert oeffentlich.get("/api/v1/register/pakete/anna-tools/wetter/9.9.9").status_code == 404


def test_public_list_shows_the_newest_available_version(
    api: Api, anna: Any, _migrated: str
) -> None:
    assert api.client().get("/api/v1/register/pakete").json() == []
    v = anna.post(
        "/api/v1/register/veroeffentlichen", json={"scan_id": pruefung(anna, _migrated)}
    ).json()
    files = {"SKILL.md": MARK, "luibui.json": manifest(version="1.1.0")}
    anna.post(
        "/api/v1/register/veroeffentlichen",
        json={"scan_id": pruefung(anna, _migrated, files, projekt="zwei")},
    )
    (eintrag,) = api.client().get("/api/v1/register/pakete").json()
    assert (eintrag["paket"], eintrag["version"], eintrag["ampel"]) == (
        "anna-tools/wetter",
        "1.1.0",
        "gelb",
    )
    neueste = next(x for x in anna.get("/api/v1/register/meine").json() if x["version"] == "1.1.0")
    anna.post(f"/api/v1/register/versionen/{neueste['id']}/zurueckziehen")
    assert api.client().get("/api/v1/register/pakete").json()[0]["version"] == v["version"]


def test_an_update_with_a_new_endpoint_shows_and_signs_the_diff(
    api: Api, anna: Any, _migrated: str
) -> None:
    """DoD Sprint 4: an update with a new endpoint shows the diff."""
    anna.post("/api/v1/register/veroeffentlichen", json={"scan_id": pruefung(anna, _migrated)})
    neu = manifest(
        version="1.1.0",
        rechte={"netzwerk": True, "dateien": {"lesen": [], "schreiben": []}, "shell": False,
                "zugangsdaten": False, "umgebungsvariablen": []},
        endpunkte=[{"host": "sammler.example", "zweck": "Statistik", "land": "US",
                    "datenkategorien": ["nutzereingaben"], "rechtsgrundlage": "einwilligung"}],
    )  # fmt: skip
    sid = pruefung(anna, _migrated, {"SKILL.md": MARK, "luibui.json": neu}, projekt="zwei")
    r = anna.post("/api/v1/register/veroeffentlichen", json={"scan_id": sid})
    assert r.status_code == 201, r.text
    d = api.client().get("/api/v1/register/pakete/anna-tools/wetter/1.1.0").json()
    assert d["vorversion"] == "1.0.0"
    assert [a["text"] for a in d["aenderungen"]] == [
        "Netzwerkzugriff neu",
        "Neuer Endpunkt sammler.example (US)",
    ]
    v = api.client().get("/api/v1/register/pakete/anna-tools/wetter").json()["versionen"][0]
    assert json.loads(v["aussage"])["aenderungen"] == d["aenderungen"]  # part of the signature
    erste = api.client().get("/api/v1/register/pakete/anna-tools/wetter/1.0.0").json()
    assert (erste["vorversion"], erste["aenderungen"]) == (None, [])
