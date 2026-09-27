"""Analyzer A, part 4: model files (Prüfkatalog A16, A18, A19; Scanner-Matrix MOD-01, MOD-06,
MOD-07).

Pickle files are never loaded. ``pickletools.genops`` only walks the opcode stream and returns the
imports a load would perform; nothing is resolved, imported or called. PyTorch checkpoints are ZIP
files whose ``data.pkl`` is read into memory with a size limit, not unpacked to disk.
"""

import json
import pickletools
import re
import zipfile
from collections.abc import Iterator
from pathlib import PurePosixPath

from luibui_scan.analyzers._common import file_name, finding, read_bytes, read_json, visible
from luibui_scan.context import InventoryEntry, ScanContext
from luibui_scan.models import Ebene, Finding, Schwere

MAX_PICKLE = 10 * 1024 * 1024
_PICKLE_EXT = frozenset(
    {".pkl", ".pickle", ".joblib", ".pt", ".pth", ".bin", ".ckpt", ".dat", ".sav", ".model"}
)
_DANGEROUS_MODULES = frozenset(
    {
        "os", "posix", "nt", "subprocess", "socket", "runpy", "shutil", "sys", "pty",
        "commands", "webbrowser", "importlib", "pickle", "_pickle", "marshal", "ctypes",
        "requests", "urllib", "urllib.request", "http.client", "httpx", "code", "codeop",
        "multiprocessing", "asyncio", "pdb", "timeit", "profile", "cProfile", "signal",
    }
)  # fmt: skip
_DANGEROUS_BUILTINS = frozenset(
    {"eval", "exec", "compile", "open", "getattr", "setattr", "__import__", "globals", "breakpoint",
     "input", "delattr", "vars", "locals", "apply", "execfile"}
)  # fmt: skip
_SAFE_PREFIXES = (
    "collections.",
    "torch.",
    "numpy.",
    "_codecs.encode",
    "builtins.set",
    "builtins.frozenset",
    "builtins.slice",
    "builtins.bytearray",
    "builtins.complex",
    "builtins.range",
    "sklearn.",
    "scipy.",
    "pandas.",
    "datetime.",
    "decimal.Decimal",
    "copy_reg._reconstructor",
    "copyreg._reconstructor",
    "__builtin__.set",
    "joblib.numpy_pickle.",
    "xgboost.",
    "lightgbm.",
    "transformers.",
    "tokenizers.",
    "pathlib.",
)
_STRING_OPS = frozenset(
    {"SHORT_BINUNICODE", "BINUNICODE", "BINUNICODE8", "UNICODE", "SHORT_BINSTRING", "BINSTRING",
     "STRING"}
)  # fmt: skip


def pickle_globals(data: bytes) -> tuple[list[str], bool]:
    """Imports a load of ``data`` would perform, and whether the stream was readable to its end."""
    found: list[str] = []
    strings: list[str] = []
    try:
        for opcode, arg, _ in pickletools.genops(data):
            if opcode.name in _STRING_OPS and isinstance(arg, str | bytes):
                strings.append(arg if isinstance(arg, str) else arg.decode("latin-1"))
                strings = strings[-2:]
            elif opcode.name in ("GLOBAL", "INST") and isinstance(arg, str):
                found.append(arg.replace(" ", ".", 1))
            elif opcode.name == "STACK_GLOBAL" and len(strings) == 2:
                found.append(f"{strings[0]}.{strings[1]}")
    except (ValueError, EOFError, KeyError, IndexError, TypeError, UnicodeDecodeError):
        return found, False
    return found, True


def _dangerous(name: str) -> bool:
    module, _, attr = name.rpartition(".")
    if module in ("builtins", "__builtin__", "__builtins__"):
        return attr in _DANGEROUS_BUILTINS
    root = module.split(".")[0]
    return module in _DANGEROUS_MODULES or root in _DANGEROUS_MODULES


