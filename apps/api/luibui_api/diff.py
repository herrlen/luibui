"""What a new version may do that the previous one did not (Prüfkatalog H01, S4-6).

Compares the two manifests (``luibui.json``) of consecutive published versions: rights that were
switched on, new file paths, environment variables, endpoints, countries and data categories.
Only additions count; what a version gives up is no risk for its users. The result is stored
with the version and signed with it, the package page shows it and ``luibui-install`` asks
again before an update that brings any of it.
"""

from typing import Any

RECHTE = {"netzwerk": "Netzwerkzugriff", "shell": "Shell-Befehle", "zugangsdaten": "Zugangsdaten"}


def _d(wert: object) -> dict[str, Any]:
    return wert if isinstance(wert, dict) else {}


def _liste(wert: object) -> list[str]:
    return [str(x) for x in wert] if isinstance(wert, list) else []


def _endpunkte(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    roh = manifest.get("endpunkte")
    eintraege = roh if isinstance(roh, list) else []
    return {str(e.get("host")): e for e in eintraege if isinstance(e, dict) and e.get("host")}


def aenderungen(alt: dict[str, Any] | None, neu: dict[str, Any]) -> list[dict[str, str]]:
    """``[{"art": "recht"|"endpunkt"|"daten", "text": "…"}]``; empty for the first version."""
    if alt is None:
        return []
    out: list[dict[str, str]] = []
    ra, rn = _d(alt.get("rechte")), _d(neu.get("rechte"))
    for schluessel, name in RECHTE.items():
        if rn.get(schluessel) is True and ra.get(schluessel) is not True:
            out.append({"art": "recht", "text": f"{name} neu"})
    da, dn = _d(ra.get("dateien")), _d(rn.get("dateien"))
    for art, wort in (("lesen", "Liest"), ("schreiben", "Schreibt")):
        for pfad in sorted(set(_liste(dn.get(art))) - set(_liste(da.get(art)))):
            out.append({"art": "recht", "text": f"{wort} neu: {pfad[:200]}"})
    for var in sorted(
        set(_liste(rn.get("umgebungsvariablen"))) - set(_liste(ra.get("umgebungsvariablen")))
    ):
        out.append({"art": "recht", "text": f"Liest neu die Umgebungsvariable {var[:100]}"})
    ea, en = _endpunkte(alt), _endpunkte(neu)
    for host in sorted(en):
        land = str(en[host].get("land", "?"))[:10]
        if host not in ea:
            out.append({"art": "endpunkt", "text": f"Neuer Endpunkt {host[:253]} ({land})"})
        elif str(ea[host].get("land")) != str(en[host].get("land")):
            vorher = str(ea[host].get("land", "?"))[:10]
            out.append({"art": "endpunkt", "text": f"{host[:253]} jetzt in {land} statt {vorher}"})
        else:
            neu_daten = set(_liste(en[host].get("datenkategorien"))) - set(
                _liste(ea[host].get("datenkategorien"))
            )
            for kategorie in sorted(neu_daten):
                out.append(
                    {"art": "daten", "text": f"Schickt neu {kategorie[:60]} an {host[:253]}"}
                )
    for kategorie in sorted(
        set(_liste(neu.get("datenkategorien"))) - set(_liste(alt.get("datenkategorien")))
    ):
        out.append({"art": "daten", "text": f"Verarbeitet neu: {kategorie[:60]}"})
    return out
