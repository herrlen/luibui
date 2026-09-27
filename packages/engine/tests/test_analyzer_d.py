"""S1-9: dependencies (D01–D05). OSV runs against a tiny database built here, never downloaded."""

import json
import os
import shutil
import zipfile
from pathlib import Path

import pytest

from luibui_scan.analyzers import AnalyzerRegistry
from luibui_scan.analyzers.d_abhaengigkeiten import (
    AbhaengigkeitenAnalyzer,
    OsvAnalyzer,
    distance,
    lookalike,
)
from luibui_scan.context import ScanContext
from luibui_scan.inventory import build_inventory
from luibui_scan.models import Finding, Pruefumfang, ScanArt
from luibui_scan.pipeline import run_pipeline


def ctx_for(
    root: Path, files: dict[str, str], umfang: Pruefumfang = Pruefumfang.PAKET
) -> ScanContext:
    for rel, content in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(content)
    return ScanContext(
        root=root,
        scan_art=ScanArt.INTENSIV,
        pruefumfang=umfang,
        inventory=build_inventory(root).entries,
    )


def deps(tmp_path: Path, files: dict[str, str]) -> list[Finding]:
    return AbhaengigkeitenAnalyzer().analyze(ctx_for(tmp_path, files))


def rules(findings: list[Finding]) -> list[str]:
    return sorted(f.rule_id for f in findings)


# --- D03 -------------------------------------------------------------------------------------


def test_distance() -> None:
    assert distance("requests", "reqeusts") == 1  # swapped neighbours
    assert distance("numpy", "numpi") == 1
    assert distance("flask", "django") > 2


@pytest.mark.parametrize(
    ("name", "target"),
    [
        ("reqeusts", "requests"),
        ("numpi", "numpy"),
        ("pandsa", "pandas"),
        ("beautifulsoup5", "beautifulsoup4"),
    ],
)
def test_lookalike(name: str, target: str) -> None:
    from luibui_scan.analyzers.a_dateien import rules_dir
    from luibui_scan.analyzers.d_abhaengigkeiten import popular

    assert lookalike(name, popular("pypi", rules_dir())) == target


def test_d03_in_requirements_and_package_json(tmp_path: Path) -> None:
    files = {
        "requirements.txt": "reqeusts==2.0\nnumpy==2.1\n",
        "package.json": json.dumps({"dependencies": {"lodahs": "4.17.21", "express": "4.19.0"}}),
        "package-lock.json": "{}",
    }
    found = [f for f in deps(tmp_path, files) if f.rule_id == "LB-D03-namensverwechslung"]
    assert sorted(f.titel for f in found) == [
        "Paketname ähnelt „lodash“",
        "Paketname ähnelt „requests“",
    ]
    assert all(f.schwere.value == "H" for f in found)


def test_d03_negative(tmp_path: Path) -> None:
    files = {"requirements.txt": "requests==2.32\nmy-own-weather-lib==1.0\nhttpx2==2.5\n"}
    assert "LB-D03-namensverwechslung" not in rules(deps(tmp_path, files))


# --- D04 -------------------------------------------------------------------------------------


def test_d04(tmp_path: Path) -> None:
    pkg = json.dumps({"dependencies": {"zod": "^3.0.0"}})
    assert "LB-D04-kein-lockfile" in rules(deps(tmp_path / "a", {"package.json": pkg}))
    assert "LB-D04-kein-lockfile" not in rules(
        deps(tmp_path / "b", {"package.json": pkg, "pnpm-lock.yaml": "x"})
    )
    assert "LB-D04-kein-lockfile" in rules(
        deps(tmp_path / "c", {"requirements.txt": "httpx>=0.27\n"})
    )
    assert "LB-D04-kein-lockfile" not in rules(
        deps(tmp_path / "d", {"requirements.txt": "httpx==0.27.2\n"})
    )
    pyproject = '[project]\nname = "x"\ndependencies = ["httpx>=0.27"]\n'
    assert "LB-D04-kein-lockfile" not in rules(
        deps(tmp_path / "e", {"pyproject.toml": pyproject, "uv.lock": "x"})
    )
    assert (
        rules(deps(tmp_path / "f", {"package.json": json.dumps({"name": "ohne-abhaengigkeiten"})}))
        == []
    )


# --- D05 -------------------------------------------------------------------------------------

SHA = "a" * 40


@pytest.mark.parametrize(
    "files",
    [
        {"package.json": json.dumps({"dependencies": {"x": "github:someone/x"}})},
        {"package.json": json.dumps({"dependencies": {"x": "git+https://example.invalid/x.git"}})},
        {"package.json": json.dumps({"dependencies": {"x": "file:../../outside"}})},
        {"package.json": json.dumps({"dependencies": {"x": "http://example.invalid/x.tgz"}})},
        {"requirements.txt": "x @ git+https://example.invalid/x.git\n"},
        {"requirements.txt": "x @ http://example.invalid/x.whl\n"},
    ],
)
def test_d05_positive(tmp_path: Path, files: dict[str, str]) -> None:
    assert "LB-D05-unsichere-quelle" in rules(deps(tmp_path, files))


@pytest.mark.parametrize(
    "files",
    [
        {
            "package.json": json.dumps(
                {"dependencies": {"x": f"git+https://example.invalid/x.git#{SHA}"}}
            )
        },
        {"package.json": json.dumps({"dependencies": {"x": "file:./packages/x", "zod": "^3.0.0"}})},
        {"package.json": json.dumps({"dependencies": {"@scope/x": "1.2.3"}})},
        {"requirements.txt": f"x @ git+https://example.invalid/x.git@{SHA}\n"},
        {"requirements.txt": "httpx==0.27.2\n"},
    ],
)
def test_d05_negative(tmp_path: Path, files: dict[str, str]) -> None:
    assert "LB-D05-unsichere-quelle" not in rules(deps(tmp_path, files))


