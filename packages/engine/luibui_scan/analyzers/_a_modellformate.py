"""Analyzer A, part 6: Keras, TensorFlow and ONNX models (Prüfkatalog A17, A18; Scanner-Matrix
MOD-02, MOD-03; S4-11).

No model is ever loaded and no ML library is imported. Keras files are read as their JSON
configuration (``config.json`` inside a ``.keras`` ZIP; for HDF5 ``.h5`` the configuration string
is searched in the raw bytes, because HDF5 would need a parser of its own). TensorFlow graphs
(``.pb``) and ONNX models (``.onnx``) are protobuf; a small reader here walks only the fields it
needs, with hard limits on depth and number of fields, and skips tensor data by its length.

What runs or reads when a model is loaded:
- a Keras ``Lambda`` layer carries Python code that runs on loading (H),
- TensorFlow ops ``ReadFile``, ``WriteFile``, ``MatchingFiles`` and the ``PyFunc`` family read and
  write files or call Python (H),
- ONNX weights in ``external_data`` with an absolute path or ``..`` read files outside the
  package (H); operators from domains outside ONNX and ONNX Runtime need custom code (M).
"""

import json
import mmap
import re
import zipfile
from collections.abc import Iterator
from pathlib import PurePosixPath
from typing import Any

from luibui_scan.analyzers._common import finding, visible
from luibui_scan.context import InventoryEntry, ScanContext
from luibui_scan.models import Ebene, Finding, Schwere

MAX_KERAS_JSON = 10 * 1024 * 1024
MAX_H5_SUCHE = 64 * 1024 * 1024
MAX_FELDER = 2_000_000
MAX_TIEFE = 12

_TF_OPS = (
    b"ReadFile",
    b"WriteFile",
    b"MatchingFiles",
    b"PyFunc",
    b"PyFuncStateless",
    b"EagerPyFunc",
)
_TF_OP = re.compile(
    rb"\x12(?P<len>[\x06-\x0f])(?P<op>"
    + b"|".join(re.escape(o) for o in sorted(_TF_OPS, key=len, reverse=True))
    + rb")"
)
"""NodeDef field 2 (``op``): tag 0x12, one length byte, the op name of exactly that length."""
_H5_LAMBDA = re.compile(rb'"class_name"\s*:\s*"Lambda"')
_ONNX_DOMAINS = frozenset(
    {"", "ai.onnx", "ai.onnx.ml", "ai.onnx.training", "ai.onnx.preview.training", "com.microsoft",
     "com.microsoft.nchwc", "com.microsoft.experimental", "com.ms.internal.nhwc"}
)  # fmt: skip


class ProtobufError(Exception):
    pass


def _varint(buf: Any, pos: int, ende: int) -> tuple[int, int]:
    wert, shift = 0, 0
    while True:
        if pos >= ende or shift > 63:
            raise ProtobufError("Varint abgeschnitten")
        b = buf[pos]
        pos += 1
        wert |= (b & 0x7F) << shift
        if not b & 0x80:
            return wert, pos
        shift += 7


class Leser:
    """Walks protobuf fields with a shared budget, so a hostile file cannot make it run long."""

    def __init__(self, buf: Any) -> None:
        self.buf = buf
        self.rest = MAX_FELDER

    def felder(self, start: int, ende: int) -> Iterator[tuple[int, int, int, int]]:
        """``(field, wiretype, value_start, value_end)``; varints as ``(f, 0, value, -1)``."""
        pos = start
        while pos < ende:
            self.rest -= 1
            if self.rest < 0:
                raise ProtobufError("zu viele Felder")
            schluessel, pos = _varint(self.buf, pos, ende)
            feld, typ = schluessel >> 3, schluessel & 7
            if typ == 0:
                wert, pos = _varint(self.buf, pos, ende)
                yield feld, 0, wert, -1
            elif typ == 1:
                pos += 8
            elif typ == 2:
                laenge, pos = _varint(self.buf, pos, ende)
                if pos + laenge > ende:
                    raise ProtobufError("Feld reicht über das Ende")
                yield feld, 2, pos, pos + laenge
                pos += laenge
            elif typ == 5:
                pos += 4
            else:
                raise ProtobufError(f"Werttyp {typ}")
            if pos > ende:
                raise ProtobufError("Datei endet mitten im Feld")

    def text(self, a: int, e: int) -> str:
        return bytes(self.buf[a : min(e, a + 1024)]).decode("utf-8", errors="replace")


def _onnx_tensor(lr: Leser, a: int, e: int, orte: list[str]) -> None:
    for f, t, va, ve in lr.felder(a, e):
        if f == 13 and t == 2:  # external_data: StringStringEntryProto
            schluessel = wert = ""
            for f2, t2, a2, e2 in lr.felder(va, ve):
                if t2 == 2 and f2 == 1:
                    schluessel = lr.text(a2, e2)
                elif t2 == 2 and f2 == 2:
                    wert = lr.text(a2, e2)
            if schluessel == "location":
                orte.append(wert)


