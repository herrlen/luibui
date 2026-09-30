"""S2-5: correlation. An instruction that points an agent to code raises that code's findings."""

from pathlib import Path

import pytest

from luibui_scan.analyzers import AnalyzerInfo, AnalyzerRegistry
from luibui_scan.analyzers._common import text_files
from luibui_scan.context import ScanContext
from luibui_scan.inventory import build_inventory
from luibui_scan.korrelation import fingerprint, in_testdateien, verweise
from luibui_scan.models import Achse, Ebene, Finding, Nachweisgrad, Pruefumfang, ScanArt, Schwere
from luibui_scan.scan import Eingabe, scan_prepared


def befund(datei: str, schwere: Schwere, ebene: Ebene = Ebene.C, rule: str = "LB-C01-x") -> Finding:
    return Finding(
        rule_id=rule,
        ebene=ebene,
        schwere=schwere,
        achse=Achse.SICHERHEIT,
        titel="Test",
        erklaerung="Test.",
        datei=datei,
        zeile=1,
        beleg=f"beleg {datei}",
        nachweisgrad=Nachweisgrad.STATISCH_ERKANNT,
        normbezug=(),
        fix="x",
        fix_prompt="",
    )


class Feste:
    def __init__(self, findings: list[Finding]) -> None:
        self.info = AnalyzerInfo(name="fest", titel="Fest", ebenen=frozenset({Ebene.C}))
        self._findings = findings

    def analyze(self, ctx: ScanContext) -> list[Finding]:
        return self._findings


def scan(
    tmp_path: Path,
    files: dict[str, str],
    findings: list[Finding],
    art: ScanArt = ScanArt.LOKAL,
    eingabe: Eingabe = Eingabe.LOKAL,
) -> dict[str, Finding]:
    for rel, text in files.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text)
    reg = AnalyzerRegistry()
    reg.add(Feste(findings))
    result = scan_prepared(tmp_path, eingabe, art, reg, erwartet={})
    return {f.datei or "": f for f in result.pipeline.findings}


SKILL = "---\nname: x\n---\nRun `python scripts/setup.py` before you start.\n"


def test_referenced_code_is_raised_one_level(tmp_path: Path) -> None:
    files = {"SKILL.md": SKILL, "scripts/setup.py": "x = 1\n", "scripts/other.py": "y = 2\n"}
    found = scan(
        tmp_path,
        files,
        [befund("scripts/setup.py", Schwere.H), befund("scripts/other.py", Schwere.H)],
    )
    raised, untouched = found["scripts/setup.py"], found["scripts/other.py"]
    assert raised.schwere is Schwere.K and raised.hochgestuft_von is Schwere.H
    assert "SKILL.md, Zeile 4" in raised.erklaerung
    assert untouched.schwere is Schwere.H and untouched.hochgestuft_von is None


@pytest.mark.parametrize(
    ("schwere", "ebene", "erwartet"),
    [
        (Schwere.M, Ebene.C, Schwere.H),
        (Schwere.K, Ebene.C, Schwere.K),  # already the top
        (Schwere.N, Ebene.C, Schwere.N),  # hints stay hints
        (Schwere.H, Ebene.B, Schwere.H),  # only what code does
    ],
)
def test_which_findings_are_raised(
    tmp_path: Path, schwere: Schwere, ebene: Ebene, erwartet: Schwere
) -> None:
    files = {"SKILL.md": SKILL, "scripts/setup.py": "x = 1\n"}
    found = scan(tmp_path, files, [befund("scripts/setup.py", schwere, ebene)])
    assert found["scripts/setup.py"].schwere is erwartet


def test_markdown_is_followed_but_not_raised(tmp_path: Path) -> None:
    files = {
        "SKILL.md": "See [the guide](references/guide.md).\n",
        "references/guide.md": "Then run `bash ../scripts/install.sh`.\n",
        "scripts/install.sh": "echo x\n",
    }
    found = scan(
        tmp_path,
        files,
        [
            befund("references/guide.md", Schwere.M, Ebene.B),
            befund("scripts/install.sh", Schwere.M),
        ],
    )
    assert found["references/guide.md"].schwere is Schwere.M
    assert found["scripts/install.sh"].schwere is Schwere.H


def test_not_in_the_quick_scan(tmp_path: Path) -> None:
    files = {"SKILL.md": SKILL, "scripts/setup.py": "x = 1\n"}
    schnell = scan(
        tmp_path, files, [befund("scripts/setup.py", Schwere.H)], ScanArt.SCHNELL, Eingabe.ZIP
    )
    assert schnell["scripts/setup.py"].schwere is Schwere.H


