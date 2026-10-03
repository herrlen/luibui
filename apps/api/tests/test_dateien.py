"""S4-8: file tree, view and download of the files of a checked version. Only the owner, only
through their scan, decrypted in memory, downloads always as attachment."""

import json
from typing import Any

from sqlalchemy import create_engine, text

from .conftest import Api
from .test_scans import project, upload_zip

MARK = b"# LUIBUI-TESTFIXTURE: entschaerft, nicht ausfuehren\n"
FILES = {
    "SKILL.md": MARK + b"# Wetter\n",
    "luibui.json": b"{}",
    "scripts/tool.py": MARK + b"import os\nos.system('echo hallo')\n",
    "bild.png": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
    "latin1.txt": "Gr\xfc\xdfe".encode("latin-1"),
    'bär"; x.py': MARK + b"x = 1\n",
}


def _scan_mit_bericht(api: Api, url: str, files: dict[str, bytes] = FILES) -> tuple[Any, str]:
    c = api.user("anna@example.org")
    sid = upload_zip(c, project(c), files).json()["id"]
    befunde = [
        {"datei": "scripts/tool.py", "zeile": 3, "schwere": "H", "titel": "Shell-Aufruf",
         "rule_id": "LB-C01-shell", "fingerprint": "f1"},
        {"datei": "scripts/tool.py", "zeile": None, "schwere": "N", "titel": "Ganze Datei",
         "rule_id": "LB-X", "fingerprint": "f2"},
        {"datei": "SKILL.md", "zeile": 1, "schwere": "I", "titel": "Hinweis",
         "rule_id": "LB-Y", "fingerprint": "f3"},
    ]  # fmt: skip
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE scans SET status = 'fertig', report = CAST(:r AS jsonb) WHERE id = :id"),
            {"r": json.dumps({"befunde": befunde}), "id": sid},
        )
    engine.dispose()
    return c, sid


def _ids(c: Any, sid: str) -> dict[str, str]:
    liste = c.get(f"/api/v1/scans/{sid}/dateien").json()
    assert liste["verfuegbar"] is True
    return {d["path"]: d["id"] for d in liste["dateien"]}


def test_tree_lists_files_with_their_finding_count(api: Api, _migrated: str) -> None:
    c, sid = _scan_mit_bericht(api, _migrated)
    liste = c.get(f"/api/v1/scans/{sid}/dateien").json()
    assert sorted(d["path"] for d in liste["dateien"]) == sorted(FILES)
    zahl = {d["path"]: d["befunde"] for d in liste["dateien"]}
    assert zahl["scripts/tool.py"] == 2 and zahl["SKILL.md"] == 1 and zahl["bild.png"] == 0


def test_view_returns_text_and_the_findings_of_this_file(api: Api, _migrated: str) -> None:
    c, sid = _scan_mit_bericht(api, _migrated)
    fid = _ids(c, sid)["scripts/tool.py"]
    v = c.get(f"/api/v1/scans/{sid}/dateien/{fid}").json()
    assert v["text"] == FILES["scripts/tool.py"].decode() and v["gekuerzt"] is False
    assert [(b["zeile"], b["schwere"]) for b in v["befunde"]] == [(3, "H"), (None, "N")]


def test_binary_and_non_utf8_files_have_no_text(api: Api, _migrated: str) -> None:
    c, sid = _scan_mit_bericht(api, _migrated)
    ids = _ids(c, sid)
    for path in ("bild.png", "latin1.txt"):
        assert c.get(f"/api/v1/scans/{sid}/dateien/{ids[path]}").json()["text"] is None


def test_long_files_are_cut_at_a_line_for_the_view_only(api: Api, _migrated: str) -> None:
    # About 1.4 MB that does not compress a hundredfold (the upload rejects ZIP bombs).
    lang = (
        MARK
        + "".join(
            f"Zeile {i:06d} mit Ümlaut {i * 7919 % 1000003:x}\n" for i in range(45_000)
        ).encode()
    )
    c, sid = _scan_mit_bericht(api, _migrated, {**FILES, "lang.txt": lang})
    fid = _ids(c, sid)["lang.txt"]
    v = c.get(f"/api/v1/scans/{sid}/dateien/{fid}").json()
    assert v["gekuerzt"] is True and v["text"].endswith("\n")
    assert len(v["text"].encode()) <= 1024 * 1024
    assert c.get(f"/api/v1/scans/{sid}/dateien/{fid}/download").content == lang


def test_download_is_an_attachment_with_the_exact_bytes(api: Api, _migrated: str) -> None:
    c, sid = _scan_mit_bericht(api, _migrated)
    name = 'bär"; x.py'
    r = c.get(f"/api/v1/scans/{sid}/dateien/{_ids(c, sid)[name]}/download")
    assert r.status_code == 200 and r.content == FILES[name]
    assert r.headers["content-type"] == "application/octet-stream"
    assert r.headers["x-content-type-options"] == "nosniff"
    cd = r.headers["content-disposition"]
    assert (
        cd.startswith('attachment; filename="b_r___x.py"')
        and "filename*=UTF-8''b%C3%A4r%22%3B%20x.py" in cd
    )
    html = c.get(f"/api/v1/scans/{sid}/dateien/{_ids(c, sid)['SKILL.md']}/download")
    assert html.headers["content-type"] == "application/octet-stream"


def test_other_users_and_other_versions_get_404(api: Api, _migrated: str) -> None:
    c, sid = _scan_mit_bericht(api, _migrated)
    fid = _ids(c, sid)["SKILL.md"]
    b = api.user("bert@example.org")
    for pfad in ("dateien", f"dateien/{fid}", f"dateien/{fid}/download"):
        assert b.get(f"/api/v1/scans/{sid}/{pfad}").status_code == 404
    # Anna's second project: its scan must not open the first project's file.
    sid2 = upload_zip(c, project(c, name="zweites")).json()["id"]
    assert c.get(f"/api/v1/scans/{sid2}/dateien/{fid}").status_code == 404
    assert (
        c.get(f"/api/v1/scans/{sid}/dateien/00000000-0000-0000-0000-000000000000").status_code
        == 404
    )


def test_deleted_files_and_git_projects_say_why(api: Api, _migrated: str) -> None:
    c, sid = _scan_mit_bericht(api, _migrated)
    fid = _ids(c, sid)["SKILL.md"]
    engine = create_engine(_migrated)
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE project_versions SET files_deleted_at = now() "
                "WHERE id = (SELECT version_id FROM scans WHERE id = :id)"
            ),
            {"id": sid},
        )
        conn.execute(
            text(
                "UPDATE projects SET quelle = 'git' "
                "WHERE id = (SELECT project_id FROM scans WHERE id = :id)"
            ),
            {"id": sid},
        )
    engine.dispose()
    liste = c.get(f"/api/v1/scans/{sid}/dateien").json()
    assert liste["verfuegbar"] is False and "Git" in liste["grund"]
    assert c.get(f"/api/v1/scans/{sid}/dateien/{fid}").status_code == 404
