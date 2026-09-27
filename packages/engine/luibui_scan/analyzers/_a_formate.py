"""Analyzer A, part 3: file names, Git attributes, installers and hidden appended data.

Prüfkatalog A04 (installers without a magic of their own), A13 (Git attributes and LFS), A14
(deceptive names) and A15 (polyglots and data after the end of an image or PDF). Scanner-Matrix
ARC-02, ARC-03, INV-01, BIN-01. Only bytes are read; nothing is opened by a viewer or parser.
"""

import re
import zipfile
from collections.abc import Iterator
from pathlib import PurePosixPath

from luibui_scan.analyzers._common import file_name, finding, read_bytes, read_text, visible
from luibui_scan.context import InventoryEntry, ScanContext
from luibui_scan.models import Ebene, Finding, Schwere

# --- A04 installers that are containers of their own -----------------------------------------

_INSTALLER = {
    ".msi": ({"ole"}, "Windows-Installer"),
    ".apk": ({"zip"}, "Android-App"),
    ".dmg": (None, "macOS-Abbild"),
    ".pkg": (None, "macOS-Installer"),
}


def _installer(ctx: ScanContext) -> Iterator[Finding]:
    for entry in ctx.inventory:
        ext = PurePosixPath(entry.path).suffix.lower()
        if ext not in _INSTALLER:
            continue
        kinds, label = _INSTALLER[ext]
        if kinds is not None and entry.kind not in kinds:
            continue
        if kinds is None and entry.kind in ("text", "script", "leer"):
            continue
        yield finding(
            rule_id="LB-A04-installationspaket",
            ebene=Ebene.A,
            schwere=Schwere.H,
            titel=f"Installationspaket im Paket ({label})",
            erklaerung=(
                "Das Paket enthält ein fertiges Installationspaket. Was es installiert, lässt sich "
                "statisch nicht prüfen."
            ),
            datei=entry.path,
            zeile=None,
            beleg=f"Endung {ext}, Typ {entry.kind}, {entry.size} Byte",
            fix="Das Installationspaket entfernen und auf die offizielle Quelle verweisen.",
            fix_prompt=f"Entferne {entry.path} aus dem Paket.",
            normbezug=("OWASP-ASI04", "OWASP-LLM03"),
        )


# --- A13 Git attributes with drivers, LFS pointers -------------------------------------------

_DRIVER = re.compile(r"^\s*[^#\s][^\n]*\s(filter|diff|merge)=(?!lfs\b)\S+", re.MULTILINE)
_LFS_POINTER = b"version https://git-lfs.github.com/spec/v1"


def _a13(ctx: ScanContext) -> Iterator[Finding]:
    pointers: list[str] = []
    for entry in ctx.inventory:
        if entry.kind not in ("text", "script"):
            continue
        if file_name(entry) == ".gitattributes":
            text = read_text(ctx, entry, 64 * 1024)
            m = _DRIVER.search(text)
            if m:
                yield finding(
                    rule_id="LB-A13-git-treiber",
                    ebene=Ebene.A,
                    schwere=Schwere.M,
                    titel="Git-Attribute rufen eigene Treiber auf",
                    erklaerung=(
                        f"`{m.group(1)}=` lässt Git beim Auschecken, Vergleichen oder "
                        "Zusammenführen ein Programm laufen, sobald der Treiber eingerichtet ist."
                    ),
                    datei=entry.path,
                    zeile=text.count("\n", 0, m.start()) + 1,
                    beleg=visible(m.group(0).strip()),
                    fix="Eigene Filter-, Diff- und Merge-Treiber aus `.gitattributes` entfernen.",
                    fix_prompt=f"Entferne die Treiber-Einträge aus {entry.path}.",
                    normbezug=("OWASP-ASI04",),
                )
        elif entry.size < 1024 and read_bytes(ctx, entry, 64).startswith(_LFS_POINTER):
            pointers.append(entry.path)
    if pointers:
        yield finding(
            rule_id="LB-A13-lfs-zeiger",
            ebene=Ebene.A,
            schwere=Schwere.I,
            titel="Git-LFS-Dateien nicht geprüft",
            erklaerung=(
                f"{len(pointers)} Dateien sind nur Zeiger auf Git LFS. Ihr Inhalt wurde nicht "
                "geladen und ist nicht Teil dieser Prüfung."
            ),
            datei=pointers[0],
            zeile=None,
            beleg=visible(", ".join(pointers[:10])),
            fix="Die Dateien direkt ins Paket legen, wenn sie zum Paket gehören.",
            fix_prompt="Lege die LFS-Dateien als echte Dateien ins Paket.",
            normbezug=(),
        )


