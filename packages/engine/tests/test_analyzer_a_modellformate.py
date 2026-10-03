"""S4-11 / A17: Keras Lambda layers, TensorFlow file and Python ops, ONNX external data and custom
operators. Every model here is a few hand-made bytes; nothing is ever loaded."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from luibui_scan.analyzers._a_modellformate import (
    ProtobufError,
    _a17_keras,
    _a17_onnx,
    _a17_tf,
    onnx_lesen,
)
from luibui_scan.context import ScanContext
from luibui_scan.inventory import build_inventory
from luibui_scan.models import Pruefumfang, ScanArt, Schwere


def _gen() -> ModuleType:
    """corpus/generate.py, loaded like test_corpus_matrix does (no sys.path changes)."""
    pfad = Path(__file__).resolve().parents[3] / "corpus" / "generate.py"
    spec = importlib.util.spec_from_file_location("corpus_generate_modelle", pfad)
    assert spec is not None and spec.loader is not None
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


GEN = _gen()
MARK, _keras, _onnx, _pb, _tf_graph = GEN.MARK, GEN._keras, GEN._onnx, GEN._pb, GEN._tf_graph


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


def regeln(findings: list) -> list[tuple[str, str]]:  # type: ignore[type-arg]
    return [(f.rule_id, f.schwere.value) for f in findings]


# --- Keras -------------------------------------------------------------------------------------


def test_keras_lambda_is_high_and_dense_is_fine(tmp_path: Path) -> None:
    ctx = ctx_for(tmp_path, {"a.keras": _keras("Lambda"), "b.keras": _keras("Dense")})
    [f] = list(_a17_keras(ctx))
    assert (f.rule_id, f.schwere, f.datei) == ("LB-A17-keras-lambda", Schwere.H, "a.keras")


def test_keras_lambda_in_hdf5_and_tf_op_lambda_is_not_lambda(tmp_path: Path) -> None:
    kopf = b"\x89HDF\r\n\x1a\n" + b"\x00" * 64
    h5 = kopf + b'{"class_name": "Sequential", "config": {"layers": [{"class_name": "Lambda"}]}}'
    tfop = kopf + b'{"class_name": "TFOpLambda"}'
    ctx = ctx_for(tmp_path, {"m.h5": h5, "ok.h5": tfop})
    assert [f.datei for f in _a17_keras(ctx)] == ["m.h5"]


# --- TensorFlow --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "op", ["ReadFile", "WriteFile", "MatchingFiles", "PyFunc", "PyFuncStateless", "EagerPyFunc"]
)
def test_tf_file_and_python_ops_are_high(tmp_path: Path, op: str) -> None:
    [f] = list(_a17_tf(ctx_for(tmp_path, {"saved_model.pb": _tf_graph(op)})))
    assert f.schwere is Schwere.H and f"Operationen: {op}" == f.beleg


def test_tf_ordinary_ops_and_names_that_only_contain_the_word(tmp_path: Path) -> None:
    graph = _tf_graph("MatMul") + _pb(1, _pb(1, b"ReadFile") + _pb(2, b"Const"))
    assert list(_a17_tf(ctx_for(tmp_path, {"g.pb": graph, "leer.pb": b""}))) == []


# --- ONNX --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ort", ["../ausserhalb/w.bin", "/etc/gewichte", "C:\\\\daten\\\\w.bin", "~/w.bin", "a/../../w"]
)
def test_onnx_external_data_outside_the_package_is_high(tmp_path: Path, ort: str) -> None:
    [f] = list(_a17_onnx(ctx_for(tmp_path, {"m.onnx": _onnx(ort)})))
    assert (f.rule_id, f.schwere) == ("LB-A17-onnx-externer-pfad", Schwere.H)


def test_onnx_relative_data_and_standard_domains_are_fine(tmp_path: Path) -> None:
    files = {"m.onnx": _onnx("gewichte/w.bin"), "n.onnx": _onnx("w.bin", "com.microsoft")}
    assert list(_a17_onnx(ctx_for(tmp_path, files))) == []


def test_onnx_custom_domain_is_medium(tmp_path: Path) -> None:
    [f] = list(_a17_onnx(ctx_for(tmp_path, {"m.onnx": _onnx("w.bin", "com.beispiel.eigen")})))
    assert (f.rule_id, f.schwere) == ("LB-A17-onnx-custom-op", Schwere.M)
    assert "com.beispiel.eigen" in (f.beleg or "")


def test_onnx_external_data_in_a_subgraph_is_found() -> None:
    tensor = _pb(8, b"t") + _pb(13, _pb(1, b"location") + _pb(2, b"../x"))
    unter = _pb(5, tensor)
    attribut = _pb(1, b"then_branch") + _pb(6, unter)
    knoten = _pb(4, b"If") + _pb(5, attribut)
    modell = _pb(6, MARK.encode()) + _pb(7, _pb(1, knoten))
    orte, _ = onnx_lesen(modell)
    assert orte == ["../x"]


@pytest.mark.parametrize(
    "kaputt",
    [
        _pb(6, b"nur Text, kein Graph"),
        _onnx("w.bin")[:-3],
        b"\x3a\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff",  # endless varint length
        b"\x3f",  # unknown wire type 7
    ],
)
def test_unreadable_onnx_is_a18(tmp_path: Path, kaputt: bytes) -> None:
    with pytest.raises(ProtobufError):
        onnx_lesen(kaputt)
    [f] = list(_a17_onnx(ctx_for(tmp_path, {"m.onnx": kaputt})))
    assert (f.rule_id, f.schwere) == ("LB-A18-modell-unklar", Schwere.M)


def test_deeply_nested_subgraphs_stop(tmp_path: Path) -> None:
    graph = b""
    for _ in range(30):
        graph = _pb(1, _pb(5, _pb(6, graph)))
    with pytest.raises(ProtobufError, match="tief"):
        onnx_lesen(_pb(7, graph))


def test_corpus_rows_mod02_and_mod03(tmp_path: Path) -> None:
    boese, gut = GEN.fixtures()
    for zeile in ("MOD-02", "MOD-03"):
        dateien, erwartet = boese[zeile]
        ctx = ctx_for(tmp_path / zeile, dateien)
        gefunden = [f.rule_id for f in [*_a17_keras(ctx), *_a17_tf(ctx), *_a17_onnx(ctx)]]
        assert erwartet in gefunden, zeile
        ctx_gut = ctx_for(tmp_path / f"{zeile}-gut", gut[zeile])
        assert [*_a17_keras(ctx_gut), *_a17_tf(ctx_gut), *_a17_onnx(ctx_gut)] == [], zeile