def _pickles(ctx: ScanContext, entry: InventoryEntry) -> Iterator[tuple[str, bytes]]:
    """(label, bytes) of every pickle stream in the file."""
    ext = PurePosixPath(entry.path).suffix.lower()
    if entry.kind == "pickle" or (ext in _PICKLE_EXT and entry.kind in ("text", "binary")):
        yield entry.path, read_bytes(ctx, entry, MAX_PICKLE)
    elif entry.kind == "zip" and ext in _PICKLE_EXT:
        try:
            with zipfile.ZipFile(ctx.resolve(entry.path)) as zf:
                for info in zf.infolist():
                    if info.filename.endswith(".pkl") and info.file_size <= MAX_PICKLE:
                        with zf.open(info) as src:
                            yield f"{entry.path}:{info.filename}", src.read(MAX_PICKLE)
        except (zipfile.BadZipFile, NotImplementedError, EOFError, OSError):
            return


def _a16_pickle(ctx: ScanContext) -> Iterator[Finding]:
    for entry in ctx.inventory:
        if entry.size > 200 * 1024 * 1024:
            continue
        for label, data in _pickles(ctx, entry):
            names, complete = pickle_globals(data)
            bad = [n for n in names if _dangerous(n)]
            unknown = [n for n in names if not _dangerous(n) and not n.startswith(_SAFE_PREFIXES)]
            if bad:
                yield finding(
                    rule_id="LB-A16-pickle-code",
                    ebene=Ebene.A,
                    schwere=Schwere.K,
                    titel="Modelldatei führt beim Laden Code aus",
                    erklaerung=(
                        "Die Pickle-Daten rufen beim Laden Funktionen auf, die Befehle starten, "
                        "Dateien öffnen oder Verbindungen aufbauen. Wer die Datei mit `pickle`, "
                        "`torch.load` oder `joblib.load` öffnet, führt diesen Code aus."
                    ),
                    datei=entry.path,
                    zeile=None,
                    beleg=visible(f"{label}: " + ", ".join(sorted(set(bad))[:8])),
                    fix="Die Datei entfernen. Modelle als safetensors weitergeben.",
                    fix_prompt=f"Entferne {entry.path}; stelle das Modell als safetensors bereit.",
                    normbezug=("OWASP-ASI05", "OWASP-LLM03"),
                )
            elif unknown or not complete:
                yield finding(
                    rule_id="LB-A18-modell-unklar",
                    ebene=Ebene.A,
                    schwere=Schwere.M,
                    titel="Modelldatei im Pickle-Format mit unbekannten Importen"
                    if unknown
                    else "Pickle-Daten nicht vollständig lesbar",
                    erklaerung=(
                        "Pickle kann beim Laden beliebigen Code ausführen. Die Datei importiert "
                        "Klassen, die nicht auf der Liste bekannter Modellbibliotheken stehen."
                        if unknown
                        else "Pickle kann beim Laden beliebigen Code ausführen. Die Daten ließen "
                        "sich nicht bis zum Ende lesen und sind deshalb nicht vollständig geprüft."
                    ),
                    datei=entry.path,
                    zeile=None,
                    beleg=visible(f"{label}: " + ", ".join(sorted(set(unknown))[:8])),
                    fix="Modelle als safetensors weitergeben.",
                    fix_prompt=f"Stelle {entry.path} als safetensors bereit.",
                    normbezug=("OWASP-ASI05", "OWASP-LLM03"),
                )


# --- A18 safetensors -------------------------------------------------------------------------


def _safetensors_problem(ctx: ScanContext, entry: InventoryEntry) -> str | None:
    head = read_bytes(ctx, entry, 8)
    length = int.from_bytes(head, "little")
    if length > min(entry.size - 8, 100 * 1024 * 1024):
        return "Kopfzeile ist länger als die Datei"
    try:
        header = json.loads(read_bytes(ctx, entry, 8 + length)[8:])
    except (ValueError, RecursionError):
        return "Kopfzeile ist kein gültiges JSON"
    if not isinstance(header, dict):
        return "Kopfzeile ist kein Objekt"
    data_size = entry.size - 8 - length
    for key, value in header.items():
        if key == "__metadata__":
            if not isinstance(value, dict) or not all(isinstance(v, str) for v in value.values()):
                return "Metadaten sind nicht nur Text"
            continue
        if not isinstance(value, dict) or set(value) != {"dtype", "shape", "data_offsets"}:
            return f"Eintrag {key!r} hat unerwartete Felder"
        offsets = value["data_offsets"]
        if (
            not isinstance(offsets, list)
            or len(offsets) != 2
            or not all(isinstance(o, int) and 0 <= o <= data_size for o in offsets)
            or offsets[0] > offsets[1]
        ):
            return f"Eintrag {key!r} zeigt außerhalb der Datei"
    return None