def test_single_file_scope_is_skipped(tmp_path: Path) -> None:
    reg = AnalyzerRegistry()
    reg.add(AbhaengigkeitenAnalyzer())
    ctx = ctx_for(tmp_path, {"requirements.txt": "reqeusts\n"}, Pruefumfang.EINZELDATEI)
    result = run_pipeline(ctx, reg)
    assert result.findings == [] and [s.analyzer for s in result.skipped] == ["d_abhaengigkeiten"]


# --- D01, D02 via OSV ------------------------------------------------------------------------

osv_missing = not (os.environ.get("LUIBUI_OSV_SCANNER") or shutil.which("osv-scanner"))


def fake_db(root: Path) -> Path:
    advisories = [
        {
            "schema_version": "1.6.0",
            "id": "MAL-2026-9999",
            "modified": "2026-09-01T00:00:00Z",
            "summary": "LUIBUI-TESTFIXTURE",
            "affected": [
                {
                    "package": {"ecosystem": "PyPI", "name": "luibui-testfixture-boese"},
                    "versions": ["1.0.0"],
                }
            ],
        },
        {
            "schema_version": "1.6.0",
            "id": "GHSA-test-0000-0001",
            "aliases": ["CVE-2026-99999"],
            "modified": "2026-09-01T00:00:00Z",
            "summary": "LUIBUI-TESTFIXTURE",
            "severity": [
                {"type": "CVSS_V3", "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"}
            ],
            "affected": [
                {
                    "package": {"ecosystem": "PyPI", "name": "luibui-testfixture-alt"},
                    "ranges": [
                        {"type": "ECOSYSTEM", "events": [{"introduced": "0"}, {"fixed": "2.0.0"}]}
                    ],
                }
            ],
        },
    ]
    target = root / "osv-scalibr" / "PyPI"
    target.mkdir(parents=True)
    with zipfile.ZipFile(target / "all.zip", "w") as zf:
        for adv in advisories:
            zf.writestr(f"{adv['id']}.json", json.dumps(adv))
    return root


@pytest.mark.skipif(osv_missing, reason="osv-scanner nicht installiert (CI installiert es)")
def test_osv_malicious_package_locks_and_vulnerability_is_rated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LUIBUI_OSV_DB", str(fake_db(tmp_path / "db")))
    files = {
        "requirements.txt": (
            "luibui-testfixture-boese==1.0.0\nluibui-testfixture-alt==1.5.0\nrequests==2.32.3\n"
        )
    }
    found = {f.rule_id: f for f in OsvAnalyzer().analyze(ctx_for(tmp_path / "pkg", files))}
    assert set(found) == {"osv:MAL-2026-9999", "osv:GHSA-test-0000-0001"}
    assert found["osv:MAL-2026-9999"].schwere.value == "K"
    assert found["osv:GHSA-test-0000-0001"].schwere.value == "H"  # CVSS 9.8
    assert found["osv:GHSA-test-0000-0001"].datei == "requirements.txt"
    assert "osv.dev/GHSA-test-0000-0001" in found["osv:GHSA-test-0000-0001"].erklaerung


@pytest.mark.skipif(osv_missing, reason="osv-scanner nicht installiert (CI installiert es)")
def test_osv_without_dependencies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUIBUI_OSV_DB", str(fake_db(tmp_path / "db")))
    assert OsvAnalyzer().analyze(ctx_for(tmp_path / "pkg", {"SKILL.md": "# x"})) == []


def test_missing_database_fails_the_analyzer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LUIBUI_OSV_DB", str(tmp_path / "leer"))
    reg = AnalyzerRegistry()
    reg.add(OsvAnalyzer())
    result = run_pipeline(
        ctx_for(tmp_path / "pkg", {"requirements.txt": "requests==2.32.3\n"}), reg
    )
    assert [f.analyzer for f in result.failed] == ["d_osv"]


@pytest.mark.skipif(osv_missing, reason="osv-scanner nicht installiert (CI installiert es)")
def test_osv_aliases_become_one_finding(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """PYSEC and GHSA entries for the same flaw (seen with pillow in anthropics/skills)."""
    db = tmp_path / "db" / "osv-scalibr" / "PyPI"
    db.mkdir(parents=True)
    affected = [
        {"package": {"ecosystem": "PyPI", "name": "luibui-testfixture-alt"}, "versions": ["1.0.0"]}
    ]
    pair = [
        {
            "id": "PYSEC-2026-1",
            "aliases": ["GHSA-aaaa-bbbb-cccc"],
            "modified": "2026-09-01T00:00:00Z",
            "affected": affected,
        },
        {
            "id": "GHSA-aaaa-bbbb-cccc",
            "aliases": ["PYSEC-2026-1"],
            "modified": "2026-09-01T00:00:00Z",
            "affected": affected,
        },
    ]
    with zipfile.ZipFile(db / "all.zip", "w") as zf:
        for adv in pair:
            zf.writestr(f"{adv['id']}.json", json.dumps(adv))
    monkeypatch.setenv("LUIBUI_OSV_DB", str(tmp_path / "db"))
    found = OsvAnalyzer().analyze(
        ctx_for(tmp_path / "pkg", {"requirements.txt": "luibui-testfixture-alt==1.0.0\n"})
    )
    assert [f.rule_id for f in found] == ["osv:GHSA-aaaa-bbbb-cccc"]
    assert "PYSEC-2026-1" in (found[0].beleg or "")