def _onnx_graph(lr: Leser, a: int, e: int, tiefe: int, orte: list[str], domains: set[str]) -> None:
    if tiefe > MAX_TIEFE:
        raise ProtobufError("zu tief verschachtelt")
    for f, t, va, ve in lr.felder(a, e):
        if t != 2:
            continue
        if f == 1:  # NodeProto
            for f2, t2, a2, e2 in lr.felder(va, ve):
                if f2 == 7 and t2 == 2:
                    domains.add(lr.text(a2, e2))
                elif f2 == 5 and t2 == 2:  # AttributeProto: subgraphs in g (6) and graphs (11)
                    for f3, t3, a3, e3 in lr.felder(a2, e2):
                        if f3 in (6, 11) and t3 == 2:
                            _onnx_graph(lr, a3, e3, tiefe + 1, orte, domains)
                        elif f3 in (5, 10) and t3 == 2:  # t (TensorProto), tensors
                            _onnx_tensor(lr, a3, e3, orte)
        elif f == 5:  # initializer
            _onnx_tensor(lr, va, ve, orte)
        elif f == 15:  # sparse_initializer: values (1) and indices (2) are TensorProtos
            for f2, t2, a2, e2 in lr.felder(va, ve):
                if f2 in (1, 2) and t2 == 2:
                    _onnx_tensor(lr, a2, e2, orte)


def onnx_lesen(buf: Any) -> tuple[list[str], set[str]]:
    """External data locations and operator domains of an ONNX ModelProto."""
    lr = Leser(buf)
    orte: list[str] = []
    domains: set[str] = set()
    graphen = 0
    for f, t, va, ve in lr.felder(0, len(buf)):
        if f == 7 and t == 2:
            graphen += 1
            _onnx_graph(lr, va, ve, 0, orte, domains)
        elif f == 8 and t == 2:  # opset_import
            for f2, t2, a2, e2 in lr.felder(va, ve):
                if f2 == 1 and t2 == 2:
                    domains.add(lr.text(a2, e2))
        elif f == 25 and t == 2:  # functions: their nodes are graph-like (field 7 holds nodes)
            for f2, t2, a2, e2 in lr.felder(va, ve):
                if f2 == 7 and t2 == 2:
                    for f3, t3, a3, e3 in lr.felder(a2, e2):
                        if f3 == 7 and t3 == 2:
                            domains.add(lr.text(a3, e3))
    if not graphen:
        raise ProtobufError("kein Graph gefunden")
    return orte, domains


def _gefaehrlicher_ort(ort: str) -> bool:
    if ort.startswith(("/", "\\", "~")) or re.match(r"^[A-Za-z]:", ort) or "\x00" in ort:
        return True
    return ".." in re.split(r"[\\/]", ort)


def _keras_lambdas(knoten: Any, tiefe: int = 0) -> int:
    if tiefe > 50:
        return 0
    if isinstance(knoten, dict):
        eigen = 1 if knoten.get("class_name") == "Lambda" else 0
        return eigen + sum(_keras_lambdas(v, tiefe + 1) for v in knoten.values())
    if isinstance(knoten, list):
        return sum(_keras_lambdas(v, tiefe + 1) for v in knoten)
    return 0


def _endung(entry: InventoryEntry) -> str:
    return PurePosixPath(entry.path).suffix.lower()


def _lambda_befund(entry: InventoryEntry, anzahl: int) -> Finding:
    return finding(
        rule_id="LB-A17-keras-lambda",
        ebene=Ebene.A,
        schwere=Schwere.H,
        titel="Keras-Modell enthält Lambda-Layer",
        erklaerung=(
            "Ein Lambda-Layer speichert Python-Code im Modell. Er läuft, sobald jemand das Modell "
            "lädt, mit allen Rechten des ladenden Programms. Wo er herkommt, lässt sich ohne "
            "Ausführen nicht prüfen."
        ),
        datei=entry.path,
        zeile=None,
        beleg=f"{anzahl} Lambda-Layer in der Modellkonfiguration",
        fix=(
            "Den Lambda-Layer durch einen registrierten eigenen Layer im Quellcode ersetzen oder "
            "das Modell nur mit `safe_mode=True` laden lassen."
        ),
        fix_prompt=f"Ersetze die Lambda-Layer in {entry.path} durch eigene Layer-Klassen.",
        normbezug=("OWASP-ASI05", "OWASP-LLM03"),
    )


def _a17_keras(ctx: ScanContext) -> Iterator[Finding]:
    for entry in ctx.inventory:
        ext = _endung(entry)
        anzahl = 0
        if ext == ".keras" and entry.kind == "zip":
            try:
                with zipfile.ZipFile(ctx.resolve(entry.path)) as zf:
                    info = zf.getinfo("config.json")
                    if info.file_size > MAX_KERAS_JSON:
                        continue
                    anzahl = _keras_lambdas(json.loads(zf.read(info)))
            except (KeyError, ValueError, zipfile.BadZipFile, OSError):
                continue
        elif entry.kind == "hdf5" or ext in (".h5", ".hdf5"):
            with ctx.resolve(entry.path).open("rb") as f:
                anzahl = len(_H5_LAMBDA.findall(f.read(MAX_H5_SUCHE)))
        if anzahl:
            yield _lambda_befund(entry, anzahl)


