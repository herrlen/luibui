"""S1-11: ``luibui scan`` for folders, ZIP archives and single files."""

import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from luibui_cli.main import main
from luibui_cli.scan import render_text, terminal_safe
from luibui_scan.analyzers import AnalyzerRegistry
from luibui_scan.models import Achse, Ebene, Finding, Nachweisgrad, ScanArt, Schwere
from luibui_scan.scan import Eingabe, scan_prepared


@pytest.fixture(autouse=True)
def private_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Every scratch the CLI creates lands here, so tests can prove it was removed."""
    scratch_parent = tmp_path / "tmp"
    scratch_parent.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch_parent))
    return scratch_parent


def run(capsys: pytest.CaptureFixture[str], *args: str) -> tuple[int, str, str]:
    code = main(["scan", *args])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def skill_dir(tmp_path: Path) -> Path:
    src = tmp_path / "skill"
    (src / "scripts").mkdir(parents=True)
    (src / "SKILL.md").write_text("# Skill\n")
    (src / "scripts/run.py").write_text("print(1)\n")
    return src


def test_folder_text(tmp_path: Path, private_tmp: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, str(skill_dir(tmp_path)))
    assert code == 0
    assert "Umfang:    Dateiauswahl ohne Manifest" in out
    assert "Pakettyp:  skill" in out
    assert "Dateien:   2" in out
    assert "Sicherheit: Gelb" in out
    assert "DSGVO:      nicht bewertet" in out
    assert "Gesamt:     Gelb, Prüfung nötig" in out
    assert "Note:       100 von 100" in out
    assert "sagt nichts über die Sicherheit" in out
    assert "grün" not in out.lower()
    assert list(private_tmp.iterdir()) == []


def test_folder_with_manifest_is_a_package(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = skill_dir(tmp_path)
    (src / "luibui.json").write_text("{}")
    code, out, _ = run(capsys, str(src), "--json")
    data = json.loads(out)
    assert code == 0
    assert data["pruefumfang"] == "paket"
    assert data["paket"]["quelle"] == "lokal"
    assert data["paket"]["name"] == "skill"
    # No analyzers yet: an incomplete scan never turns green, not even with a manifest.
    assert data["ampeln"] == {"sicherheit": "gelb", "dsgvo": "gelb", "gesamt": "gelb"}
    assert data["freigabe"] == "pruefung_noetig"


def test_zip_json(tmp_path: Path, private_tmp: Path, capsys: pytest.CaptureFixture[str]) -> None:
    archive = tmp_path / "paket.ZIP"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("SKILL.md", "# Skill\n")
        zf.writestr("server.py", "from mcp.server.fastmcp import FastMCP\n")
    code, out, _ = run(capsys, str(archive), "--json")
    data = json.loads(out)
    assert code == 0
    assert data["scan_art"] == "lokal"
    assert data["pruefumfang"] == "auswahl"
    assert data["paket"]["quelle"] == "zip"
    assert data["paket"]["dateien"] == 2
    assert "Dateiauswahl ohne Manifest" in data["hinweise"]
    assert list(private_tmp.iterdir()) == []


def test_single_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "SKILL.md"
    path.write_text("# Skill\n")
    code, out, _ = run(capsys, str(path), "--json")
    data = json.loads(out)
    assert code == 0
    assert data["pruefumfang"] == "einzeldatei"
    assert data["paket"]["quelle"] == "datei"
    assert data["ampeln"]["dsgvo"] == "nicht_bewertet"


def test_zip_slip_is_rejected(
    tmp_path: Path, private_tmp: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../../\x1b[31mevil.sh", "echo harmlos")
    code, out, _ = run(capsys, str(archive))
    assert code == 3
    assert out.startswith("Abgelehnt: Ein Pfad zeigt aus dem Paket heraus.")
    assert "\x1b" not in out
    assert "\\x1b[31mevil.sh" in out
    assert "Es wurde nichts geprüft." in out
    assert list(private_tmp.iterdir()) == []
    assert not (tmp_path.parent / "evil.sh").exists()


def test_rejection_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "link").symlink_to("/etc/passwd")
    code, out, _ = run(capsys, str(src), "--json")
    assert code == 3
    assert json.loads(out) == {
        "abgelehnt": {
            "grund": "verknuepfung",
            "text": "Das Paket enthält eine Verknüpfung oder Sonderdatei.",
            "pfad": "link",
        }
    }


def test_missing_path(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run(capsys, "/nicht/vorhanden")
    assert code == 2
    assert out == ""
    assert "Pfad nicht gefunden" in err


@pytest.mark.parametrize(
    ("raw", "shown"),
    [
        ("normal ä ✓\nzweite", "normal ä ✓\nzweite"),
        ("\x1b[2J", "\\x1b[2J"),
        ("a\rb\tc", "a\\x0db\\x09c"),
        ("evil‮gpj.md", "evil\\u202egpj.md"),
        ("zero​width", "zero\\u200bwidth"),
        ("tag\U000e0041", "tag\\U000e0041"),
    ],
)
def test_terminal_safe(raw: str, shown: str) -> None:
    assert terminal_safe(raw) == shown


class OneFinding:
    """Stand-in analyzer that reports hostile text, to check how findings are printed."""

    def __init__(self) -> None:
        from luibui_scan.analyzers import AnalyzerInfo

        self.info = AnalyzerInfo(name="test", titel="Test", ebenen=frozenset({Ebene.B}))

    def analyze(self, ctx: object) -> list[Finding]:
        return [
            Finding(
                rule_id="LB-B01-test",
                ebene=Ebene.B,
                schwere=Schwere.H,
                achse=Achse.SICHERHEIT,
                titel="Versteckte \x1b[8mAnweisung",
                erklaerung="Test",
                datei="SKILL.md",
                zeile=3,
                beleg="Zeile‮ eins\nZeile zwei",
                nachweisgrad=Nachweisgrad.STATISCH_ERKANNT,
                normbezug=(),
                fix="Entfernen",
                fix_prompt="",
            )
        ]


def test_findings_are_printed_escaped(tmp_path: Path) -> None:
    (tmp_path / "SKILL.md").write_text("x")
    registry = AnalyzerRegistry()
    registry.add(OneFinding())
    result = scan_prepared(tmp_path, Eingabe.LOKAL, ScanArt.LOKAL, registry)
    out = render_text(tmp_path, result)
    assert "[H] Versteckte \\x1b[8mAnweisung  (LB-B01-test)" in out
    assert "SKILL.md:3" in out
    assert "| Zeile\\u202e eins" in out
    assert "| Zeile zwei" in out
    assert "\x1b" not in out and "‮" not in out
    assert "keine Prüfung eingebaut" not in out
    assert "Sicherheit: Rot" in out
    assert "Note:       85 von 100" in out


class Clean:
    def __init__(self) -> None:
        from luibui_scan.analyzers import AnalyzerInfo

        self.info = AnalyzerInfo(name="leer", titel="Leer", ebenen=frozenset({Ebene.B}))

    def analyze(self, ctx: object) -> list[Finding]:
        return []


def test_green_wording_never_says_safe(tmp_path: Path) -> None:
    (tmp_path / "SKILL.md").write_text("x")
    (tmp_path / "luibui.json").write_text("{}")
    registry = AnalyzerRegistry()
    registry.add(Clean())
    out = render_text(tmp_path, scan_prepared(tmp_path, Eingabe.LOKAL, ScanArt.LOKAL, registry))
    assert "Gesamt:     Grün, keine bekannten Befunde, geprüft am " in out
    assert "sicher" not in out.replace("Sicherheit", "")


@pytest.mark.parametrize(("fail_on", "code"), [(None, 0), ("gelb", 1), ("rot", 0), ("gesperrt", 0)])
def test_fail_on(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], fail_on: str | None, code: int
) -> None:
    """Without analyzers every scan is yellow; the thresholds are checked against that."""
    extra = [] if fail_on is None else ["--fail-on", fail_on]
    got, out, _ = run(capsys, str(skill_dir(tmp_path)), *extra)
    assert got == code
    assert "Gesamt:     Gelb" in out


@pytest.mark.parametrize(
    ("gesamt", "fail_on", "code"),
    [
        ("rot", "rot", 1),
        ("gesperrt", "rot", 1),
        ("gesperrt", "gesperrt", 1),
        ("rot", "gesperrt", 0),
        ("gruen", "gelb", 0),
    ],
)
def test_exit_code_thresholds(gesamt: str, fail_on: str, code: int, tmp_path: Path) -> None:
    from dataclasses import replace

    from luibui_cli.scan import exit_code
    from luibui_scan.scoring import AmpelSicherheit

    (tmp_path / "a.md").write_text("x")
    result = scan_prepared(tmp_path, Eingabe.LOKAL, ScanArt.LOKAL, AnalyzerRegistry())
    result = replace(result, bewertung=replace(result.bewertung, gesamt=AmpelSicherheit(gesamt)))
    assert exit_code(result, fail_on) == code


def test_fail_on_rejects_unknown_level(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["scan", ".", "--fail-on", "gruen"])
    assert exc.value.code == 2
