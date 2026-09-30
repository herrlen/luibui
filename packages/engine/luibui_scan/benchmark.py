"""Benchmark (S3-2): detection rate and false-alarm rate per category → ``docs/benchmark.md``.

    python -m luibui_scan.benchmark corpus/ --holen /tmp/v
    python -m luibui_scan.benchmark corpus/ [--vergleich /tmp/v] [--ausgabe docs/benchmark.md]

Three sets, all scanned with the full pipeline like an Intensivscan:

- **Nachbildungen:** the defused fixtures in ``corpus/generate.py`` (one per Scanner-Matrix row).
  Detected means the expected rule fired *and* the overall light is not green.
- **Gutartig, eigen:** ``corpus/benign/*`` and the benign counterparts in ``generate.py``.
- **Gutartig, echt** (``--vergleich``): the open packages in ``corpus/vergleich.json``, fetched
  beforehand with ``--holen`` through ``safe_git`` at the current default branch (on the host:
  the worker image has no git); the commit is printed with the result.

A false alarm is a benign package with a K or H finding. ``osv:`` findings are counted apart:
a known vulnerability in a pinned dependency is a fact, not a false alarm. Findings a reviewer
has accepted for one package stay listed but leave the count (``berechtigt`` in vergleich.json).

Run it where all scanners are installed (the worker image, see ``scripts/benchmark.sh``); the
table names every analyzer that was skipped or failed, so a thin local run cannot pass for a
full one. Nothing from a scanned package is executed or imported.
"""

import argparse
import datetime
import importlib.util
import json
import shutil
import sys
import tempfile
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

from luibui_scan.analyzers import _a_modelle
from luibui_scan.intake.limits import MB, Limits
from luibui_scan.intake.safe_git import clone_into
from luibui_scan.models import Finding, ScanArt, Schwere
from luibui_scan.scan import Eingabe, ScanResult, scan_prepared
from luibui_scan.scoring import AmpelSicherheit

ZIEL_ERKENNUNG = 0.90
ZIEL_ERKENNUNG_CODE = 0.95
ZIEL_FEHLALARM = 0.05
"""Sprint 3 Definition of Done (docs/luibui_Sprintplanung.md)."""

VERGLEICH_LIMITS = Limits(auswahl_dateien=60_000, auswahl_bytes=1024 * MB)
VERGLEICH_MAX_BYTES = 1536 * MB
VERGLEICH_TIMEOUT = 300.0
"""Only for the fixed list in vergleich.json; uploads keep the limits of safe_git."""

_ERNST = (Schwere.K, Schwere.H)
_MATRIX_GRUPPE = {
    "AGT": "Agenten-Konfiguration",
    "ARC": "Archive und Dateinamen",
    "BIN": "Binärdateien",
    "COD": "Code",
    "DAT": "Datendateien",
    "DEP": "Abhängigkeiten",
    "DOC": "Dokumente",
    "INV": "Inventar",
    "MOD": "Modelle",
    "SEC": "Secrets",
}


@dataclass
class Treffer:
    """One scanned package."""

    name: str
    gruppe: str
    ampel: str
    ernst: list[str] = field(default_factory=list)
    """K/H findings as ``"<Schwere> <rule_id> <datei>"``."""
    luecken: list[str] = field(default_factory=list)
    """K/H ``osv:`` findings (known vulnerabilities, not counted as false alarms)."""
    berechtigt: list[str] = field(default_factory=list)
    erkannt: bool | None = None
    """Only for malicious fixtures."""
    erwartet: str = ""
    herkunft: str = ""

    @property
    def fehlalarm(self) -> bool:
        return bool(self.ernst)


@dataclass
class Lauf:
    boesartig: list[Treffer] = field(default_factory=list)
    gutartig_eigen: list[Treffer] = field(default_factory=list)
    gutartig_echt: list[Treffer] = field(default_factory=list)
    nicht_geholt: list[str] = field(default_factory=list)
    uebersprungen: dict[str, str] = field(default_factory=dict)
    fehlgeschlagen: dict[str, str] = field(default_factory=dict)


