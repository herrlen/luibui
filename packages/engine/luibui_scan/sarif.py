"""SARIF 2.1.0 of a report, for GitHub Code Scanning and other SARIF viewers (S2-12, S5-5).

The same conversion as ``apps/web/lib/sarif.ts`` (download in the browser); both are tested
against ``spec/tests/sarif-referenz.json`` so they cannot drift apart. Only plain-text message
fields are used: package content never reaches a Markdown renderer.
"""

from typing import Any
from urllib.parse import quote

SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
PAKET_ANKER = "luibui.json"
OHNE_GEWAEHR = "Schnellscan: eingeschränkter Umfang, ohne Gewähr."

LEVEL = {"K": "error", "H": "error", "M": "warning", "N": "note", "I": "note"}
# GitHub sorts security alerts by this score (critical ≥ 9, high ≥ 7, medium ≥ 4, low > 0).
SECURITY_SEVERITY = {"K": "9.5", "H": "7.5", "M": "5.0", "N": "2.0", "I": "0.1"}

BEFUND_STATUS_TEXT = {
    "offen": "Offen",
    "behoben": "Behoben",
    "akzeptiert": "Akzeptiert",
    "bestritten": "Bestritten",
}
MODERATION_TEXT = {"bestritten": "Vom Autor bestritten", "fehlalarm": "Fehlalarm, Regel angepasst"}


def status_label(st: dict[str, Any] | None) -> str:
    if not st or st.get("status") == "offen":
        return ""
    if st.get("moderation"):
        m = str(st["moderation"])
        return MODERATION_TEXT.get(m, m)
    s = str(st.get("status", ""))
    return BEFUND_STATUS_TEXT.get(s, s)


def _unterdrueckung(st: dict[str, Any] | None) -> list[dict[str, Any]] | None:
    """SARIF suppressions (§3.35): accepted = kept on purpose or a confirmed false alarm;
    underReview = disputed, not decided; rejected = luibui kept the finding."""
    if not st:
        return None
    if st.get("status") == "akzeptiert" or st.get("moderation") == "fehlalarm":
        status = "accepted"
    elif st.get("status") == "bestritten":
        status = "rejected" if st.get("moderation") == "bestritten" else "underReview"
    else:
        return None
    out: dict[str, Any] = {"kind": "external", "status": status}
    if st.get("begruendung"):
        out["justification"] = st["begruendung"]
    return [out]


def _datei_uri(pfad: str) -> str:
    """A relative URI reference: each path segment encoded like encodeURIComponent."""
    return "/".join(quote(t, safe="!'()*-._~") for t in pfad.lstrip("/").split("/"))


def hinweise(b: dict[str, Any]) -> list[str]:
    """Report hints, with the quick-scan disclaimer first (CLAUDE.md rule 12)."""
    h = list(b.get("hinweise") or [])
    if b.get("scan_art") == "schnell" and OHNE_GEWAEHR not in h:
        return [OHNE_GEWAEHR, *h]
    return h


def bericht_als_sarif(
    b: dict[str, Any], status: dict[str, dict[str, Any]] | None = None
) -> dict[str, Any]:
    """``status``: the owner's finding status by fingerprint (S3-7), only for the owner."""
    regeln: dict[str, int] = {}
    rules: list[dict[str, Any]] = []
    results = []
    for x in b.get("befunde") or []:
        index = regeln.get(x["rule_id"])
        if index is None:
            index = len(rules)
            regeln[x["rule_id"]] = index
            rules.append(
                {
                    "id": x["rule_id"],
                    "shortDescription": {"text": x["titel"]},
                    "fullDescription": {"text": x["erklaerung"]},
                    "help": {"text": x["fix"]},
                    "properties": {
                        "tags": [x["achse"], f"ebene-{x['ebene']}", *x["normbezug"]],
                        "security-severity": SECURITY_SEVERITY[x["schwere"]],
                    },
                }
            )
        st = (status or {}).get(x["fingerprint"]) if x.get("fingerprint") else None
        r: dict[str, Any] = {}
        unterdrueckt = _unterdrueckung(st)
        if unterdrueckt:
            r["suppressions"] = unterdrueckt
        zeile = x.get("zeile")
        properties: dict[str, Any] = {
            "schwere": x["schwere"],
            "achse": x["achse"],
            "nachweisgrad": x["nachweisgrad"],
        }
        if x.get("beleg"):
            properties["beleg"] = x["beleg"]
        properties["fix_prompt"] = x["fix_prompt"]
        if status_label(st):
            properties["luibui_status"] = status_label(st)
        r |= {
            "ruleId": x["rule_id"],
            "ruleIndex": index,
            "level": LEVEL[x["schwere"]],
            "message": {"text": f"{x['titel']}: {x['erklaerung']}"},
            # GitHub Code Scanning rejects results without a location. Findings about the
            # whole package are anchored at its manifest, line 1.
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": _datei_uri(x["datei"]) if x.get("datei") else PAKET_ANKER
                        },
                        "region": {
                            "startLine": zeile if x.get("datei") and zeile and zeile > 0 else 1
                        },
                    }
                }
            ],
            "properties": properties,
        }
        results.append(r)
    return {
        "$schema": SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "luibui",
                        "version": b.get("engine_version"),
                        "informationUri": "https://luibui.com",
                        "rules": rules,
                    }
                },
                "results": results,
                "properties": {
                    "scan_art": b.get("scan_art"),
                    "pruefumfang": b.get("pruefumfang"),
                    "paket": (b.get("paket") or {}).get("name"),
                    "geprueft_am": b.get("geprueft_am"),
                    "ampeln": b.get("ampeln"),
                    "note": b.get("note"),
                    "freigabe": b.get("freigabe"),
                    "hinweise": hinweise(b),
                },
            }
        ],
    }
