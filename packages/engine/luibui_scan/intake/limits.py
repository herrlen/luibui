"""Intake limits from CLAUDE.md rule 2. Sizes are binary megabytes."""

from dataclasses import dataclass

MB = 1024 * 1024
KB = 1024


@dataclass(frozen=True, slots=True)
class Limits:
    einzeldatei_bytes: int = 10 * MB
    auswahl_dateien: int = 1_000
    auswahl_bytes: int = 50 * MB
    text_bytes: int = 200 * KB
    zip_gepackt_bytes: int = 50 * MB
    zip_entpackt_bytes: int = 200 * MB
    zip_eintraege: int = 10_000
    tiefe: int = 20
    """Maximum number of path segments, the file name included."""
    kompressionsrate: int = 100
    kompressionsrate_ab_bytes: int = 1 * MB
    """Both ratio checks (per entry and for the whole archive) apply from this unpacked size on,
    so small repetitive text files pass. Below it the ratio cannot fill the disk anyway."""
    segment_bytes: int = 255
    pfad_bytes: int = 1024


DEFAULT_LIMITS = Limits()
