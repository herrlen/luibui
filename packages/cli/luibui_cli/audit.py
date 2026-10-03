"""``luibui audit`` (S5-3): installed packages against what luibui checked and published.

Per package from ``~/.luibui/luibui.lock``: changed, missing or added files, withdrawn versions,
newer versions and what they bring (``luibui_install.audit``). With ``--scan`` the installed
folder is also checked locally with the current rules, like ``luibui scan``.
"""

import argparse
import shutil
import tempfile
from pathlib import Path
from typing import Any, TextIO

from luibui_cli import scan as scan_cmd
from luibui_install.audit import pruefe_eintrag
from luibui_install.main import befund_ausgeben, lock_eintraege
from luibui_scan.intake import IntakeRejectedError
from luibui_scan.models import ScanArt
from luibui_scan.scan import scan_prepared

EXIT_OK = 0
EXIT_PROBLEM = 1


def add_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "audit",
        help="installierte Pakete gegen das Register und die geprüften Dateien abgleichen",
        description="Prüft die mit luibui install installierten Pakete: Sind die Dateien noch "
        "dieselben, die luibui geprüft hat? Wurde die Version zurückgezogen, gibt es eine neuere?",
    )
    parser.add_argument(
        "--scan", action="store_true", help="installierte Ordner zusätzlich lokal neu prüfen"
    )
    parser.add_argument(
        "--ohne-register", action="store_true", help="nur lokal vergleichen, keine Abfrage"
    )
    parser.set_defaults(run=run)


def _lokal(ordner: Path, out: TextIO) -> bool:
    """Scan the installed folder; True if the overall light is red or locked."""
    scratch = Path(tempfile.mkdtemp(prefix="luibui-audit-"))
    try:
        try:
            eingabe = scan_cmd._intake(ordner, scratch)
        except IntakeRejectedError as exc:
            out.write(f"  Lokale Prüfung: abgelehnt ({scan_cmd.terminal_safe(exc.text)})\n")
            return True
        result = scan_prepared(scratch, eingabe, ScanArt.LOKAL)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    ampel = result.bewertung.gesamt.value
    out.write(
        f"  Lokale Prüfung: {scan_cmd._AMPEL.get(ampel, ampel)}, Note {result.bewertung.note}, "
        f"{len(result.pipeline.findings)} Befunde\n"
    )
    return ampel in ("rot", "gesperrt")


def run(args: argparse.Namespace, out: TextIO, err: TextIO) -> int:
    eintraege = lock_eintraege()
    if not eintraege:
        out.write("Noch nichts installiert.\n")
        return EXIT_OK
    probleme = 0
    for e in eintraege:
        b = pruefe_eintrag(e, register=not args.ohne_register)
        befund_ausgeben(b, out)
        problem = b.problem
        if args.scan and Path(b.ordner).is_dir():
            problem = _lokal(Path(b.ordner), out) or problem
        probleme += problem
    out.write(
        f"\n{len(eintraege)} Pakete geprüft, "
        + (f"{probleme} mit Abweichungen.\n" if probleme else "alle unverändert.\n")
    )
    return EXIT_PROBLEM if probleme else EXIT_OK
