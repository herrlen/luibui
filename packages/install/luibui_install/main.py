"""``luibui-install namespace/name[@version] --ziel claude|chatgpt|gemini|mistral|upload|mcp``.

Skills (``SKILL.md``) go into the skill folder of the client: Claude Code, Codex/ChatGPT,
Gemini CLI or Mistral Vibe (S5-1, docs/plattform-formate.md). ``upload`` writes the checked
archive as a ZIP for clients that only take uploads in the browser (ChatGPT, Gemini app,
Open WebUI imports the SKILL.md from it). ``mcp`` unpacks and prints a config snippet.

1. Fetch the version, verify luibui's signature, the archive's SHA-256 and size (register.py).
2. Show what luibui found: light, grade, rights from luibui.json. Red needs ``--trotzdem``.
3. Ask (or ``--ja``), unpack into a new directory next to the target, then move it in place.
4. Record it in ``~/.luibui/luibui.lock``.

Nothing from the package is ever executed. Text from the package is cleaned of control
characters before it reaches the terminal.
"""

import argparse
import json
import os
import sys
import tempfile
import unicodedata
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

from luibui_install.entpacken import entpacken
from luibui_install.register import InstallError, Version, info, laden, verlauf

EXIT_OK = 0
EXIT_FEHLER = 1
EXIT_ABGEBROCHEN = 3

AMPEL = {"gruen": "Grün", "gelb": "Gelb", "rot": "Rot", "gesperrt": "Gesperrt"}


def sauber(text: object, grenze: int = 300) -> str:
    """Control and format characters made visible, cut to ``grenze``."""
    out = []
    for c in str(text):
        if unicodedata.category(c) in ("Cc", "Cf", "Co", "Cn", "Zl", "Zp"):
            out.append(f"<U+{ord(c):04X}>")
        else:
            out.append(c)
    s = "".join(out)
    return s if len(s) <= grenze else s[: grenze - 1] + "…"


def luibui_home() -> Path:
    return Path(os.environ.get("LUIBUI_HOME") or Path.home() / ".luibui")


def _dict(wert: object) -> dict[str, Any]:
    return wert if isinstance(wert, dict) else {}


def _rechte(manifest: dict[str, Any]) -> list[str]:
    r = _dict(manifest.get("rechte"))
    dateien = _dict(r.get("dateien"))
    roh = manifest.get("endpunkte")
    endpunkte = roh if isinstance(roh, list) else []
    hosts = [sauber(e.get("host"), 80) for e in endpunkte if isinstance(e, dict)]
    zeilen = [
        f"Netzwerk: {'ja (' + ', '.join(hosts) + ')' if r.get('netzwerk') else 'nein'}",
        f"Dateien: lesen {len(dateien.get('lesen') or [])}, "
        f"schreiben {len(dateien.get('schreiben') or [])}",
        f"Shell: {'ja' if r.get('shell') else 'nein'}",
        f"Zugangsdaten: {'ja' if r.get('zugangsdaten') or r.get('umgebungsvariablen') else 'nein'}",
    ]
    return zeilen


def zusammenfassung(v: Version, out: TextIO) -> None:
    a = v.aussage
    print(f"Paket:    {sauber(v.paket)} {sauber(v.version)}", file=out)
    if v.manifest.get("beschreibung"):
        print(f"          {sauber(v.manifest['beschreibung'])}", file=out)
    print(f"Lizenz:   {sauber(v.manifest.get('lizenz', '?'))}", file=out)
    ampel = AMPEL.get(str(a.get("ampel")), sauber(a.get("ampel")))
    print(f"Prüfung:  {ampel}, Note {sauber(a.get('note'))} (luibui, Signatur geprüft)", file=out)
    print("Rechte laut luibui.json:", file=out)
    for z in _rechte(v.manifest):
        print(f"  - {z}", file=out)
    print(f"Bericht:  https://luibui.com/pakete/{v.paket}?version={v.version}", file=out)


def seit(
    verlauf_: list[tuple[str, list[dict[str, str]]]], installiert: str, ziel: str
) -> list[str]:
    """Changes of every version after ``installiert`` up to ``ziel`` (newest first in the
    history), without repeats. If ``installiert`` is not in the history: all up to ``ziel``."""
    texte: list[str] = []
    drin = False
    for version, aenderungen in verlauf_:
        if version == ziel:
            drin = True
        if version == installiert:
            break
        if drin:
            for a in aenderungen:
                t = sauber(a.get("text", "") if isinstance(a, dict) else a, 300)
                if t not in texte:
                    texte.append(t)
    return texte


def _installiert(paket: str, ziel: str) -> str | None:
    try:
        daten = json.loads((luibui_home() / "luibui.lock").read_text("utf-8"))
    except (OSError, ValueError):
        return None
    for p in daten.get("pakete", []):
        if isinstance(p, dict) and p.get("paket") == paket and p.get("ziel") == ziel:
            return str(p.get("version"))
    return None


