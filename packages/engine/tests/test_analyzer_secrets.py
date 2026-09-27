"""S1-8: secrets via gitleaks (B20). The package can never silence gitleaks."""

import os
import secrets
import shutil
import string
from pathlib import Path

import pytest

from luibui_scan.analyzers import AnalyzerRegistry
from luibui_scan.analyzers.secrets import SecretsAnalyzer
from luibui_scan.context import ScanContext
from luibui_scan.inventory import build_inventory
from luibui_scan.models import Finding, Pruefumfang, ScanArt
from luibui_scan.pipeline import run_pipeline
from luibui_scan.tools import ToolError, gitleaks

pytestmark = pytest.mark.skipif(
    not (os.environ.get("LUIBUI_GITLEAKS") or shutil.which("gitleaks")),
    reason="gitleaks nicht installiert (CI installiert es; lokal LUIBUI_GITLEAKS setzen)",
)


def fake_token() -> str:
    """Random, never valid: has the shape of a GitHub token so the default rule matches."""
    alphabet = string.ascii_letters + string.digits
    return "ghp_" + "".join(secrets.choice(alphabet) for _ in range(36))


def scan(tmp_path: Path, files: dict[str, str]) -> list[Finding]:
    root = tmp_path / "pkg"
    for rel, content in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(content)
    inv = build_inventory(root)
    ctx = ScanContext(
        root=root, scan_art=ScanArt.INTENSIV, pruefumfang=Pruefumfang.PAKET, inventory=inv.entries
    )
    return SecretsAnalyzer().analyze(ctx)


def test_token_is_found_masked_and_locking(tmp_path: Path) -> None:
    token = fake_token()
    (f,) = scan(tmp_path, {"src/config.py": f'TOKEN = "{token}"\n'})
    assert f.rule_id.startswith("gitleaks:")
    assert f.schwere.value == "K"
    assert f.datei == "src/config.py" and f.zeile == 1
    assert token not in (f.beleg or "") and token[4:] not in f.model_dump_json()


def test_clean_package(tmp_path: Path) -> None:
    assert (
        scan(
            tmp_path, {"SKILL.md": "# Wetter\nNutze die API von example.invalid.", "a.py": "x = 1"}
        )
        == []
    )


def test_sample_paths_are_medium_not_critical(tmp_path: Path) -> None:
    """Placeholders in examples and tests (seen in modelcontextprotocol/python-sdk)."""
    (f,) = scan(tmp_path, {"examples/demo.py": f'TOKEN = "{fake_token()}"\n'})
    assert f.schwere.value == "M"


@pytest.mark.parametrize(
    "trick",
    [
        {".gitleaks.toml": 'title = "x"\n[allowlist]\npaths = [".*"]\n'},
        {".gitleaks.toml": 'title = "leer"\n[[rules]]\nid = "nichts"\nregex = "a^"\n'},
        {".gitleaksignore": "*\n"},
    ],
)
def test_package_cannot_configure_gitleaks(tmp_path: Path, trick: dict[str, str]) -> None:
    files = {"src/config.py": f'TOKEN = "{fake_token()}"\n', **trick}
    assert len(scan(tmp_path, files)) == 1


def test_inline_allow_comments_are_ignored(tmp_path: Path) -> None:
    files = {"src/config.py": f'TOKEN = "{fake_token()}"  # gitleaks:allow\n'}
    assert len(scan(tmp_path, files)) == 1


def test_missing_gitleaks_fails_the_analyzer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LUIBUI_GITLEAKS", "")
    monkeypatch.setattr(gitleaks.shutil, "which", lambda _: None)
    with pytest.raises(ToolError):
        gitleaks.binary()
    root = tmp_path / "pkg"
    root.mkdir()
    (root / "a.md").write_text("x")
    reg = AnalyzerRegistry()
    reg.add(SecretsAnalyzer())
    ctx = ScanContext(
        root=root,
        scan_art=ScanArt.LOKAL,
        pruefumfang=Pruefumfang.PAKET,
        inventory=build_inventory(root).entries,
    )
    result = run_pipeline(ctx, reg)
    assert [f.analyzer for f in result.failed] == ["secrets"]