def test_readme_alone_does_not_count(tmp_path: Path) -> None:
    files = {"README.md": "Run `python scripts/setup.py`.\n", "scripts/setup.py": "x = 1\n"}
    found = scan(tmp_path, files, [befund("scripts/setup.py", Schwere.H)])
    assert found["scripts/setup.py"].schwere is Schwere.H


def test_findings_get_stable_fingerprints(tmp_path: Path) -> None:
    f = befund("a.py", Schwere.M)
    assert fingerprint(f) == fingerprint(f.model_copy(update={"zeile": 99}))
    assert fingerprint(f) != fingerprint(f.model_copy(update={"datei": "b.py"}))
    found = scan(tmp_path, {"a.py": "x = 1\n"}, [f])
    assert found["a.py"].fingerprint == fingerprint(f)


@pytest.mark.parametrize(
    ("text", "ziel"),
    [
        ("Run `python scripts/x.py`.", "scripts/x.py"),
        ("Run `${CLAUDE_PLUGIN_ROOT}/scripts/x.py`.", "scripts/x.py"),
        ("Execute ./scripts/x.py now.", "scripts/x.py"),
        ("[Skript](scripts/x.py)", "scripts/x.py"),
        ("uv run {baseDir}/scripts/x.py", "scripts/x.py"),
    ],
)
def test_reference_forms(tmp_path: Path, text: str, ziel: str) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "x.py").write_text("x = 1\n")
    (tmp_path / "SKILL.md").write_text(text + "\n")
    inv = build_inventory(tmp_path)
    ctx = ScanContext(
        root=tmp_path, scan_art=ScanArt.LOKAL, pruefumfang=Pruefumfang.AUSWAHL,
        inventory=inv.entries,
    )  # fmt: skip
    assert set(verweise(list(text_files(ctx)), {e.path for e in inv.entries})) == {ziel}


def test_references_never_leave_the_package(tmp_path: Path) -> None:
    (tmp_path / "SKILL.md").write_text("Run `python ../../etc/x.py` and [a](https://x.invalid).\n")
    inv = build_inventory(tmp_path)
    ctx = ScanContext(
        root=tmp_path, scan_art=ScanArt.LOKAL, pruefumfang=Pruefumfang.AUSWAHL,
        inventory=inv.entries,
    )  # fmt: skip
    assert verweise(list(text_files(ctx)), {e.path for e in inv.entries}) == {}


HOOKS = (
    '{"hooks": {"Stop": [{"hooks": [{"type": "command", '
    '"command": "python3 \\"${CLAUDE_PLUGIN_ROOT}/hooks/stop.py\\""}]}]}}'
)


@pytest.mark.parametrize("wo", ["", "plugins/p/"])
def test_scripts_started_by_plugin_hooks_are_raised(tmp_path: Path, wo: str) -> None:
    """Benchmark S3-6: a hook runs its script by itself, like an instruction the agent follows."""
    files = {f"{wo}hooks/hooks.json": HOOKS, f"{wo}hooks/stop.py": "x = 1\n"}
    found = scan(tmp_path, files, [befund(f"{wo}hooks/stop.py", Schwere.H)])
    f = found[f"{wo}hooks/stop.py"]
    assert f.schwere is Schwere.K and f"{wo}hooks/hooks.json" in f.erklaerung


@pytest.mark.parametrize(
    ("datei", "ebene", "schwere", "erwartet"),
    [
        ("tests/unit/test_path_validation.py", Ebene.C, Schwere.K, Schwere.M),
        ("tests/cli.spec.ts", Ebene.C, Schwere.H, Schwere.M),
        ("src/__tests__/a.js", Ebene.E, Schwere.H, Schwere.M),
        ("tests/test_x.py", Ebene.C, Schwere.M, Schwere.M),
        ("tests/test_x.py", Ebene.B, Schwere.K, Schwere.K),  # instructions still count
        ("tests/test_x.py", Ebene.A, Schwere.H, Schwere.H),
        ("src/server.py", Ebene.C, Schwere.K, Schwere.K),
        ("contest/run.py", Ebene.C, Schwere.K, Schwere.K),
    ],
)
def test_code_findings_in_test_files_count_at_most_medium(
    datei: str, ebene: Ebene, schwere: Schwere, erwartet: Schwere
) -> None:
    (f,) = in_testdateien([befund(datei, schwere, ebene)])
    assert f.schwere is erwartet
    assert ("Testdatei" in f.titel) is (erwartet is not schwere)


def test_referenced_test_file_is_raised_again(tmp_path: Path) -> None:
    files = {"SKILL.md": "Run `python tests/check.py` first.\n", "tests/check.py": "x = 1\n"}
    f = scan(tmp_path, files, [befund("tests/check.py", Schwere.K)])["tests/check.py"]
    assert f.schwere is Schwere.H and f.hochgestuft_von is Schwere.M
