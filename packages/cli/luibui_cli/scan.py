"""``luibui scan <pfad>``: check a local folder, ZIP archive or single file (S1-11).

The input goes through the same intake as uploads into a private temporary directory, which is
deleted afterwards. Everything printed that comes from the package is escaped for the terminal.
"""

import argparse
import json
import shutil
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

from luibui_scan.intake import (
    IntakeRejectedError,
    accept_directory,
    accept_file,
    extract_zip,
)
from luibui_scan.models import Finding, Pruefumfang, ScanArt
from luibui_scan.report import build_report, hinweise, sort_findings
from luibui_scan.scan import Eingabe, ScanResult, scan_prepared
from luibui_scan.scoring import AmpelDsgvo, AmpelSicherheit, Freigabe

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_REJECTED = 3

_UMFANG = {
    Pruefumfang.PAKET: "Paket",
    Pruefumfang.AUSWAHL: "Dateiauswahl ohne Manifest (luibui.json fehlt)",
    Pruefumfang.EINZELDATEI: "Einzeldatei",
}

_AMPEL = {
    "gruen": "Grün",
    "gelb": "Gelb",
    "rot": "Rot",
    "gesperrt": "Gesperrt",
    "nicht_bewertet": "nicht bewertet",
}
_FREIGABE = {
    Freigabe.FREIGEGEBEN: "freigegeben",
    Freigabe.PRUEFUNG_NOETIG: "Prüfung nötig",
    Freigabe.BLOCKIERT: "blockiert",
}

EPILOG = """Rückgabewerte:
  0  Prüfung gelaufen (Befunde stehen in der Ausgabe)
  2  Pfad nicht gefunden oder falscher Aufruf
  3  Eingabe abgelehnt, zum Beispiel wegen eines unsicheren Pfads im Archiv"""


def add_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "scan",
        help="Ordner, ZIP-Archiv oder einzelne Datei lokal prüfen",
        description="Prüft einen Ordner, ein ZIP-Archiv oder eine einzelne Datei lokal. "
        "Es wird nichts hochgeladen und nichts aus dem Paket ausgeführt.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("pfad", type=Path, help="Ordner, .zip-Datei oder einzelne Datei")
    parser.add_argument("--json", action="store_true", help="Ergebnis als JSON ausgeben")
    parser.set_defaults(run=run)


def run(args: argparse.Namespace, out: TextIO, err: TextIO) -> int:
    source: Path = args.pfad
    if not source.exists():
        err.write(f"luibui: Pfad nicht gefunden: {terminal_safe(str(source))}\n")
        return EXIT_USAGE
    scratch = Path(tempfile.mkdtemp(prefix="luibui-scan-"))
    try:
        try:
            eingabe = _intake(source, scratch)
        except IntakeRejectedError as exc:
            _print_rejected(exc, args.json, out)
            return EXIT_REJECTED
        result = scan_prepared(scratch, eingabe, ScanArt.LOKAL)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    if args.json:
        report = build_report(result, name=source.resolve().name or str(source))
        json.dump(report, out, indent=2, ensure_ascii=True)
        out.write("\n")
    else:
        out.write(render_text(source, result))
    return EXIT_OK


def _intake(source: Path, scratch: Path) -> Eingabe:
    if source.is_dir():
        accept_directory(source, scratch)
        return Eingabe.LOKAL
    if source.suffix.lower() == ".zip":
        extract_zip(source, scratch)
        return Eingabe.ZIP
    with source.open("rb") as f:
        accept_file(source.name, f, scratch)
    return Eingabe.DATEI


def terminal_safe(text: str) -> str:
    """Escape control and invisible format characters (ANSI escapes, Bidi, zero-width, tags)."""
    return "".join(
        c if c == "\n" or unicodedata.category(c) not in ("Cc", "Cf") else _escape(c) for c in text
    )


def _escape(c: str) -> str:
    code = ord(c)
    return (
        f"\\x{code:02x}"
        if code < 0x100
        else f"\\u{code:04x}"
        if code < 0x10000
        else f"\\U{code:08x}"
    )


def _print_rejected(exc: IntakeRejectedError, as_json: bool, out: TextIO) -> None:
    if as_json:
        data = {"abgelehnt": {"grund": exc.grund.value, "text": exc.text, "pfad": exc.pfad}}
        json.dump(data, out, indent=2, ensure_ascii=True)
        out.write("\n")
        return
    out.write(f"Abgelehnt: {exc.text}\n")
    if exc.pfad is not None:
        out.write(f"  Eintrag: {terminal_safe(exc.pfad)}\n")
    out.write("Es wurde nichts geprüft.\n")


def _size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB".replace(".", ",")
    return f"{n / 1024 / 1024:.1f} MB".replace(".", ",")


def render_text(source: Path, result: ScanResult) -> str:
    inv = result.inventory
    pipe = result.pipeline
    lines = [
        f"luibui scan: {terminal_safe(str(source))}",
        f"Umfang:    {_UMFANG[result.pruefumfang]}",
        f"Pakettyp:  {inv.pakettyp.value}",
    ]
    lines += [f"           {terminal_safe(m)}" for m in inv.merkmale]
    lines += [
        f"Dateien:   {len(inv.entries)} ({_size(inv.bytes)}), Inventar {inv.sha256[:12]}",
        "Sprachen:  " + (", ".join(f"{k} {v}" for k, v in inv.sprachen.items()) or "keine"),
        "",
        f"Prüfungen: {len(pipe.ran)} gelaufen, {len(pipe.skipped)} übersprungen, "
        f"{len(pipe.failed)} fehlgeschlagen",
    ]
    lines += [f"  übersprungen: {s.titel} ({s.grund})" for s in pipe.skipped]
    lines += [f"  fehlgeschlagen: {f.titel} ({f.fehler})" for f in pipe.failed]
    lines.append("")
    if pipe.findings:
        lines.append(f"Befunde: {len(pipe.findings)}")
        for finding in sort_findings(pipe.findings):
            lines += _finding_lines(finding)
    else:
        lines.append("Befunde: keine")
    lines += ["", *_verdict_lines(result)]
    return "\n".join(lines) + "\n"


def _finding_lines(f: Finding) -> list[str]:
    where = f.datei or "(Paket)"
    if f.zeile is not None:
        where += f":{f.zeile}"
    lines = [
        "",
        f"  [{f.schwere.value}] {terminal_safe(f.titel)}  ({f.rule_id})",
        f"      {terminal_safe(where)}",
    ]
    if f.beleg:
        lines += [f"      | {terminal_safe(line)}" for line in f.beleg.split("\n")]
    lines.append(f"      Fix: {terminal_safe(f.fix)}")
    return lines


def _verdict_lines(result: ScanResult) -> list[str]:
    b = result.bewertung
    gesamt = _AMPEL[b.gesamt.value]
    if b.gesamt is AmpelSicherheit.GRUEN:
        heute = datetime.now().strftime("%d.%m.%Y")
        gesamt += f", keine bekannten Befunde, geprüft am {heute}"
    else:
        gesamt += f", {_FREIGABE[b.freigabe]}"
    lines = [
        f"Sicherheit: {_AMPEL[b.sicherheit.value]}",
        f"DSGVO:      {_AMPEL[b.dsgvo.value]}",
        f"Gesamt:     {gesamt}",
        f"Note:       {b.note} von 100",
    ]
    if b.dsgvo is AmpelDsgvo.NICHT_BEWERTET:
        lines.append("            DSGVO wird nur bei einem Paket mit luibui.json bewertet.")
    lines += [f"Hinweis: {h}" for h in hinweise(result)]
    return lines
