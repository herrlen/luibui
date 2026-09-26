"""ScanContext: everything an analyzer may look at. Read-only by convention."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from luibui_scan.models import Pruefumfang, ScanArt


@dataclass(frozen=True, slots=True)
class InventoryEntry:
    """One file of the scanned package. Filled by the inventory step (S1-4)."""

    path: str
    """Relative path with '/' separators, already checked by intake."""
    size: int
    sha256: str
    kind: str | None = None
    """Detected type from magic bytes, e.g. 'text', 'elf', 'zip'."""


@dataclass(frozen=True, slots=True)
class ScanContext:
    """Input for every analyzer.

    ``root`` is the job's scratch directory. Analyzers only read files below it and never execute,
    import or evaluate them.
    """

    root: Path
    scan_art: ScanArt
    pruefumfang: Pruefumfang
    inventory: tuple[InventoryEntry, ...] = ()
    manifest: dict[str, Any] | None = None
    """Parsed luibui.json, if present and valid."""
    options: dict[str, Any] = field(default_factory=dict)

    def resolve(self, relative: str) -> Path:
        """Return the absolute path of a package file, refusing anything outside ``root``."""
        candidate = (self.root / relative).resolve()
        root = self.root.resolve()
        if not candidate.is_relative_to(root):
            raise ValueError(f"Pfad außerhalb des Prüfverzeichnisses: {relative!r}")
        return candidate
