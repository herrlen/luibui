"""Report as defined by ``spec/report.schema.json`` (Konzept §2 and §5)."""

import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from luibui_scan import __version__
from luibui_scan.models import Finding, Pruefumfang, ScanArt, Schwere
from luibui_scan.scan import ScanResult

SCHEMA_VERSION = "1"
OHNE_GEWAEHR = "Schnellscan mit eingeschränktem Umfang, ohne Gewähr."

_UMFANG_HINWEIS = {
    Pruefumfang.AUSWAHL: "Dateiauswahl ohne Manifest",
    Pruefumfang.EINZELDATEI: "Einzeldatei-Prüfung",
}


_ORDER = {s: i for i, s in enumerate([Schwere.K, Schwere.H, Schwere.M, Schwere.N, Schwere.I])}


def sort_findings(findings: Iterable[Finding]) -> list[Finding]:
    """Most severe first, then by file and line."""
    return sorted(findings, key=lambda f: (_ORDER[f.schwere], f.datei or "", f.zeile or 0))


def hinweise(result: ScanResult) -> list[str]:
    out: list[str] = []
    if result.scan_art is ScanArt.SCHNELL:
        out.append(OHNE_GEWAEHR)
    if result.pruefumfang in _UMFANG_HINWEIS:
        out.append(_UMFANG_HINWEIS[result.pruefumfang])
    if not result.pipeline.ran:
        out.append(
            "Es ist noch keine Prüfung eingebaut. Das Ergebnis sagt nichts über die Sicherheit "
            "des Pakets aus, deshalb höchstens Gelb."
        )
    elif result.pipeline.failed:
        out.append(
            f"Prüfung unvollständig: {len(result.pipeline.failed)} Prüfung(en) fehlgeschlagen, "
            "deshalb höchstens Gelb."
        )
    return out


def nicht_geprueft(result: ScanResult) -> list[dict[str, str]]:
    skipped = [{"pruefung": s.titel, "grund": s.grund} for s in result.pipeline.skipped]
    failed = [{"pruefung": f.titel, "grund": "fehlgeschlagen"} for f in result.pipeline.failed]
    return skipped + failed


def build_report(
    result: ScanResult,
    *,
    name: str,
    scan_id: uuid.UUID | None = None,
    geprueft_am: datetime | None = None,
) -> dict[str, Any]:
    """Assemble the report. ``name`` is the package or file name shown to the user."""
    b = result.bewertung
    inv = result.inventory
    when = (geprueft_am or datetime.now(UTC)).astimezone(UTC)
    return {
        "schema_version": SCHEMA_VERSION,
        "scan_id": str(scan_id or uuid.uuid4()),
        "scan_art": result.scan_art.value,
        "pruefumfang": result.pruefumfang.value,
        "geprueft_am": when.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "engine_version": __version__,
        "paket": {
            "name": name[:200] or "unbenannt",
            "version": None,
            "quelle": result.eingabe.value,
            "dateien": len(inv.entries),
            "bytes": inv.bytes,
            "sha256": inv.sha256,
        },
        "ampeln": {
            "sicherheit": b.sicherheit.value,
            "dsgvo": b.dsgvo.value,
            "gesamt": b.gesamt.value,
        },
        "note": b.note,
        "freigabe": b.freigabe.value,
        "befunde": [f.to_json_dict() for f in sort_findings(result.pipeline.findings)],
        "nicht_geprueft": nicht_geprueft(result),
        "hinweise": hinweise(result),
    }
