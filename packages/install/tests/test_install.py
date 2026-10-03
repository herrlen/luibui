"""S4-5: luibui-install checks luibui's signature, the archive and the paths before anything
lands on disk. A tiny local register serves signed test packages."""

import base64
import hashlib
import io
import json
import threading
import zipfile
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from luibui_install.main import main

MARK = b"<!-- LUIBUI-TESTFIXTURE: entschaerft, nicht ausfuehren -->\n"


def zip_von(dateien: dict[str, bytes], link: str | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, inhalt in dateien.items():
            zf.writestr(name, inhalt)
        if link:
            info = zipfile.ZipInfo(link)
            info.external_attr = 0o120777 << 16
            zf.writestr(info, "/etc/passwd")
    return buf.getvalue()


class Register:
    def __init__(self) -> None:
        self.key = Ed25519PrivateKey.generate()
        self.antworten: dict[str, bytes] = {}
        self.versionen: dict[str, list[dict[str, Any]]] = {}

    def veroeffentlichen(
        self,
        paket: str = "acme/wetter",
        version: str = "1.0.0",
        archiv: bytes | None = None,
        ampel: str = "gelb",
        typ: str = "skill",
        **falsch: Any,
    ) -> None:
        archiv = archiv if archiv is not None else zip_von({"SKILL.md": MARK + b"# Wetter\n"})
        aussage = {
            "paket": paket, "version": version, "archiv_bytes": len(archiv),
            "archiv_sha256": hashlib.sha256(archiv).hexdigest(), "ampel": ampel, "note": 90,
            "aenderungen": [{"art": "endpunkt", "text": t} for t in falsch.get("neu", [])],
        } | falsch.get("aussage", {})  # fmt: skip
        text = json.dumps(aussage, sort_keys=True, separators=(",", ":"))
        signatur = (falsch.get("key") or self.key).sign(text.encode())
        eintrag = {
            "version": version,
            "zurueckgezogen": falsch.get("zurueckgezogen", False),
            "aussage": text,
            "signatur": base64.b64encode(signatur).decode(),
            "manifest": {
                "typ": typ, "lizenz": "MIT", "beschreibung": "Wetter\x1b[31m rot",
                "einstieg": "server.py",
                "rechte": {"netzwerk": True, "shell": False},
                "endpunkte": [{"host": "api.wetter.example"}],
            },
        }  # fmt: skip
        liste = [v for v in self.versionen.get(paket, []) if v["version"] != version]
        self.versionen[paket] = [eintrag, *liste]  # newest first, like the register
        info = {"paket": paket, "versionen": self.versionen[paket]}
        ns, name = paket.split("/")
        self.antworten[f"/api/v1/register/pakete/{ns}/{name}"] = json.dumps(info).encode()
        self.antworten[f"/api/v1/register/pakete/{ns}/{name}/{version}/archiv.zip"] = falsch.get(
            "ausgeliefert", archiv
        )


@pytest.fixture
def register(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Register]:
    reg = Register()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            daten = reg.antworten.get(self.path)
            self.send_response(200 if daten is not None else 404)
            self.end_headers()
            self.wfile.write(daten or b"{}")

        def log_message(self, *_: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    pub = reg.key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    monkeypatch.setenv("LUIBUI_REGISTER_URL", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setenv("LUIBUI_REGISTER_SCHLUESSEL", base64.b64encode(pub).decode())
    monkeypatch.setenv("LUIBUI_HOME", str(tmp_path / "home"))
    yield reg
    server.shutdown()


def run(*argv: str) -> tuple[int, str]:
    out = io.StringIO()
    code = main(list(argv), out=out, eingabe=io.StringIO())
    return code, out.getvalue()


def test_installs_a_skill_and_records_it(register: Register, tmp_path: Path) -> None:
    register.veroeffentlichen()
    code, text = run(
        "acme/wetter", "--ziel", "claude", "--ordner", str(tmp_path / "skills"), "--ja"
    )
    assert code == 0, text
    assert (tmp_path / "skills" / "wetter" / "SKILL.md").read_bytes().startswith(MARK)
    assert "Gelb, Note 90" in text and "Signatur geprüft" in text
    assert "\x1b" not in text and "<U+001B>" in text  # package text cannot drive the terminal
    lock = json.loads((tmp_path / "home" / "luibui.lock").read_text())
    assert [(p["paket"], p["version"], p["ziel"]) for p in lock["pakete"]] == [
        ("acme/wetter", "1.0.0", "claude")
    ]
    code, text = run("--liste")
    assert "acme/wetter 1.0.0 (claude)" in text


def test_mcp_target_prints_a_config_snippet(register: Register, tmp_path: Path) -> None:
    register.veroeffentlichen(typ="mcp-server")
    code, text = run("acme/wetter@1.0.0", "--ziel", "mcp", "--ja")
    assert code == 0, text
    ordner = tmp_path / "home" / "pakete" / "acme" / "wetter" / "1.0.0"
    assert (ordner / "SKILL.md").exists()
    assert '"command": "python3"' in text and str(ordner / "server.py") in text
    code, text = run("acme/wetter", "--ziel", "claude", "--ja")
    assert code == 1 and "--ziel mcp" in text  # an MCP server is not a Claude skill


@pytest.mark.parametrize(
    ("falsch", "meldung"),
    [
        ({"key": Ed25519PrivateKey.generate()}, "Signatur stimmt nicht"),
        ({"ausgeliefert": zip_von({"SKILL.md": b"anders"})}, "Prüfsumme"),
        ({"aussage": {"paket": "boese/wetter"}}, "passt nicht zu diesem Paket"),
        ({"zurueckgezogen": True}, "zurückgezogen"),
    ],
)
def test_nothing_is_installed_when_a_check_fails(
    register: Register, tmp_path: Path, falsch: dict[str, Any], meldung: str
) -> None:
    register.veroeffentlichen(**falsch)
    code, text = run("acme/wetter", "--ordner", str(tmp_path / "skills"), "--ja")
    assert code == 1 and meldung in text, text
    assert not (tmp_path / "skills").exists()
    assert not (tmp_path / "home" / "luibui.lock").exists()


@pytest.mark.parametrize(
    "archiv",
    [
        zip_von({"../ausserhalb.md": MARK}),
        zip_von({"/absolut.md": MARK}),
        zip_von({"a\\..\\b.md": MARK}),
        zip_von({"SKILL.md": MARK}, link="link.md"),
    ],
)
def test_unsafe_archives_never_leave_files(
    register: Register, tmp_path: Path, archiv: bytes
) -> None:
    register.veroeffentlichen(archiv=archiv)
    code, text = run("acme/wetter", "--ordner", str(tmp_path / "s"), "--ja")
    assert code == 1 and "nichts installiert" in text, text
    assert not (tmp_path / "s" / "wetter").exists()
    assert not (tmp_path / "ausserhalb.md").exists()
    assert [p.name for p in (tmp_path / "s").iterdir()] == []  # temporary folder removed too


def test_red_needs_trotzdem_and_existing_folders_need_ersetzen(
    register: Register, tmp_path: Path
) -> None:
    register.veroeffentlichen(ampel="rot")
    ziel = ["--ordner", str(tmp_path / "s"), "--ja"]
    assert run("acme/wetter", *ziel)[0] == 3
    assert run("acme/wetter", *ziel, "--trotzdem")[0] == 0
    code, text = run("acme/wetter", *ziel, "--trotzdem")
    assert code == 1 and "--ersetzen" in text
    assert run("acme/wetter", *ziel, "--trotzdem", "--ersetzen")[0] == 0
    register.veroeffentlichen(ampel="gesperrt")
    code, text = run("acme/wetter", *ziel, "--trotzdem", "--ersetzen")
    assert code == 1 and "Gesperrte" in text


def test_without_tty_it_asks_for_ja_and_refuses_plain_http(
    register: Register, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    register.veroeffentlichen()
    assert run("acme/wetter", "--ordner", str(tmp_path / "s"))[0] == 3
    monkeypatch.setenv("LUIBUI_REGISTER_URL", "http://register.example")
    code, text = run("acme/wetter", "--ordner", str(tmp_path / "s"), "--ja")
    assert code == 1 and "HTTPS" in text


def test_an_update_shows_what_the_skipped_versions_bring(
    register: Register, tmp_path: Path
) -> None:
    ziel = ["--ordner", str(tmp_path / "s"), "--ja"]
    register.veroeffentlichen(version="1.0.0")
    assert run("acme/wetter", *ziel)[0] == 0
    register.veroeffentlichen(version="1.1.0", neu=["Neuer Endpunkt a.example (US)"])
    register.veroeffentlichen(
        version="1.2.0", neu=["Shell-Befehle neu", "Neuer Endpunkt a.example (US)"]
    )
    code, text = run("--aktualisierungen")
    assert "acme/wetter: 1.0.0 → 1.2.0" in text
    assert text.count("Neuer Endpunkt a.example (US)") == 1 and "Shell-Befehle neu" in text
    code, text = run("acme/wetter", *ziel, "--ersetzen")
    assert code == 0, text
    assert "Update von 1.0.0 auf 1.2.0" in text and "! Shell-Befehle neu" in text
    assert "aktuell" in run("--aktualisierungen")[1]


def test_changes_from_unsigned_statements_are_ignored(register: Register, tmp_path: Path) -> None:
    ziel = ["--ordner", str(tmp_path / "s"), "--ja"]
    register.veroeffentlichen(version="1.0.0")
    run("acme/wetter", *ziel)
    fremd = Ed25519PrivateKey.generate()
    register.veroeffentlichen(version="1.1.0", neu=["gefälscht"], key=fremd)
    register.veroeffentlichen(version="1.2.0", neu=["echt"])
    code, text = run("acme/wetter", *ziel, "--ersetzen")
    assert code == 0 and "! echt" in text and "gefälscht" not in text


@pytest.mark.parametrize(
    ("ziel", "standard", "hinweis"),
    [
        ("chatgpt", ".agents/skills", "Codex"),
        ("gemini", ".gemini/skills", "Gemini CLI"),
        ("mistral", ".vibe/skills", "Mistral Vibe"),
    ],
)
def test_skill_folders_of_other_clients(
    register: Register,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    ziel: str,
    standard: str,
    hinweis: str,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "nutzer"))
    register.veroeffentlichen()
    code, text = run("acme/wetter", "--ziel", ziel, "--ja")
    assert code == 0, text
    assert (tmp_path / "nutzer" / standard / "wetter" / "SKILL.md").is_file()
    assert hinweis in text
    lock = json.loads((tmp_path / "home" / "luibui.lock").read_text())
    assert lock["pakete"][0]["ziel"] == ziel


def test_upload_writes_the_checked_archive(register: Register, tmp_path: Path) -> None:
    archiv = zip_von({"SKILL.md": MARK + b"# Wetter\n", "beispiel.txt": b"x"})
    register.veroeffentlichen(archiv=archiv)
    code, text = run("acme/wetter", "--ziel", "upload", "--ordner", str(tmp_path), "--ja")
    assert code == 0, text
    assert (tmp_path / "wetter-1.0.0.zip").read_bytes() == archiv
    assert "ChatGPT" in text and not (tmp_path / "home" / "luibui.lock").exists()
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".luibui-")] == []


@pytest.mark.parametrize("ziel", ["gemini", "upload"])
def test_skill_targets_need_a_skill_md(register: Register, tmp_path: Path, ziel: str) -> None:
    register.veroeffentlichen(archiv=zip_von({"README.md": MARK + b"# kein Skill\n"}))
    code, text = run("acme/wetter", "--ziel", ziel, "--ordner", str(tmp_path / "z"), "--ja")
    assert code == 1 and "SKILL.md" in text
    assert list((tmp_path / "z").iterdir()) == []
    register.veroeffentlichen(paket="acme/server", typ="mcp-server")
    code, text = run("acme/server", "--ziel", ziel, "--ordner", str(tmp_path / "z"), "--ja")
    assert code == 1 and "--ziel mcp" in text
