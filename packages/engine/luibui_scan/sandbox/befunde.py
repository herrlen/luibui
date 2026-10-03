"""Sandbox protocol → findings F01–F05 (S6-6, Prüfkatalog §7).

All with Nachweisgrad ``in_sandbox_beobachtet``.

- F01 (H): DNS lookups or connections to hosts the manifest does not declare.
- F02 (K): a decoy file was read, or a decoy value shows up in traffic, a DNS name or a written
  file (then it is theft, not just curiosity).
- F03 (H): a shell started outside npm's own lifecycle scripts, or files written outside the
  package folder, ``/tmp`` and the npm cache.
- F04 (K): behaviour only with the clock turned forward (time bomb).
- F05 (K): writes to shell profiles, crontab, autostart or systemd user units.

Everything from the protocol is data from code under test: shown masked and with invisible
characters made visible, never trusted beyond the schema.
"""

import posixpath
from collections.abc import Iterable
from typing import Any

from luibui_scan.analyzers._common import finding, masked
from luibui_scan.models import Ebene, Finding, Nachweisgrad, Schwere
from luibui_scan.sandbox.koeder import KoederSatz

HOME = "/home/sandbox"
PAKET = "/paket"
ERLAUBT_SCHREIBEN = (PAKET, "/tmp", f"{HOME}/.npm", f"{HOME}/.cache")  # noqa: S108 - sandbox paths
SHELLS = frozenset({"sh", "bash", "dash", "zsh", "ash", "ksh", "fish"})
PERSISTENZ = (
    f"{HOME}/.bashrc",
    f"{HOME}/.bash_profile",
    f"{HOME}/.profile",
    f"{HOME}/.zshrc",
    f"{HOME}/.config/autostart/",
    f"{HOME}/.config/systemd/user/",
    "/var/spool/cron/",
    "/etc/cron",
    "/etc/profile",
)
MAX_BELEGE = 5


Text = tuple[str, str, str, tuple[str, ...]]
"""Title, explanation, fix, norm references."""

F01: Text = (
    "Verbindungsversuche zu nicht angegebenen Zielen",
    "In der Sandbox hat das Paket Namen aufgelöst oder Verbindungen versucht, die nicht in "
    "luibui.json unter endpunkte stehen. Die Sandbox hat kein Internet; angekommen ist nichts. "
    "Unangekündigte Ziele können Datenabfluss oder Nachladen von Code bedeuten.",
    "Alle Ziele in luibui.json unter endpunkte angeben oder die Verbindungen entfernen.",
    ("ASI02", "LLM02"),
)
F02: Text = (
    "Zugangsdaten gelesen",
    "luibui legt in der Sandbox präparierte, wertlose Zugangsdaten ab (AWS, SSH, GitHub, .env). "
    "Das Paket hat sie gelesen. Ein Paket, das fremde Zugangsdaten anfasst, ohne dass das zu "
    "seiner Aufgabe gehört, ist als Diebstahl zu behandeln.",
    "Keine Zugangsdaten außerhalb des eigenen Bedarfs lesen; benötigte Schlüssel nur über "
    "erklärte Umgebungsvariablen beziehen.",
    ("ASI03", "LLM02"),
)
F02_ABFLUSS = " Es hat sie außerdem in Verbindungen, DNS-Namen oder Dateien weitergegeben."
F03: Text = (
    "Shell gestartet oder außerhalb des Paketordners geschrieben",
    "In der Sandbox hat das Paket eine Shell gestartet (nicht als npm-Skript) oder Dateien "
    "außerhalb seines Ordners, /tmp und des npm-Caches geschrieben.",
    "Ohne Shell auskommen und nur im eigenen Ordner schreiben.",
    ("ASI05",),
)
F04: Text = (
    "Anderes Verhalten mit vorgedrehter Uhr",
    "luibui führt das Paket zweimal aus, einmal mit vorgestellter Uhr. Nur dann hat es "
    "zusätzliche Verbindungen, Prozesse oder Schreibzugriffe gezeigt. So verhalten sich "
    "Zeitbomben, die erst nach einer Prüfung aktiv werden.",
    "Datumsabhängige Logik entfernen oder offenlegen und begründen.",
    ("ASI10",),
)
F05: Text = (
    "Schreibt in Autostart, Profile oder Crontab",
    "In der Sandbox hat das Paket in Dateien geschrieben, die bei jedem Start einer Shell oder "
    "des Systems ausgeführt werden. Damit setzt es sich dauerhaft fest.",
    "Keine Profile, Crontabs oder Autostart-Einträge verändern.",
    ("ASI06", "ASI10"),
)


def _f(
    rule: str,
    schwere: Schwere,
    titel: str,
    erklaerung: str,
    fix: str,
    norm: tuple[str, ...],
    beleg: str,
) -> Finding:
    return finding(
        rule_id=rule,
        ebene=Ebene.F,
        schwere=schwere,
        titel=titel,
        erklaerung=erklaerung,
        datei=None,
        zeile=None,
        beleg=beleg,
        fix=fix,
        fix_prompt=f"{titel}. {fix}",
        normbezug=norm,
        nachweisgrad=Nachweisgrad.IN_SANDBOX_BEOBACHTET,
    )


