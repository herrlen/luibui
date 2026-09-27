"""Scanner-Matrix DEP-01, DEP-03, DEP-04, AGT-10, SEC-01."""

from pathlib import Path

import pytest

from luibui_scan.analyzers.a_dateien import DateienAnalyzer
from luibui_scan.analyzers.d_abhaengigkeiten import AbhaengigkeitenAnalyzer, dependencies
from luibui_scan.analyzers.secrets import key_files
from luibui_scan.context import ScanContext
from luibui_scan.inventory import build_inventory
from luibui_scan.models import Finding, Pruefumfang, ScanArt, Schwere
from luibui_scan.scoring import is_blocklisted


def ctx_for(root: Path, files: dict[str, str | bytes]) -> ScanContext:
    for rel, content in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        data = content.encode() if isinstance(content, str) else content
        (root / rel).write_bytes(data)
    return ScanContext(
        root=root,
        scan_art=ScanArt.INTENSIV,
        pruefumfang=Pruefumfang.PAKET,
        inventory=build_inventory(root).entries,
    )


def rules(findings: list[Finding]) -> list[str]:
    return sorted(f.rule_id for f in findings)


# --- DEP-01 ----------------------------------------------------------------------------------


def test_setup_cfg_and_pipfile_are_read(tmp_path: Path) -> None:
    cfg = (
        "[options]\ninstall_requires =\n    reqeusts>=2\n    click\n"
        "[options.extras_require]\ndev = pytest\n"
    )
    pipfile = '[packages]\nnumpy = "*"\nflask = {version = "==3.0"}\n[dev-packages]\nruff = "*"\n'
    found = dependencies(ctx_for(tmp_path, {"setup.cfg": cfg, "Pipfile": pipfile}))
    assert {d.name for d in found} == {"reqeusts", "click", "pytest", "numpy", "flask", "ruff"}


def test_typo_in_setup_cfg_is_reported(tmp_path: Path) -> None:
    cfg = "[options]\ninstall_requires =\n    reqeusts\n"
    found = AbhaengigkeitenAnalyzer().analyze(ctx_for(tmp_path, {"setup.cfg": cfg}))
    assert "LB-D03-namensverwechslung" in rules(found)
    assert "LB-D04-kein-lockfile" in rules(found)


def test_pipfile_with_lock_has_no_d04(tmp_path: Path) -> None:
    found = AbhaengigkeitenAnalyzer().analyze(
        ctx_for(tmp_path, {"Pipfile": '[packages]\nclick = "*"\n', "Pipfile.lock": "{}"})
    )
    assert "LB-D04-kein-lockfile" not in rules(found)


def test_broken_setup_cfg(tmp_path: Path) -> None:
    assert dependencies(ctx_for(tmp_path, {"setup.cfg": "kein [ini"})) == []


# --- DEP-04 ----------------------------------------------------------------------------------


def test_direct_url_without_hash(tmp_path: Path) -> None:
    req = "paket @ https://files.example/paket-1.0.tar.gz\n"
    found = AbhaengigkeitenAnalyzer().analyze(ctx_for(tmp_path, {"requirements.txt": req}))
    assert "LB-D05-unsichere-quelle" in rules(found)


def test_direct_url_with_hash(tmp_path: Path) -> None:
    req = "paket @ https://files.example/paket-1.0.tar.gz#sha256=" + "a" * 64 + "\n"
    found = AbhaengigkeitenAnalyzer().analyze(ctx_for(tmp_path, {"requirements.txt": req}))
    assert "LB-D05-unsichere-quelle" not in rules(found)


# --- AGT-10 ----------------------------------------------------------------------------------

WEBUI = '''"""
title: Wetter
author: x
requirements: reqeusts, beautifulsoup4==4.12
"""

class Tools:
    pass
'''


def test_open_webui_requirements(tmp_path: Path) -> None:
    found = dependencies(ctx_for(tmp_path, {"wetter.py": WEBUI}))
    assert [(d.name, d.spec, d.zeile) for d in found] == [
        ("reqeusts", "", 4),
        ("beautifulsoup4", "==4.12", 4),
    ]


def test_plain_docstring_has_no_requirements(tmp_path: Path) -> None:
    code = '"""Ein Modul.\n\nrequirements werden hier nicht genannt.\n"""\nx = 1\n'
    assert dependencies(ctx_for(tmp_path, {"modul.py": code})) == []


# --- DEP-03 ----------------------------------------------------------------------------------


def test_uv_toml_foreign_index(tmp_path: Path) -> None:
    toml = '[[index]]\nname = "intern"\nurl = "https://pypi.intern.example/simple"\n'
    found = DateienAnalyzer().analyze(ctx_for(tmp_path, {"uv.toml": toml}))
    assert "LB-A12-fremde-paketquelle" in rules(found)


def test_uv_toml_official_index(tmp_path: Path) -> None:
    toml = '[[index]]\nurl = "https://pypi.org/simple"\n'
    found = DateienAnalyzer().analyze(ctx_for(tmp_path, {"uv.toml": toml}))
    assert "LB-A12-fremde-paketquelle" not in rules(found)


# --- SEC-01 ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["id_rsa", "keys/id_ed25519", "cert.p12", "store.jks", "passwords.kdbx", ".aws/credentials"],
)
def test_key_files_are_critical_and_lock(tmp_path: Path, name: str) -> None:
    (found,) = key_files(ctx_for(tmp_path, {name: b"\x30\x82\x01\x00geheim"}))
    assert found.schwere is Schwere.K
    assert is_blocklisted(found)
    assert "geheim" not in (found.beleg or "")


def test_key_file_in_tests_is_medium(tmp_path: Path) -> None:
    (found,) = key_files(ctx_for(tmp_path, {"tests/fixtures/client.pfx": b"\x30\x82"}))
    assert found.schwere is Schwere.M


@pytest.mark.parametrize("name", ["id_rsa.pub", "README.md", "keystore.md", "empty.p12"])
def test_no_key_files(tmp_path: Path, name: str) -> None:
    content = b"" if name == "empty.p12" else b"ssh-ed25519 AAAA"
    assert key_files(ctx_for(tmp_path, {name: content})) == []
