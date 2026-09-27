"""Helpers shared by analyzers: reading package files safely and building findings."""

import os
from collections.abc import Iterator
from dataclasses import dataclass

from luibui_scan.context import InventoryEntry, ScanContext
from luibui_scan.models import Achse, Ebene, Finding, Nachweisgrad, Schwere

TEXT_KINDS = frozenset({"text", "script"})
MAX_TEXT_BYTES = 5 * 1024 * 1024
"""Larger text files are skipped by content analyzers (and reported as such by the pipeline)."""
MAX_BELEG_CHARS = 300


@dataclass(frozen=True, slots=True)
class TextFile:
    entry: InventoryEntry
    text: str

    @property
    def path(self) -> str:
        return self.entry.path

    def line_of(self, offset: int) -> int:
        return self.text.count("\n", 0, offset) + 1

    def line_text(self, line: int) -> str:
        lines = self.text.split("\n", line)
        return lines[line - 1] if len(lines) >= line else ""


def read_bytes(ctx: ScanContext, entry: InventoryEntry, limit: int = MAX_TEXT_BYTES) -> bytes:
    """Read a package file without following symlinks; never more than ``limit`` bytes."""
    fd = os.open(ctx.resolve(entry.path), os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as f:
        return f.read(limit)


def text_files(ctx: ScanContext) -> Iterator[TextFile]:
    for entry in ctx.inventory:
        if entry.kind in TEXT_KINDS and entry.size <= MAX_TEXT_BYTES:
            yield TextFile(entry, read_bytes(ctx, entry).decode("utf-8", errors="replace"))


def visible(text: str, limit: int = MAX_BELEG_CHARS) -> str:
    """Make invisible and control characters visible as ``<U+XXXX>`` and cut to ``limit``."""
    import unicodedata

    out = []
    for c in text:
        if c in "\t" or (unicodedata.category(c) not in ("Cc", "Cf", "Co", "Cn", "Zl", "Zp")):
            out.append(c)
        else:
            out.append(f"<U+{ord(c):04X}>")
    result = "".join(out)
    return result if len(result) <= limit else result[: limit - 1] + "…"


def finding(
    *,
    rule_id: str,
    ebene: Ebene,
    schwere: Schwere,
    titel: str,
    erklaerung: str,
    datei: str | None,
    zeile: int | None,
    beleg: str | None,
    fix: str,
    fix_prompt: str,
    normbezug: tuple[str, ...],
    achse: Achse = Achse.SICHERHEIT,
    nachweisgrad: Nachweisgrad = Nachweisgrad.STATISCH_ERKANNT,
) -> Finding:
    if beleg is not None:
        beleg = "\n".join(beleg.split("\n")[:5])[:2000]
    return Finding(
        rule_id=rule_id,
        ebene=ebene,
        schwere=schwere,
        achse=achse,
        titel=titel,
        erklaerung=erklaerung,
        datei=datei,
        zeile=zeile,
        beleg=beleg,
        nachweisgrad=nachweisgrad,
        normbezug=normbezug,
        fix=fix,
        fix_prompt=fix_prompt,
    )