SKILL_ORDNER = {
    "claude": (Path(".claude") / "skills", "Claude lädt den Skill beim nächsten Start."),
    "chatgpt": (
        Path(".agents") / "skills",
        "Codex lädt den Skill beim nächsten Start. Für ChatGPT im Browser: --ziel upload.",
    ),
    "gemini": (
        Path(".gemini") / "skills",
        "Gemini CLI lädt den Skill beim nächsten Start. Für die Gemini-App: --ziel upload.",
    ),
    "mistral": (Path(".vibe") / "skills", "Mistral Vibe lädt den Skill beim nächsten Start."),
}
ZIELE = [*SKILL_ORDNER, "upload", "mcp"]


def _nur_skill(v: Version, ziel: str) -> None:
    if v.manifest.get("typ") != "skill":
        raise InstallError(
            f"Mit --ziel {ziel} lassen sich Skills installieren; dieses Paket ist "
            f"„{sauber(v.manifest.get('typ'), 20)}“. Versuche --ziel mcp."
        )


def _ordner(v: Version, ziel: str, basis: Path | None) -> Path:
    ns, name = v.paket.split("/")
    if ziel in SKILL_ORDNER:
        _nur_skill(v, ziel)
        return (basis or Path.home() / SKILL_ORDNER[ziel][0]) / name
    if ziel == "upload":
        _nur_skill(v, ziel)
        return (basis or Path.cwd()) / f"{name}-{v.version}.zip"
    return (basis or luibui_home() / "pakete") / ns / name / v.version


def _mcp_schnipsel(v: Version, ordner: Path) -> dict[str, Any]:
    einstieg = str(v.manifest.get("einstieg") or "")
    pfad = str(ordner / einstieg) if einstieg else str(ordner)
    if einstieg.endswith(".py"):
        befehl = {"command": "python3", "args": [pfad]}
    elif einstieg.endswith((".js", ".mjs", ".cjs")):
        befehl = {"command": "node", "args": [pfad]}
    else:
        befehl = {"command": pfad, "args": []}
    return {"mcpServers": {v.paket.split("/")[1]: befehl}}


def _lock(v: Version, ziel: str, ordner: Path) -> Path:
    datei = luibui_home() / "luibui.lock"
    datei.parent.mkdir(parents=True, exist_ok=True)
    try:
        daten = json.loads(datei.read_text("utf-8"))
    except (OSError, ValueError):
        daten = {}
    pakete = [
        p for p in daten.get("pakete", [])
        if isinstance(p, dict) and not (p.get("paket") == v.paket and p.get("ziel") == ziel)
    ]  # fmt: skip
    pakete.append(
        {
            "paket": v.paket,
            "version": v.version,
            "archiv_sha256": v.aussage["archiv_sha256"],
            "ziel": ziel,
            "ordner": str(ordner),
            "installiert_am": datetime.now(UTC).isoformat(timespec="seconds"),
        }
    )
    neu = datei.with_suffix(".tmp")
    neu.write_text(json.dumps({"version": 1, "pakete": pakete}, indent=2, ensure_ascii=False))
    neu.replace(datei)
    return datei


def installieren(args: argparse.Namespace, out: TextIO, eingabe: TextIO) -> int:
    v = laden(args.paket)
    zusammenfassung(v, out)
    vorher = _installiert(v.paket, args.ziel)
    if vorher and vorher != v.version:
        neuerungen = seit(v.verlauf, vorher, v.version)
        print(f"\nUpdate von {sauber(vorher)} auf {sauber(v.version)}.", file=out)
        if neuerungen:
            print("Neu seitdem (laut luibui.json, von luibui signiert):", file=out)
            for t in neuerungen:
                print(f"  ! {t}", file=out)
        else:
            print("Keine neuen Rechte, Endpunkte oder Datenkategorien.", file=out)
    ampel = v.aussage.get("ampel")
    if ampel == "gesperrt":
        raise InstallError("Gesperrte Pakete werden nicht installiert.")
    if ampel == "rot" and not args.trotzdem:
        print("\nDie Prüfung ist Rot. Installieren nur mit --trotzdem.", file=out)
        return EXIT_ABGEBROCHEN
    ordner = _ordner(v, args.ziel, Path(args.ordner).expanduser() if args.ordner else None)
    if ordner.exists() and not args.ersetzen:
        raise InstallError(f"{ordner} gibt es schon. Ersetzen mit --ersetzen.")
    print(f"\nZiel:     {ordner}", file=out)
    if not args.ja:
        if not eingabe.isatty():
            print("Ohne Rückfrage nur mit --ja.", file=out)
            return EXIT_ABGEBROCHEN
        print("Installieren? [j/N] ", end="", file=out, flush=True)
        if eingabe.readline().strip().lower() not in ("j", "ja", "y", "yes"):
            print("Abgebrochen.", file=out)
            return EXIT_ABGEBROCHEN
    ordner.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ordner.parent, prefix=".luibui-") as tmp:
        neu = Path(tmp) / "paket"
        anzahl = entpacken(v.archiv, neu)
        skill = args.ziel in SKILL_ORDNER or args.ziel == "upload"
        if skill and not (neu / "SKILL.md").is_file():
            raise InstallError("Im Paket liegt keine SKILL.md im Hauptordner.")
        if args.ziel == "upload":
            # The archive itself, already checked against luibui's signature and hash.
            fertig = Path(tmp) / "upload.zip"
            fertig.write_bytes(v.archiv)
            fertig.replace(ordner)
            print(f"Gespeichert: {ordner}", file=out)
            print(
                "Hochladen: ChatGPT unter Plugins → Skills → Upload, die Gemini-App unter "
                "Skills; Open WebUI importiert die SKILL.md daraus unter Workspace → Skills.",
                file=out,
            )
            return EXIT_OK
        if ordner.exists():
            alt = Path(tmp) / "alt"
            ordner.rename(alt)
        neu.rename(ordner)
    lock = _lock(v, args.ziel, ordner)
    print(f"Installiert: {anzahl} Dateien. Eingetragen in {lock}.", file=out)
    if args.ziel in SKILL_ORDNER:
        print(SKILL_ORDNER[args.ziel][1], file=out)
    else:
        print("\nIn die MCP-Konfiguration deines Clients eintragen:", file=out)
        print(json.dumps(_mcp_schnipsel(v, ordner), indent=2, ensure_ascii=False), file=out)
    return EXIT_OK


