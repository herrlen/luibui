"""S5-5: the GitHub Action script against a stub of the luibui API (no network)."""

import json
import os
import subprocess
import threading
import uuid
import zipfile
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest

SKRIPT = Path(__file__).parents[1] / "pruefen.sh"
PROJEKT = str(uuid.uuid4())
SCAN = str(uuid.uuid4())
TOKEN = "lb_" + "x" * 40
SARIF = {
    "version": "2.1.0",
    "runs": [{"results": [{"ruleId": "A"}, {"ruleId": "B", "suppressions": [{}]}]}],
}


class Stub:
    def __init__(self) -> None:
        self.ampel = "gelb"
        self.abfragen = 0
        self.archiv: bytes = b""
        self.auth: list[str] = []


@pytest.fixture
def stub() -> Iterator[tuple[Stub, str]]:
    s = Stub()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a: Any) -> None:
            pass

        def _json(self, code: int, data: object, typ: str = "application/json") -> None:
            body = json.dumps(data).encode()
            self.send_response(code)
            self.send_header("Content-Type", typ)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            s.auth.append(self.headers.get("Authorization", ""))
            roh = self.rfile.read(int(self.headers["Content-Length"]))
            start = roh.find(b"PK\x03\x04")
            s.archiv = roh[start : roh.rfind(b"\r\n--")]
            if self.path != f"/api/v1/projects/{PROJEKT}/scans":
                return self._json(404, {"detail": "Nicht gefunden"})
            self._json(202, {"id": SCAN, "status": "wartend"})

        def do_GET(self) -> None:
            s.auth.append(self.headers.get("Authorization", ""))
            if self.path == f"/api/v1/scans/{SCAN}":
                s.abfragen += 1
                if s.abfragen < 2:
                    return self._json(200, {"id": SCAN, "status": "laeuft"})
                return self._json(
                    200,
                    {"id": SCAN, "status": "fertig", "note": 72, "ampeln": {"gesamt": s.ampel}},
                )
            if self.path == f"/api/v1/scans/{SCAN}/bericht.sarif":
                return self._json(200, SARIF, "application/sarif+json")
            self._json(404, {})

    server = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield s, f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def paket(tmp_path: Path) -> Path:
    p = tmp_path / "repo"
    (p / "skill").mkdir(parents=True)
    (p / "skill" / "SKILL.md").write_text("# Wetter\n")
    (p / "README.md").write_text("# Repo\n")
    return p


def lauf(
    tmp_path: Path, api: str, **env: str
) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
    ausgabe = tmp_path / "output"
    ausgabe.write_text("")
    e = {
        "PATH": os.environ["PATH"],
        "LUIBUI_API": api,
        "LUIBUI_TOKEN": TOKEN,
        "LUIBUI_PROJEKT": PROJEKT,
        "LUIBUI_SARIF": str(tmp_path / "luibui.sarif"),
        "LUIBUI_TAKT": "0",
        "GITHUB_OUTPUT": str(ausgabe),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
    } | env
    if "LUIBUI_PFAD" not in e:
        e["LUIBUI_PFAD"] = str(paket(tmp_path) / "skill")
    r = subprocess.run(["bash", str(SKRIPT)], env=e, capture_output=True, text=True, timeout=60)  # noqa: S603, S607
    werte = dict(z.split("=", 1) for z in ausgabe.read_text().splitlines() if "=" in z)
    return r, werte


def test_yellow_passes_below_the_threshold(tmp_path: Path, stub: tuple[Stub, str]) -> None:
    s, api = stub
    r, out = lauf(tmp_path, api)
    assert r.returncode == 0, r.stdout + r.stderr
    assert out["ampel"] == "gelb" and out["note"] == "72"
    assert out["bericht"].endswith(f"/pruefungen/{SCAN}")
    assert json.loads((tmp_path / "luibui.sarif").read_text()) == SARIF
    assert set(s.auth) == {f"Bearer {TOKEN}"}
    assert "::add-mask::" in r.stdout
    assert zipfile.ZipFile(BytesIO(s.archiv)).namelist() == ["SKILL.md"]
    assert "| gelb | 72 | 1 |" in (tmp_path / "summary").read_text()


@pytest.mark.parametrize(
    ("ampel", "schwelle", "ok"),
    [
        ("rot", "rot", False),
        ("rot", "gesperrt", True),
        ("gesperrt", "nie", True),
        ("gelb", "gelb", False),
    ],
)
def test_threshold(
    tmp_path: Path, stub: tuple[Stub, str], ampel: str, schwelle: str, ok: bool
) -> None:
    s, api = stub
    s.ampel = ampel
    r, _ = lauf(tmp_path, api, LUIBUI_SCHWELLE=schwelle)
    assert (r.returncode == 0) is ok, r.stdout + r.stderr


def test_git_repository_sends_only_tracked_files(tmp_path: Path, stub: tuple[Stub, str]) -> None:
    s, api = stub
    p = paket(tmp_path)
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    subprocess.run([*git, "init", "-q"], cwd=p, check=True)  # noqa: S603
    subprocess.run([*git, "add", "skill/SKILL.md"], cwd=p, check=True)  # noqa: S603
    subprocess.run([*git, "commit", "-qm", "x"], cwd=p, check=True)  # noqa: S603
    (p / "skill" / "geheim.env").write_text("nicht eingecheckt\n")
    r, _ = lauf(tmp_path, api, LUIBUI_PFAD=str(p / "skill"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert zipfile.ZipFile(BytesIO(s.archiv)).namelist() == ["SKILL.md"]


@pytest.mark.parametrize(
    "env",
    [
        {"LUIBUI_PROJEKT": "1; rm -rf /"},
        {"LUIBUI_SCHWELLE": "blau"},
        {"LUIBUI_API": "http://example.invalid"},
        {"LUIBUI_ZEITLIMIT": "10s"},
    ],
)
def test_bad_inputs(tmp_path: Path, stub: tuple[Stub, str], env: dict[str, str]) -> None:
    s, api = stub
    r, _ = lauf(tmp_path, api, **env)
    assert r.returncode == 2 and s.auth == []


def test_upload_refused(tmp_path: Path, stub: tuple[Stub, str]) -> None:
    _, api = stub
    r, _ = lauf(tmp_path, api, LUIBUI_PROJEKT=str(uuid.uuid4()))
    assert r.returncode == 1 and "HTTP 404" in r.stdout