def load_generator(corpus: Path) -> ModuleType:
    """Import ``corpus/generate.py`` (our own fixture code, never package content)."""
    spec = importlib.util.spec_from_file_location("corpus_generate", corpus / "generate.py")
    if spec is None or spec.loader is None:
        raise FileNotFoundError(corpus / "generate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(root: Path, files: Mapping[str, bytes]) -> None:
    for rel, data in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def _describe(f: Finding) -> str:
    return f"{f.schwere.value} {f.rule_id} {f.datei or '-'}"


def _record(lauf: Lauf, result: ScanResult) -> None:
    for s in result.pipeline.skipped:
        lauf.uebersprungen.setdefault(s.titel, s.grund)
    for fa in result.pipeline.failed:
        lauf.fehlgeschlagen.setdefault(fa.titel, fa.fehler)


def bewerte_gutartig(
    name: str, gruppe: str, result: ScanResult, berechtigt: Iterable[str] = ()
) -> Treffer:
    accepted = tuple(berechtigt)
    t = Treffer(name, gruppe, result.bewertung.gesamt.value)
    for f in result.pipeline.findings:
        if f.schwere not in _ERNST:
            continue
        if f.rule_id.startswith("osv:"):
            t.luecken.append(_describe(f))
        elif any(f.rule_id.startswith(a) for a in accepted):
            t.berechtigt.append(_describe(f))
        else:
            t.ernst.append(_describe(f))
    return t


def bewerte_boesartig(name: str, erwartet: str, result: ScanResult) -> Treffer:
    gruppe = _MATRIX_GRUPPE.get(name.split("-")[0], name.split("-")[0])
    t = Treffer(name, gruppe, result.bewertung.gesamt.value, erwartet=erwartet)
    hit = any(f.rule_id.startswith(erwartet) for f in result.pipeline.findings)
    t.erkannt = hit and result.bewertung.gesamt is not AmpelSicherheit.GRUEN
    return t


def ebene_von(erwartet: str) -> str:
    """``LB-C04-…`` → ``C``; anything else by its tool prefix."""
    if erwartet.startswith("LB-") and len(erwartet) > 3:
        return erwartet[3]
    return erwartet.split(":")[0]


def run_fixtures(corpus: Path, lauf: Lauf, work: Path) -> None:
    gen = load_generator(corpus)
    malicious, benign = gen.fixtures()
    # The pickle fixture names the harmless corpus/_dummy.py instead of a real dangerous module;
    # the engine tests treat that name as dangerous, and so does the benchmark.
    original = _a_modelle._DANGEROUS_MODULES
    _a_modelle._DANGEROUS_MODULES = original | {"_dummy"}
    try:
        for matrix_id, (files, erwartet) in sorted(malicious.items()):
            root = work / "m" / matrix_id
            _write(root, files)
            result = scan_prepared(root, Eingabe.ZIP, ScanArt.INTENSIV)
            _record(lauf, result)
            lauf.boesartig.append(bewerte_boesartig(matrix_id, erwartet, result))
            shutil.rmtree(root)
    finally:
        _a_modelle._DANGEROUS_MODULES = original
    for matrix_id, files in sorted(benign.items()):
        root = work / "b" / matrix_id
        _write(root, files)
        result = scan_prepared(root, Eingabe.ZIP, ScanArt.INTENSIV)
        _record(lauf, result)
        gruppe = _MATRIX_GRUPPE.get(matrix_id.split("-")[0], "Matrix")
        lauf.gutartig_eigen.append(bewerte_gutartig(f"Matrix {matrix_id}", gruppe, result))
        shutil.rmtree(root)
    for package in sorted(p for p in (corpus / "benign").iterdir() if p.is_dir()):
        root = work / "k" / package.name
        shutil.copytree(package, root)
        result = scan_prepared(root, Eingabe.LOKAL, ScanArt.INTENSIV)
        _record(lauf, result)
        lauf.gutartig_eigen.append(bewerte_gutartig(package.name, "Korpus", result))
        shutil.rmtree(root)


def _slug(repo: str) -> str:
    return repo.removeprefix("https://github.com/").replace("/", "__")


def hole_vergleich(liste: Path, ziel: Path) -> list[str]:
    """Fetch every repository of the list through ``safe_git`` into ``ziel/<slug>/``.

    Runs where git is installed (the host); the worker image has none. Writes
    ``ziel/stand.json`` with the commit per repository and returns the failures.
    """
    data = json.loads(liste.read_text("utf-8"))
    stand: dict[str, str] = {}
    fehler: list[str] = []
    ziel.mkdir(parents=True, exist_ok=True)
    work = ziel / ".work"
    work.mkdir(exist_ok=True)
    for repo in dict.fromkeys(entry["repo"] for entry in data["pakete"]):
        checkout = ziel / _slug(repo)
        checkout.mkdir()
        try:
            clone = clone_into(
                repo,
                checkout,
                work,
                timeout=VERGLEICH_TIMEOUT,
                max_bytes=VERGLEICH_MAX_BYTES,
                limits=VERGLEICH_LIMITS,
            )
        except Exception as exc:  # report and go on with the next repository
            fehler.append(f"{repo}: {type(exc).__name__}: {exc}")
            shutil.rmtree(checkout, ignore_errors=True)
            continue
        stand[repo] = clone.commit
    shutil.rmtree(work, ignore_errors=True)
    (ziel / "stand.json").write_text(
        json.dumps({"stand": stand, "fehler": fehler}, indent=2), encoding="utf-8"
    )
    return fehler


def run_vergleich(liste: Path, geholt: Path, lauf: Lauf, work: Path) -> None:
    """Scan the packages that ``hole_vergleich`` fetched into ``geholt``."""
    data = json.loads(liste.read_text("utf-8"))
    stand = json.loads((geholt / "stand.json").read_text("utf-8"))
    lauf.nicht_geholt.extend(stand["fehler"])
    for entry in data["pakete"]:
        repo, pfad = entry["repo"], entry["pfad"]
        if repo not in stand["stand"]:
            continue
        commit = stand["stand"][repo][:12]
        checkout = geholt / _slug(repo)
        quelle = checkout / pfad if pfad else checkout
        kurz = repo.removeprefix("https://github.com/")
        name = f"{kurz}/{pfad}" if pfad else kurz
        if not quelle.is_dir():
            lauf.nicht_geholt.append(f"{name}: Pfad fehlt im Stand {commit}")
            continue
        root = work / "p"
        shutil.copytree(quelle, root)
        result = scan_prepared(root, Eingabe.GIT, ScanArt.INTENSIV)
        _record(lauf, result)
        accepted = [b["regel"] for b in entry.get("berechtigt", [])]
        t = bewerte_gutartig(name, kurz, result, accepted)
        t.herkunft = commit
        lauf.gutartig_echt.append(t)
        shutil.rmtree(root)


def _quote(n: int, von: int) -> str:
    return "–" if von == 0 else f"{n}/{von} ({100 * n / von:.0f} %)"


def _ziel(wert: float, ziel: float, *, hoechstens: bool = False) -> str:
    ok = wert <= ziel if hoechstens else wert >= ziel
    return "erreicht" if ok else "**nicht erreicht**"


def _rate(items: list[Treffer], attr: str) -> float:
    return sum(bool(getattr(t, attr)) for t in items) / len(items) if items else 0.0


def render(lauf: Lauf, *, stand: str, datum: str) -> str:
    out: list[str] = []
    w = out.append
    w("# Benchmark\n")
    w(
        f"Stand `{stand}`, gemessen am {datum} mit `python -m luibui_scan.benchmark` "
        "(S3-2). Erzeugt, nicht von Hand ändern; Erklärungen und Kalibrierung stehen in "
        "`docs/log.md`.\n"
    )
    b, ge, ec = lauf.boesartig, lauf.gutartig_eigen, lauf.gutartig_echt
    code = [t for t in b if ebene_von(t.erwartet) == "C"]
    w("## Ergebnis\n")
    w("| Messung | Wert | Ziel Sprint 3 | |")
    w("|---|---|---|---|")
    w(
        f"| Erkennung, Nachbildungen | {_quote(sum(bool(t.erkannt) for t in b), len(b))} "
        f"| ≥ 90 % | {_ziel(_rate(b, 'erkannt'), ZIEL_ERKENNUNG)} |"
    )
    w(
        f"| Erkennung, Code-Ebene | {_quote(sum(bool(t.erkannt) for t in code), len(code))} "
        f"| ≥ 95 % | {_ziel(_rate(code, 'erkannt'), ZIEL_ERKENNUNG_CODE)} |"
    )
    if ec:
        w(
            f"| Fehlalarme, echte Pakete | {_quote(sum(t.fehlalarm for t in ec), len(ec))} "
            f"| ≤ 5 % | {_ziel(_rate(ec, 'fehlalarm'), ZIEL_FEHLALARM, hoechstens=True)} |"
        )
    else:
        grund = "siehe „Nicht geholt“" if lauf.nicht_geholt else "ohne `--vergleich`"
        w(f"| Fehlalarme, echte Pakete | nicht gemessen ({grund}) | ≤ 5 % | |")
    w(f"| Fehlalarme, eigener Korpus | {_quote(sum(t.fehlalarm for t in ge), len(ge))} | 0 | |")
    w("")
    w(
        "Erkannt heißt: die erwartete Regel hat angeschlagen und die Gesamtampel ist nicht grün. "
        "Fehlalarm heißt: ein gutartiges Paket hat mindestens einen K- oder H-Befund. Bekannte "
        "Lücken aus OSV zählen nicht als Fehlalarm und stehen gesondert.\n"
    )
    w(
        "**Grenzen:** Die Nachbildungen sind je eine Datei pro Zeile der Scanner-Matrix, keine "
        "vollständigen Pakete, und stammen vom selben Team wie die Regeln. Die Erkennungsrate "
        "zeigt daher, ob jede Prüfung greift, nicht wie gut luibui unbekannte Angriffe findet.\n"
    )
    if lauf.uebersprungen or lauf.fehlgeschlagen:
        w("## Nicht vollständig gelaufen\n")
        for titel, grund in sorted(lauf.fehlgeschlagen.items()):
            w(f"- **{titel}:** fehlgeschlagen ({grund})")
        for titel, grund in sorted(lauf.uebersprungen.items()):
            w(f"- {titel}: übersprungen, {grund}")
        w("")
    if lauf.nicht_geholt:
        w("## Nicht geholt\n")
        for zeile in lauf.nicht_geholt:
            w(f"- {zeile}")
        w("")

    w("## Erkennung je Ebene\n")
    w("| Ebene | Erkannt |")
    w("|---|---|")
    ebenen: dict[str, list[Treffer]] = defaultdict(list)
    for t in b:
        ebenen[ebene_von(t.erwartet)].append(t)
    for e, items in sorted(ebenen.items()):
        w(f"| {e} | {_quote(sum(bool(t.erkannt) for t in items), len(items))} |")
    w("")
    w("## Nachbildungen\n")
    w("| Matrix | Gruppe | Erwartet | Ampel | Erkannt |")
    w("|---|---|---|---|---|")
    for t in b:
        erkannt = "ja" if t.erkannt else "**nein**"
        w(f"| {t.name} | {t.gruppe} | `{t.erwartet}` | {t.ampel} | {erkannt} |")
    w("")
    for titel, items in (("Gutartig, echte Pakete", ec), ("Gutartig, eigener Korpus", ge)):
        if not items:
            continue
        w(f"## {titel}\n")
        w("| Paket | Stand | Ampel | K/H-Befunde | Bekannte Lücken |")
        w("|---|---|---|---|---|")
        for t in items:
            ernst = "<br>".join(f"`{x}`" for x in t.ernst) or "–"
            if t.berechtigt:
                ernst += "<br>berechtigt: " + ", ".join(f"`{x}`" for x in t.berechtigt)
            w(f"| {t.name} | {t.herkunft or '–'} | {t.ampel} | {ernst} | {len(t.luecken) or '–'} |")
        w("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m luibui_scan.benchmark")
    parser.add_argument("corpus", type=Path, help="Ordner corpus/ des Repositorys")
    parser.add_argument(
        "--holen", type=Path, metavar="ORDNER", help="nur die echten Pakete holen (braucht git)"
    )
    parser.add_argument(
        "--vergleich", type=Path, metavar="ORDNER", help="mit --holen geholte Pakete prüfen"
    )
    parser.add_argument("--ausgabe", type=Path, help="Markdown hierhin schreiben")
    parser.add_argument("--stand", default="unbekannt", help="Commit von luibui für den Kopf")
    parser.add_argument(
        "--streng", action="store_true", help="Exit-Code 1, wenn ein Ziel nicht erreicht ist"
    )
    args = parser.parse_args(argv)

    if args.holen:
        fehler = hole_vergleich(args.corpus / "vergleich.json", args.holen)
        for zeile in fehler:
            print(zeile, file=sys.stderr)
        return 0

    lauf = Lauf()
    with tempfile.TemporaryDirectory(prefix="luibui-benchmark-") as tmp:
        run_fixtures(args.corpus, lauf, Path(tmp))
        if args.vergleich:
            run_vergleich(args.corpus / "vergleich.json", args.vergleich, lauf, Path(tmp))
    text = render(lauf, stand=args.stand, datum=datetime.date.today().isoformat())
    if args.ausgabe:
        args.ausgabe.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)

    code = [t for t in lauf.boesartig if ebene_von(t.erwartet) == "C"]
    ok = (
        _rate(lauf.boesartig, "erkannt") >= ZIEL_ERKENNUNG
        and _rate(code, "erkannt") >= ZIEL_ERKENNUNG_CODE
        and (not lauf.gutartig_echt or _rate(lauf.gutartig_echt, "fehlalarm") <= ZIEL_FEHLALARM)
    )
    return 1 if args.streng and not ok else 0


if __name__ == "__main__":
    sys.exit(main())