def aktualisierungen(out: TextIO) -> int:
    """For every installed package: is there a newer version, and what does it bring?"""
    try:
        daten = json.loads((luibui_home() / "luibui.lock").read_text("utf-8"))
    except (OSError, ValueError):
        print("Noch nichts installiert.", file=out)
        return EXIT_OK
    for p in daten.get("pakete", []):
        if not isinstance(p, dict):
            continue
        try:
            paket, versionen = info(str(p.get("paket")))
        except InstallError as exc:
            print(f"{sauber(p.get('paket'))}: {exc}", file=out)
            continue
        neueste = next((v for v in versionen if not v.get("zurueckgezogen")), None)
        installiert = str(p.get("version"))
        zurueck = any(
            v.get("version") == installiert and v.get("zurueckgezogen") for v in versionen
        )
        hinweis = " (deine Version wurde zurückgezogen)" if zurueck else ""
        if neueste is None or neueste.get("version") == installiert:
            print(f"{sauber(paket)} {sauber(installiert)}: aktuell{hinweis}", file=out)
            continue
        ziel = str(neueste.get("version"))
        print(f"{sauber(paket)}: {sauber(installiert)} → {sauber(ziel)}{hinweis}", file=out)
        for t in seit(verlauf(versionen), installiert, ziel):
            print(f"  ! {t}", file=out)
    return EXIT_OK


def liste(out: TextIO) -> int:
    try:
        daten = json.loads((luibui_home() / "luibui.lock").read_text("utf-8"))
    except (OSError, ValueError):
        print("Noch nichts installiert.", file=out)
        return EXIT_OK
    for p in daten.get("pakete", []):
        print(
            f"{sauber(p.get('paket'))} {sauber(p.get('version'))} ({sauber(p.get('ziel'))}) "
            f"→ {sauber(p.get('ordner'))}",
            file=out,
        )
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="luibui-install",
        description="Installiert geprüfte Pakete aus dem luibui-Register.",
    )
    p.add_argument("paket", nargs="?", help="namespace/name oder namespace/name@version")
    p.add_argument("--ziel", choices=ZIELE, default="claude")
    p.add_argument(
        "--ordner",
        help="anderer Zielordner (Standard: ~/.claude/skills, ~/.agents/skills, ~/.gemini/skills, "
        "~/.vibe/skills, bei upload der aktuelle Ordner, bei mcp ~/.luibui/pakete)",
    )
    p.add_argument("--ja", action="store_true", help="ohne Rückfrage installieren")
    p.add_argument("--ersetzen", action="store_true", help="vorhandene Installation ersetzen")
    p.add_argument("--trotzdem", action="store_true", help="auch bei roter Ampel installieren")
    p.add_argument("--liste", action="store_true", help="installierte Pakete anzeigen")
    p.add_argument(
        "--aktualisierungen",
        action="store_true",
        help="neuere Versionen der installierten Pakete und was sie neu dürfen",
    )
    return p


def main(
    argv: Sequence[str] | None = None, out: TextIO | None = None, eingabe: TextIO | None = None
) -> int:
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    if args.liste:
        return liste(out)
    if args.aktualisierungen:
        return aktualisierungen(out)
    if not args.paket:
        build_parser().print_help(out)
        return EXIT_FEHLER
    try:
        return installieren(args, out, eingabe or sys.stdin)
    except InstallError as exc:
        print(f"Fehler: {exc}", file=out)
        return EXIT_FEHLER
    except OSError as exc:
        print(f"Fehler beim Schreiben: {sauber(exc.strerror or exc)}", file=out)
        return EXIT_FEHLER


if __name__ == "__main__":
    sys.exit(main())