def _pfad(roh: str) -> str:
    p = roh.replace("~", HOME, 1) if roh.startswith("~") else roh
    return posixpath.normpath(p)


def _koeder_pfad(k: str) -> str:
    return _pfad(k) if k.startswith("~") else posixpath.normpath(posixpath.join(PAKET, k))


def _host(ziel: str) -> str:
    return ziel.strip().rstrip(".").lower()


def _deklariert(manifest: dict[str, Any] | None) -> set[str]:
    endpunkte = (manifest or {}).get("endpunkte")
    hosts = set()
    for e in endpunkte if isinstance(endpunkte, list) else []:
        if isinstance(e, dict) and isinstance(e.get("host"), str):
            hosts.add(_host(e["host"]))
    return hosts


def _erlaubt(host: str, deklariert: set[str]) -> bool:
    return any(host == d or host.endswith("." + d) for d in deklariert)


def _zeilen(eintraege: Iterable[str]) -> str:
    liste = sorted(set(eintraege))
    mehr = len(liste) - MAX_BELEGE
    out = [masked(x, 200) for x in liste[:MAX_BELEGE]]
    if mehr > 0:
        out[-1] += f" (und {mehr} weitere)"
    return "\n".join(out)


def _signatur(lauf: dict[str, Any]) -> set[str]:
    """What a run did, as comparable strings (for F04)."""
    out = {f"verbindung {_host(v['ziel'])}" for v in lauf["verbindungen"]}
    out |= {f"prozess {posixpath.basename(p['befehl'])}" for p in lauf["prozesse"]}
    out |= {f"schreibt {_pfad(d['pfad'])}" for d in lauf["dateien"] if d["zugriff"] == "schreiben"}
    return out


def befunde(
    protokoll: dict[str, Any], koeder: KoederSatz, manifest: dict[str, Any] | None
) -> list[Finding]:
    laeufe = protokoll["laeufe"]
    deklariert = _deklariert(manifest)
    koeder_pfade = {_koeder_pfad(k) for k in koeder.pfade()}
    out: list[Finding] = []

    fremde_hosts: set[str] = set()
    gelesen: set[str] = set()
    abfluss: set[str] = set()
    shells: set[str] = set()
    fremd_geschrieben: set[str] = set()
    persistenz: set[str] = set()
    for lauf in laeufe:
        for v in lauf["verbindungen"]:
            host = _host(v["ziel"])
            if not _erlaubt(host, deklariert):
                fremde_hosts.add(f"{v['art']} {host}" + (f":{v['port']}" if v.get("port") else ""))
            for wert, art in koeder.werte.items():
                if wert in v["ziel"] or wert in v.get("daten_anfang", ""):
                    abfluss.add(f"{art} an {host}")
        for d in lauf["dateien"]:
            pfad = _pfad(d["pfad"])
            if d["zugriff"] == "lesen" and pfad in koeder_pfade:
                gelesen.add(pfad.replace(HOME, "~", 1))
            if d["zugriff"] == "schreiben":
                for wert, art in koeder.werte.items():
                    if wert in d.get("inhalt_anfang", ""):
                        abfluss.add(f"{art} in {pfad}")
                if any(pfad.startswith(p) for p in PERSISTENZ):
                    persistenz.add(pfad)
                elif not any(pfad == p or pfad.startswith(p + "/") for p in ERLAUBT_SCHREIBEN):
                    fremd_geschrieben.add(pfad)
        for p in lauf["prozesse"]:
            if posixpath.basename(p["befehl"]) in SHELLS and not p["skript"]:
                shells.add(" ".join([p["befehl"], *p["argumente"]])[:200])

    if fremde_hosts:
        out.append(_f("LB-F01-netzwerk", Schwere.H, *F01, _zeilen(fremde_hosts)))
    if gelesen or abfluss:
        titel, erklaerung, fix, norm = F02
        if abfluss:
            titel += " und weitergegeben"
            erklaerung += F02_ABFLUSS
        belege = [*(f"gelesen {g}" for g in gelesen), *(f"weitergegeben: {a}" for a in abfluss)]
        out.append(_f("LB-F02-koeder", Schwere.K, titel, erklaerung, fix, norm, _zeilen(belege)))
    if shells or fremd_geschrieben:
        belege = [*(f"Shell: {s}" for s in shells), *(f"schreibt {p}" for p in fremd_geschrieben)]
        out.append(_f("LB-F03-system", Schwere.H, *F03, _zeilen(belege)))
    echt = [lauf for lauf in laeufe if lauf["uhr"] == "echt"]
    vorgedreht = [lauf for lauf in laeufe if lauf["uhr"] == "vorgedreht"]
    if echt and vorgedreht:
        normal = set().union(*(_signatur(lauf) for lauf in echt))
        spaeter = set().union(*(_signatur(lauf) for lauf in vorgedreht))
        if spaeter - normal:
            out.append(_f("LB-F04-zeitbombe", Schwere.K, *F04, _zeilen(spaeter - normal)))
    if persistenz:
        out.append(_f("LB-F05-persistenz", Schwere.K, *F05, _zeilen(persistenz)))
    return out