def _a17_tf(ctx: ScanContext) -> Iterator[Finding]:
    for entry in ctx.inventory:
        if _endung(entry) != ".pb" or entry.size == 0:
            continue
        with (
            ctx.resolve(entry.path).open("rb") as f,
            mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as buf,
        ):
            ops = sorted(
                {
                    m.group("op").decode()
                    for m in _TF_OP.finditer(buf)
                    if int.from_bytes(m.group("len"), "big") == len(m.group("op"))
                }
            )
        if not ops:
            continue
        yield finding(
            rule_id="LB-A17-tf-dateioperation",
            ebene=Ebene.A,
            schwere=Schwere.H,
            titel="TensorFlow-Graph liest oder schreibt Dateien oder ruft Python auf",
            erklaerung=(
                "Der Graph enthält Operationen, die beim Ausführen des Modells Dateien lesen oder "
                "schreiben oder Python-Code aufrufen. Ein Modell, das Daten verarbeiten soll, "
                "braucht das normalerweise nicht."
            ),
            datei=entry.path,
            zeile=None,
            beleg=visible("Operationen: " + ", ".join(ops)),
            fix="Die Operationen aus dem Graphen entfernen und das Modell neu exportieren.",
            fix_prompt=f"Entferne {', '.join(ops)} aus dem Graphen in {entry.path}.",
            normbezug=("OWASP-ASI05", "OWASP-LLM03"),
        )


def _a17_onnx(ctx: ScanContext) -> Iterator[Finding]:
    for entry in ctx.inventory:
        if _endung(entry) != ".onnx" or entry.size == 0:
            continue
        try:
            with (
                ctx.resolve(entry.path).open("rb") as f,
                mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as buf,
            ):
                orte, domains = onnx_lesen(buf)
        except ProtobufError as exc:
            yield finding(
                rule_id="LB-A18-modell-unklar",
                ebene=Ebene.A,
                schwere=Schwere.M,
                titel="ONNX-Modelldatei ist nicht lesbar",
                erklaerung=(
                    f"Die Struktur ließ sich nicht prüfen: {exc}. Externe Gewichte und eigene "
                    "Operatoren sind so nicht geprüft."
                ),
                datei=entry.path,
                zeile=None,
                beleg=f"{entry.size} Byte",
                fix="Die Datei neu aus dem Originalmodell exportieren.",
                fix_prompt=f"Exportiere {entry.path} neu aus dem Originalmodell.",
                normbezug=("OWASP-LLM03",),
            )
            continue
        aussen = sorted({o for o in orte if _gefaehrlicher_ort(o)})
        if aussen:
            yield finding(
                rule_id="LB-A17-onnx-externer-pfad",
                ebene=Ebene.A,
                schwere=Schwere.H,
                titel="ONNX-Modell lädt Gewichte von außerhalb des Pakets",
                erklaerung=(
                    "Gewichte stehen in externen Dateien mit absolutem Pfad oder mit „..“. Beim "
                    "Laden liest die Laufzeit diese Dateien, auch wenn sie außerhalb des Pakets "
                    "liegen, etwa Schlüssel oder Konfigurationen des Nutzers."
                ),
                datei=entry.path,
                zeile=None,
                beleg=visible("Pfade: " + ", ".join(aussen[:5])),
                fix="Externe Gewichte nur mit relativen Pfaden innerhalb des Pakets ablegen.",
                fix_prompt=f"Speichere die externen Gewichte von {entry.path} relativ im Paket.",
                normbezug=("OWASP-ASI02", "OWASP-LLM03"),
            )
        fremd = sorted(d for d in domains if d not in _ONNX_DOMAINS)
        if fremd:
            yield finding(
                rule_id="LB-A17-onnx-custom-op",
                ebene=Ebene.A,
                schwere=Schwere.M,
                titel="ONNX-Modell nutzt eigene Operatoren",
                erklaerung=(
                    "Das Modell verwendet Operatoren aus Domänen außerhalb von ONNX und ONNX "
                    "Runtime. Sie brauchen beim Laden eigenen, nativen Code, den das Paket oder "
                    "der Nutzer mitbringen muss; dieser Code ist hier nicht geprüft."
                ),
                datei=entry.path,
                zeile=None,
                beleg=visible("Domänen: " + ", ".join(fremd[:5])),
                fix=(
                    "Wenn möglich nur Standard-Operatoren verwenden oder den Code der Operatoren "
                    "offenlegen."
                ),
                fix_prompt=(
                    f"Ersetze die eigenen Operatoren in {entry.path} durch Standard-Operatoren."
                ),
                normbezug=("OWASP-ASI04", "OWASP-LLM03"),
            )
