"""Scanner-Matrix MOD-01, MOD-06, MOD-07 (Prüfkatalog A16, A18, A19). Pickle data is only built
as bytes and never loaded; the "dangerous" import is the harmless corpus/_dummy.py module, marked
dangerous for the test (CLAUDE.md rule 8)."""

import io
import json
import zipfile
from pathlib import Path

import pytest

from luibui_scan.analyzers import _a_modelle
from luibui_scan.analyzers.a_dateien import DateienAnalyzer
from luibui_scan.context import ScanContext
from luibui_scan.inventory import build_inventory
from luibui_scan.models import Finding, Pruefumfang, ScanArt, Schwere
from luibui_scan.scoring import is_blocklisted

DUMMY = "_dummy"


@pytest.fixture(autouse=True)
def dummy_is_dangerous(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_a_modelle, "_DANGEROUS_MODULES", _a_modelle._DANGEROUS_MODULES | {DUMMY})


def global_pickle(module: str, name: str, protocol: int = 2) -> bytes:
    """GLOBAL (protocol 2) or STACK_GLOBAL (protocol 4), then an empty call: never loaded."""
    if protocol == 2:
        return b"\x80\x02c" + f"{module}\n{name}\n".encode() + b")R."
    body = (
        b"\x8c" + bytes([len(module)]) + module.encode()
        + b"\x8c" + bytes([len(name)]) + name.encode()
        + b"\x93)R."
    )  # fmt: skip
    return b"\x80\x04\x95" + len(body).to_bytes(8, "little") + body


def analyze(root: Path, files: dict[str, bytes | str]) -> list[Finding]:
    for rel, content in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(content.encode() if isinstance(content, str) else content)
    ctx = ScanContext(
        root=root,
        scan_art=ScanArt.INTENSIV,
        pruefumfang=Pruefumfang.PAKET,
        inventory=build_inventory(root).entries,
    )
    return DateienAnalyzer().analyze(ctx)


def by_rule(findings: list[Finding], rule: str) -> Finding | None:
    return next((f for f in findings if f.rule_id == rule), None)


# --- MOD-01 ----------------------------------------------------------------------------------


@pytest.mark.parametrize("protocol", [2, 4])
def test_pickle_with_dangerous_import_locks(tmp_path: Path, protocol: int) -> None:
    found = analyze(tmp_path, {"model.pkl": global_pickle(DUMMY, "harmlos", protocol)})
    f = by_rule(found, "LB-A16-pickle-code")
    assert f is not None and f.schwere is Schwere.K and is_blocklisted(f)
    assert "_dummy.harmlos" in (f.beleg or "")


def test_torch_checkpoint_zip_is_read_in_memory(tmp_path: Path) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("archive/data.pkl", global_pickle(DUMMY, "harmlos"))
        zf.writestr("archive/version", "3\n")
    found = analyze(tmp_path, {"weights.pt": buf.getvalue()})
    assert by_rule(found, "LB-A16-pickle-code") is not None
    assert by_rule(found, "LB-A07-archiv-im-paket") is None
    assert not (tmp_path / "archive").exists()


def test_known_model_classes_pass(tmp_path: Path) -> None:
    data = global_pickle("collections", "OrderedDict")
    assert analyze(tmp_path, {"state.pkl": data}) == []


def test_unknown_import_is_medium(tmp_path: Path) -> None:
    found = analyze(tmp_path, {"state.pkl": global_pickle("meinpaket.modell", "Klasse")})
    f = by_rule(found, "LB-A18-modell-unklar")
    assert f is not None and f.schwere is Schwere.M


def test_truncated_pickle_is_medium(tmp_path: Path) -> None:
    found = analyze(tmp_path, {"state.pkl": b"\x80\x02c" + b"collections\nOrd"})
    assert by_rule(found, "LB-A18-modell-unklar") is not None


def test_builtins_are_judged_by_name() -> None:
    assert _a_modelle._dangerous("builtins.eval")
    assert not _a_modelle._dangerous("builtins.set")


# --- MOD-06 ----------------------------------------------------------------------------------


def safetensors(header: dict[str, object], data: bytes = b"\0" * 8) -> bytes:
    raw = json.dumps(header).encode()
    return len(raw).to_bytes(8, "little") + raw + data


def test_valid_safetensors(tmp_path: Path) -> None:
    header = {
        "w": {"dtype": "F32", "shape": [2], "data_offsets": [0, 8]},
        "__metadata__": {"format": "pt"},
    }
    assert analyze(tmp_path, {"model.safetensors": safetensors(header)}) == []


@pytest.mark.parametrize(
    "header",
    [
        {"w": {"dtype": "F32", "shape": [2], "data_offsets": [0, 4096]}},
        {"w": {"dtype": "F32", "shape": [2], "data_offsets": [0, 8], "code": "x"}},
        {"__metadata__": {"a": {"b": 1}}},
    ],
)
def test_invalid_safetensors(tmp_path: Path, header: dict[str, object]) -> None:
    found = analyze(tmp_path, {"model.safetensors": safetensors(header)})
    assert by_rule(found, "LB-A18-modell-unklar") is not None


# --- MOD-07 ----------------------------------------------------------------------------------


def test_auto_map(tmp_path: Path) -> None:
    cfg = {"model_type": "x", "auto_map": {"AutoModel": "modeling_x.XModel"}}
    found = analyze(tmp_path, {"config.json": json.dumps(cfg)})
    assert by_rule(found, "LB-A19-remote-code") is not None


def test_chat_template_ssti_locks(tmp_path: Path) -> None:
    tpl = "{{ cycler.__init__.__globals__ }}{% for m in messages %}{{ m.content }}{% endfor %}"
    found = analyze(tmp_path, {"tokenizer_config.json": json.dumps({"chat_template": tpl})})
    f = by_rule(found, "LB-A16-template-code")
    assert f is not None and is_blocklisted(f)


def test_ordinary_config_and_template(tmp_path: Path) -> None:
    tpl = "{% for m in messages %}<|{{ m.role }}|>{{ m.content }}{% endfor %}"
    files = {
        "config.json": json.dumps({"model_type": "llama", "hidden_size": 8}),
        "tokenizer_config.json": json.dumps({"chat_template": tpl}),
    }
    assert analyze(tmp_path, files) == []