# --- A14 deceptive names ---------------------------------------------------------------------

_HARMLESS = frozenset(
    {"pdf", "doc", "docx", "xls", "xlsx", "txt", "jpg", "jpeg", "png", "gif", "mp3", "mp4", "md"}
)
_RUNNABLE = frozenset(
    {"exe", "scr", "com", "bat", "cmd", "ps1", "vbs", "js", "jse", "hta", "msi", "lnk", "sh", "app"}
)
_RESERVED = re.compile(r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?$", re.IGNORECASE)


def _a14(ctx: ScanContext) -> Iterator[Finding]:
    for entry in ctx.inventory:
        name = file_name(entry)
        parts = name.lower().split(".")
        if len(parts) >= 3 and parts[-2] in _HARMLESS and parts[-1] in _RUNNABLE:
            yield _name_finding(
                entry,
                "doppelendung",
                "Doppelte Dateiendung tarnt ein Programm",
                f"`{name}` sieht aus wie eine `.{parts[-2]}`-Datei, ist aber `.{parts[-1]}`. "
                "Viele Dateimanager blenden die letzte Endung aus.",
            )
        elif any(_RESERVED.match(seg) for seg in entry.path.split("/")):
            yield _name_finding(
                entry,
                "reservierter-name",
                "Reservierter Windows-Name",
                "Namen wie `CON`, `NUL` oder `COM1` lassen sich unter Windows nicht anlegen oder "
                "öffnen. Sie brechen Installation und Prüfung auf Windows-Rechnern.",
            )


def _name_finding(entry: InventoryEntry, art: str, titel: str, erklaerung: str) -> Finding:
    return finding(
        rule_id=f"LB-A14-{art}",
        ebene=Ebene.A,
        schwere=Schwere.M,
        titel=titel,
        erklaerung=erklaerung,
        datei=entry.path,
        zeile=None,
        beleg=visible(entry.path),
        fix="Die Datei mit einem eindeutigen, unverfänglichen Namen ablegen.",
        fix_prompt=f"Benenne {entry.path} eindeutig um oder entferne die Datei.",
        normbezug=("OWASP-ASI04",),
    )


# --- A15 polyglots and appended data ---------------------------------------------------------

_APPENDED_MIN = 1024
_END_MARKERS = {
    "png": b"IEND\xaeB`\x82",
    "jpeg": b"\xff\xd9",
    "gif": b"\x00;",
    "pdf": b"%%EOF",
}
_SCAN_LIMIT = 10 * 1024 * 1024


def _a15(ctx: ScanContext) -> Iterator[Finding]:
    for entry in ctx.inventory:
        if entry.kind not in _END_MARKERS or entry.size > _SCAN_LIMIT:
            continue
        path = ctx.resolve(entry.path)
        embedded_zip = zipfile.is_zipfile(path)
        data = read_bytes(ctx, entry, _SCAN_LIMIT)
        end = data.rfind(_END_MARKERS[entry.kind])
        appended = len(data) - (end + len(_END_MARKERS[entry.kind])) if end >= 0 else 0
        # PDFs may end with whitespace or several updates; only large tails count there.
        if not embedded_zip and appended < _APPENDED_MIN:
            continue
        yield finding(
            rule_id="LB-A15-angehaengte-daten",
            ebene=Ebene.A,
            schwere=Schwere.H if embedded_zip else Schwere.M,
            titel=(
                "Datei ist gleichzeitig ein Archiv"
                if embedded_zip
                else "Daten hinter dem Dateiende versteckt"
            ),
            erklaerung=(
                f"Die Datei ist ein gültiges {entry.kind.upper()} und enthält zusätzlich ein "
                "ZIP-Archiv. So werden Inhalte an Prüfungen vorbeigeschmuggelt."
                if embedded_zip
                else f"Hinter dem Ende des {entry.kind.upper()} folgen {appended} Byte, die kein "
                "Programm anzeigt."
            ),
            datei=entry.path,
            zeile=None,
            beleg=f"Typ {entry.kind}, {entry.size} Byte, {max(appended, 0)} Byte nach dem Ende",
            fix="Die Datei neu speichern, sodass nur das Bild oder Dokument selbst enthalten ist.",
            fix_prompt=f"Speichere {entry.path} neu ohne angehängte Daten.",
            normbezug=("OWASP-ASI04",),
        )
