"""S5-3: ``luibui audit`` over the lock file of luibui-install, optionally with a local scan."""

import hashlib
import json
from pathlib import Path

import pytest

from luibui_cli.main import main


def installiert(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, inhalt: bytes) -> Path:
    home, ordner = tmp_path / "home", tmp_path / "skills" / "wetter"
    ordner.mkdir(parents=True)
    (ordner / "SKILL.md").write_bytes(inhalt)
    home.mkdir()
    eintrag = {
        "paket": "acme/wetter",
        "version": "1.0.0",
        "archiv_sha256": "0" * 64,
        "ziel": "claude",
        "ordner": str(ordner),
        "dateien": {"SKILL.md": hashlib.sha256(inhalt).hexdigest()},
    }
    (home / "luibui.lock").write_text(json.dumps({"version": 1, "pakete": [eintrag]}))
    monkeypatch.setenv("LUIBUI_HOME", str(home))
    return ordner


def test_audit_offline_and_with_local_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ordner = installiert(tmp_path, monkeypatch, b"# Wetter\nZeigt das Wetter.\n")
    assert main(["audit", "--ohne-register", "--scan"]) == 0
    out = capsys.readouterr().out
    assert "acme/wetter 1.0.0 (claude): unverändert" in out and "Lokale Prüfung:" in out
    (ordner / "SKILL.md").write_text("# Wetter\nanders\n")
    assert main(["audit", "--ohne-register"]) == 1
    assert "Geändert: SKILL.md" in capsys.readouterr().out


def test_audit_without_installations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("LUIBUI_HOME", str(tmp_path))
    assert main(["audit"]) == 0
    assert "Noch nichts installiert" in capsys.readouterr().out