def _a18_safetensors(ctx: ScanContext) -> Iterator[Finding]:
    for entry in ctx.inventory:
        if entry.kind != "safetensors" and not entry.path.lower().endswith(".safetensors"):
            continue
        problem = _safetensors_problem(ctx, entry) if entry.size >= 10 else "Datei zu kurz"
        if problem is None:
            continue
        yield finding(
            rule_id="LB-A18-modell-unklar",
            ebene=Ebene.A,
            schwere=Schwere.M,
            titel="safetensors-Datei ist nicht gültig",
            erklaerung=(
                f"{problem}. Eine beschädigte oder manipulierte Modelldatei kann Ladeprogramme "
                "zum Absturz bringen oder Daten an falscher Stelle lesen lassen."
            ),
            datei=entry.path,
            zeile=None,
            beleg=f"{entry.size} Byte",
            fix="Die Datei neu aus dem Originalmodell erzeugen.",
            fix_prompt=f"Erzeuge {entry.path} neu mit der safetensors-Bibliothek.",
            normbezug=("OWASP-LLM03",),
        )


# --- A19 auto_map, A16 chat_template ---------------------------------------------------------

_SSTI = re.compile(
    r"__(class|globals|subclasses|builtins|mro|base|bases|init|import)__|\bcycler\b|\bjoiner\b"
    r"|\blipsum\b|\bnamespace\s*\.\s*__|\bos\.(popen|system)|\.__getitem__\(|\bconfig\.items\(",
)


def _a19_config(ctx: ScanContext) -> Iterator[Finding]:
    for entry in ctx.inventory:
        name = file_name(entry).lower()
        if entry.kind != "text" or name not in ("config.json", "tokenizer_config.json"):
            continue
        data = read_json(ctx, entry)
        if not isinstance(data, dict):
            continue
        auto_map = data.get("auto_map")
        if isinstance(auto_map, dict) and auto_map:
            yield finding(
                rule_id="LB-A19-remote-code",
                ebene=Ebene.A,
                schwere=Schwere.M,
                titel="Modell bringt eigenen Code mit (trust_remote_code)",
                erklaerung=(
                    "`auto_map` verweist auf Python-Code im Paket. Transformers führt ihn aus, "
                    "sobald jemand das Modell mit `trust_remote_code=True` lädt."
                ),
                datei=entry.path,
                zeile=None,
                beleg=visible(json.dumps(auto_map)[:200]),
                fix="Ein Modell ohne eigenen Code verwenden oder den Code offenlegen und prüfen.",
                fix_prompt=f"Prüfe den Code, auf den auto_map in {entry.path} verweist.",
                normbezug=("OWASP-ASI05", "OWASP-LLM03"),
            )
        template = data.get("chat_template")
        texts = (
            [template]
            if isinstance(template, str)
            else [t.get("template", "") for t in template if isinstance(t, dict)]
            if isinstance(template, list)
            else []
        )
        for text in texts:
            m = _SSTI.search(str(text))
            if m:
                yield finding(
                    rule_id="LB-A16-template-code",
                    ebene=Ebene.A,
                    schwere=Schwere.K,
                    titel="Chat-Vorlage greift auf Python-Interna zu",
                    erklaerung=(
                        "Die Jinja-Vorlage des Modells nutzt Mittel, mit denen Vorlagen aus der "
                        "Sandbox ausbrechen und Code ausführen (Server-Side Template Injection). "
                        "Das passiert beim ersten Chat mit dem Modell."
                    ),
                    datei=entry.path,
                    zeile=None,
                    beleg=visible(str(text)[max(0, m.start() - 60) : m.end() + 60]),
                    fix="Die Chat-Vorlage durch die offizielle Vorlage des Modells ersetzen.",
                    fix_prompt=f"Ersetze chat_template in {entry.path} durch die Originalvorlage.",
                    normbezug=("OWASP-ASI05", "OWASP-LLM03"),
                )
                break
