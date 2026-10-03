"""S1-1: projects, uploads, stored versions, scan status — and user B never reaches A's data."""

import io
import json
import zipfile
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, text

from .conftest import Api

pytestmark = pytest.mark.db


def db_rows(url: str, sql: str) -> list[Any]:
    engine = create_engine(url)
    with engine.connect() as conn:
        rows = list(conn.execute(text(sql)).all())
    engine.dispose()
    return rows


def zip_bytes(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


SKILL = {"SKILL.md": b"# LUIBUI-TESTFIXTURE Skill\ngeheimer Inhalt\n", "luibui.json": b"{}"}


def project(c, name: str = "wetter", **extra: Any) -> str:  # type: ignore[no-untyped-def]
    r = c.post("/api/v1/projects", json={"name": name, "typ": "skill", **extra})
    assert r.status_code == 201, r.text
    return r.json()["id"]  # type: ignore[no-any-return]


def upload_zip(c, pid: str, files: dict[str, bytes] = SKILL):  # type: ignore[no-untyped-def]
    return c.post(
        f"/api/v1/projects/{pid}/scans",
        data={"art": "zip"},
        files={"dateien": ("paket.zip", zip_bytes(files), "application/zip")},
    )


def scratch_dirs(tmp_path: Path) -> list[str]:
    return sorted(p.name for p in (tmp_path / "scratch").iterdir())


def blobs(tmp_path: Path) -> list[Path]:
    root = tmp_path / "projects"
    return [p for p in root.rglob("*") if p.is_file()] if root.exists() else []


# --- projects --------------------------------------------------------------------------------


def test_project_crud_and_isolation(api: Api) -> None:
    a, b = api.user("anna@example.org"), api.user("bert@example.org")
    pid = project(a)
    assert a.get(f"/api/v1/projects/{pid}").json()["name"] == "wetter"
    assert project(b)  # same name is fine for another owner
    assert [p["id"] for p in a.get("/api/v1/projects").json()] == [pid]
    assert b.get(f"/api/v1/projects/{pid}").status_code == 404
    assert b.delete(f"/api/v1/projects/{pid}").status_code == 404
    assert a.post("/api/v1/projects", json={"name": "wetter", "typ": "skill"}).status_code == 409
    assert a.delete(f"/api/v1/projects/{pid}").status_code == 204
    assert a.get(f"/api/v1/projects/{pid}").status_code == 404


# --- uploads ---------------------------------------------------------------------------------


def test_zip_upload_is_staged_stored_encrypted_and_queued(
    api: Api, tmp_path: Path, _migrated: str
) -> None:
    c = api.user("anna@example.org")
    pid = project(c)
    r = upload_zip(c, pid)
    assert r.status_code == 202, r.text
    scan = r.json()
    assert (scan["status"], scan["pruefumfang"], scan["bericht"]) == ("wartend", "paket", None)

    ((job_id, payload),) = db_rows(_migrated, "SELECT id, payload FROM jobs")
    assert payload["eingabe"] == "zip" and payload["scan_id"] == scan["id"]
    staged = tmp_path / "scratch" / str(job_id)
    assert sorted(p.name for p in staged.iterdir()) == ["SKILL.md", "luibui.json"]

    stored = db_rows(_migrated, "SELECT path FROM stored_files")
    assert sorted(r[0] for r in stored) == ["SKILL.md", "luibui.json"]
    assert len(blobs(tmp_path)) == 2
    for blob in blobs(tmp_path):
        assert b"geheimer" not in blob.read_bytes()
    (version,) = db_rows(_migrated, "SELECT number, file_count FROM project_versions")
    assert tuple(version) == (1, 2)


@pytest.mark.parametrize(
    ("data", "files", "umfang"),
    [
        ({"art": "datei"}, [("dateien", ("SKILL.md", b"# Skill"))], "einzeldatei"),
        ({"art": "text", "text": "# Skill\nHallo"}, [], "einzeldatei"),
        (
            {"art": "auswahl", "pfade": ["plugin/SKILL.md", "plugin/src/a.py"]},
            [("dateien", ("SKILL.md", b"a")), ("dateien", ("a.py", b"b"))],
            "auswahl",
        ),
    ],
)
def test_other_input_kinds(
    api: Api, tmp_path: Path, data: dict[str, Any], files: list[Any], umfang: str
) -> None:
    c = api.user("anna@example.org")
    pid = project(c)
    r = c.post(f"/api/v1/projects/{pid}/scans", data=data, files=files or None)
    if not files:
        r = c.post(f"/api/v1/projects/{pid}/scans", data=data, files={"x": ("", b"")})
    assert r.status_code == 202, r.text
    assert r.json()["pruefumfang"] == umfang


def test_selection_keeps_folders(api: Api, tmp_path: Path) -> None:
    c = api.user("anna@example.org")
    pid = project(c)
    r = c.post(
        f"/api/v1/projects/{pid}/scans",
        data={"art": "auswahl", "pfade": ["plugin/src/a.py"]},
        files=[("dateien", ("a.py", b"print(1)"))],
    )
    assert r.status_code == 202
    (staged,) = (tmp_path / "scratch").iterdir()
    assert (staged / "plugin/src/a.py").read_bytes() == b"print(1)"


def test_zip_slip_is_refused_and_nothing_stays(api: Api, tmp_path: Path, _migrated: str) -> None:
    c = api.user("anna@example.org")
    pid = project(c)
    r = upload_zip(c, pid, {"ok.md": b"x", "../../evil.sh": b"echo harmlos"})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "pfad_ausserhalb"
    assert r.json()["detail"]["pfad"] == "../../evil.sh"
    assert scratch_dirs(tmp_path) == []
    assert blobs(tmp_path) == []
    assert db_rows(_migrated, "SELECT count(*) FROM scans")[0][0] == 0
    assert db_rows(_migrated, "SELECT count(*) FROM project_versions")[0][0] == 0
    assert not (tmp_path / "evil.sh").exists()


@pytest.mark.parametrize(
    ("data", "files"),
    [
        ({"art": "git"}, [("dateien", ("a", b"x"))]),
        ({"art": "auswahl", "pfade": ["a", "b"]}, [("dateien", ("a", b"x"))]),
        ({"art": "zip"}, [("dateien", ("a.zip", b"x")), ("dateien", ("b.zip", b"y"))]),
        ({"art": "datei"}, [("dateien", ("../a.md", b"x"))]),
        ({"art": "datei"}, [("anders", ("a.md", b"x"))]),
    ],
)
def test_bad_uploads(api: Api, tmp_path: Path, data: dict[str, Any], files: list[Any]) -> None:
    c = api.user("anna@example.org")
    r = c.post(f"/api/v1/projects/{project(c)}/scans", data=data, files=files)
    assert r.status_code == 422, r.text
    assert scratch_dirs(tmp_path) == []


def test_upload_size_limit(api: Api, monkeypatch: pytest.MonkeyPatch) -> None:
    c = api.user("anna@example.org")
    pid = project(c)
    monkeypatch.setenv("UPLOAD_MAX_BYTES", "1000")
    from luibui_api.settings import get_settings

    get_settings.cache_clear()
    r = c.post(
        f"/api/v1/projects/{pid}/scans",
        data={"art": "datei"},
        files={"dateien": ("a", b"x" * 2000)},
    )
    assert r.status_code == 413


def test_quota(api: Api, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    c = api.user("anna@example.org")
    pid = project(c)
    monkeypatch.setenv("ACCOUNT_QUOTA_BYTES", "100")
    from luibui_api.settings import get_settings

    get_settings.cache_clear()
    r = upload_zip(c, pid, {"a.md": b"x" * 101})
    assert r.status_code == 413
    assert scratch_dirs(tmp_path) == [] and blobs(tmp_path) == []


def test_only_the_last_versions_are_kept(
    api: Api, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _migrated: str
) -> None:
    monkeypatch.setenv("VERSIONS_PER_PROJECT", "2")
    from luibui_api.settings import get_settings

    get_settings.cache_clear()
    c = api.user("anna@example.org")
    pid = project(c)
    for i in range(3):
        assert upload_zip(c, pid, {"a.md": f"v{i}".encode()}).status_code == 202
    assert [r[0] for r in db_rows(_migrated, "SELECT number FROM project_versions ORDER BY 1")] == [
        2,
        3,
    ]
    assert len(blobs(tmp_path)) == 2
    # The scan of the dropped version survives, only its link to the files is gone.
    assert db_rows(_migrated, "SELECT count(*) FROM scans WHERE version_id IS NULL")[0][0] == 1


def test_delete_after_scan_stores_nothing(api: Api, tmp_path: Path, _migrated: str) -> None:
    c = api.user("anna@example.org")
    pid = project(c, nach_pruefung_loeschen=True)
    assert upload_zip(c, pid).status_code == 202
    assert blobs(tmp_path) == []
    assert db_rows(_migrated, "SELECT count(*) FROM project_versions")[0][0] == 0
    assert len(scratch_dirs(tmp_path)) == 1  # the worker still gets the files


def test_deleting_a_project_deletes_its_files(api: Api, tmp_path: Path) -> None:
    c = api.user("anna@example.org")
    pid = project(c)
    upload_zip(c, pid)
    assert blobs(tmp_path)
    c.delete(f"/api/v1/projects/{pid}")
    assert blobs(tmp_path) == []


def test_api_token_can_upload(api: Api) -> None:
    c = api.user("anna@example.org")
    pid = project(c)
    token = c.post("/api/v1/tokens", json={"name": "ci"}).json()["token"]
    cli = api.client("https://api.luibui.com")
    cli.headers["Authorization"] = f"Bearer {token}"
    r = upload_zip(cli, pid)
    assert r.status_code == 202
    assert cli.get(f"/api/v1/scans/{r.json()['id']}").status_code == 200


# --- rule 9 ----------------------------------------------------------------------------------


def test_b_cannot_upload_to_or_read_from_a(api: Api, tmp_path: Path) -> None:
    a, b = api.user("anna@example.org"), api.user("bert@example.org")
    pid = project(a)
    scan_id = upload_zip(a, pid).json()["id"]
    assert upload_zip(b, pid).status_code == 404
    assert b.get(f"/api/v1/scans/{scan_id}").status_code == 404
    assert a.get(f"/api/v1/scans/{scan_id}").status_code == 200
    assert len(scratch_dirs(tmp_path)) == 1


def test_unauthenticated(api: Api) -> None:
    c = api.client()
    assert c.get("/api/v1/projects").status_code == 401
    assert c.post("/api/v1/projects", json={"name": "x", "typ": "skill"}).status_code == 401
    pid = project(api.user("anna@example.org"))
    assert upload_zip(c, pid).status_code == 401


# --- end to end with the real worker ---------------------------------------------------------


def test_worker_scans_the_upload(api: Api, tmp_path: Path, _migrated: str) -> None:
    from luibui_worker.main import Worker
    from luibui_worker.settings import WorkerSettings

    c = api.user("anna@example.org")
    pid = project(c)
    scan_id = upload_zip(c, pid).json()["id"]
    engine = create_engine(_migrated)
    worker = Worker(
        WorkerSettings(database_url=_migrated, scratch_root=tmp_path / "scratch"),  # type: ignore[arg-type]
        engine=engine,
    )
    assert worker.run_once()
    engine.dispose()

    s = c.get(f"/api/v1/scans/{scan_id}").json()
    assert s["status"] == "fertig", s
    # No analyzers yet: incomplete, so never green.
    assert s["ampeln"] == {"sicherheit": "gelb", "dsgvo": "gelb", "gesamt": "gelb"}
    assert s["bericht"]["scan_id"] == scan_id
    assert s["bericht"]["paket"]["name"] == "wetter"
    assert s["bericht"]["pruefumfang"] == "paket"
    assert scratch_dirs(tmp_path) == []
    (status,) = db_rows(_migrated, "SELECT status FROM jobs")[0]
    assert status == "done"
    json.dumps(s["bericht"])


def test_known_malware_is_never_stored(
    api: Api, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, _migrated: str
) -> None:
    import hashlib

    from luibui_api import uploads

    payload = b"LUIBUI-TESTFIXTURE: entschaerft\n"
    monkeypatch.setattr(
        uploads, "known_malware", lambda: frozenset({hashlib.sha256(payload).hexdigest()})
    )
    c = api.user("anna@example.org")
    r = upload_zip(c, project(c), {"x.bin": payload, "SKILL.md": b"# x"})
    assert r.status_code == 202
    assert blobs(tmp_path) == []
    assert db_rows(_migrated, "SELECT count(*) FROM project_versions")[0][0] == 0
    assert len(scratch_dirs(tmp_path)) == 1  # still scanned, so the report shows A08


def test_project_list_shows_latest_scan_and_scan_list(api: Api) -> None:
    a, b = api.user("anna@example.org"), api.user("bert@example.org")
    pid = project(a)
    first = upload_zip(a, pid).json()["id"]
    second = upload_zip(a, pid).json()["id"]
    (p,) = a.get("/api/v1/projects").json()
    assert p["letzte_pruefung"]["id"] == second and p["letzte_pruefung"]["status"] == "wartend"
    ids = [s["id"] for s in a.get(f"/api/v1/projects/{pid}/scans").json()]
    assert ids == [second, first]
    assert b.get(f"/api/v1/projects/{pid}/scans").status_code == 404
    assert b.get("/api/v1/projects").json() == []


# --- single checks from the overview (no project) ---------------------------------------------


def einzel(c, name: str = "SKILL.md", inhalt: bytes = b"# LUIBUI-TESTFIXTURE\nHallo\n"):  # type: ignore[no-untyped-def]
    return c.post("/api/v1/scans", data={"art": "datei"}, files={"dateien": (name, inhalt)})


def test_single_check_without_project_stores_no_files(
    api: Api, tmp_path: Path, _migrated: str
) -> None:
    a = api.user("a@luibui.example")
    r = einzel(a)
    assert r.status_code == 202, r.text
    s = r.json()
    assert s["project_id"] is None and s["pruefumfang"] == "einzeldatei"
    assert blobs(tmp_path) == []
    row = db_rows(_migrated, "SELECT owner_id IS NOT NULL, expires_at FROM scans")[0]
    assert row == (True, None)
    liste = a.get("/api/v1/scans").json()
    assert [x["id"] for x in liste] == [s["id"]]
    assert a.get(f"/api/v1/scans/{s['id']}").status_code == 200


def test_single_check_kinds(api: Api) -> None:
    a = api.user("a@luibui.example")
    assert a.post("/api/v1/scans", data={"art": "text", "text": "Hallo Welt"}).status_code == 202
    zip_ = ("paket.zip", zip_bytes(SKILL))
    assert a.post("/api/v1/scans", data={"art": "zip"}, files={"dateien": zip_}).status_code == 202
    git = {"art": "git", "git_url": "https://github.com/x/y"}
    assert a.post("/api/v1/scans", data=git).status_code == 422


def test_b_cannot_see_or_delete_single_checks_of_a(api: Api) -> None:
    a, b = api.user("a@luibui.example"), api.user("b@luibui.example")
    sid = einzel(a).json()["id"]
    assert b.get("/api/v1/scans").json() == []
    assert b.get(f"/api/v1/scans/{sid}").status_code == 404
    assert b.delete(f"/api/v1/scans/{sid}").status_code == 404
    assert a.get(f"/api/v1/scans/{sid}").status_code == 200


def test_deleting_single_checks(api: Api, _migrated: str) -> None:
    a = api.user("a@luibui.example")
    sid = einzel(a).json()["id"]
    assert a.delete(f"/api/v1/scans/{sid}").status_code == 409  # still queued
    with create_engine(_migrated).begin() as conn:
        conn.execute(text("UPDATE scans SET status = 'fertig'"))
    assert a.delete(f"/api/v1/scans/{sid}").status_code == 204
    assert a.get(f"/api/v1/scans/{sid}").status_code == 404
    pid = project(a)
    psid = upload_zip(a, pid).json()["id"]
    with create_engine(_migrated).begin() as conn:
        conn.execute(text("UPDATE scans SET status = 'fertig'"))
    assert a.delete(f"/api/v1/scans/{psid}").status_code == 409  # belongs to a project
    assert [x["id"] for x in a.get("/api/v1/scans").json()] == []


def test_single_check_needs_login_and_open_intake(api: Api) -> None:
    anon = api.client()
    assert einzel(anon).status_code == 401


def test_progress_is_shown_only_while_the_scan_runs(api: Api, _migrated: str) -> None:
    c = api.user("anna@example.org")
    sid = upload_zip(c, project(c)).json()["id"]
    f = '{"schritt": 2, "von": 9, "titel": "B – Inhalte"}'
    engine = create_engine(_migrated)
    for status, erwartet in (("wartend", None), ("laeuft", json.loads(f)), ("fertig", None)):
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE scans SET status = CAST(:s AS scan_status), "
                    "fortschritt = CAST(:f AS jsonb) WHERE id = :id"
                ),
                {"s": status, "f": f, "id": sid},
            )
        assert c.get(f"/api/v1/scans/{sid}").json()["fortschritt"] == erwartet
    engine.dispose()
