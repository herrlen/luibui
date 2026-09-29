"""The report as PDF (S3-11), standard or detail.

Standard: cover with traffic lights, grade, scope, scan type and date, then one line per finding.
Detail: every finding opened up as on the report page (explanation, evidence, fix, fix prompt).
Built on the server with ReportLab and fonts shipped with the API; nothing is loaded from outside.

Everything taken from the report is package content or derived from it. It is escaped before it
reaches ReportLab's paragraph markup, and characters that would stay invisible (zero-width,
direction marks, control characters) or that the font cannot show are written as ``[U+XXXX]``,
so evidence can never hide text in the PDF (CLAUDE.md rules 6 and 12).
"""

import io
import re
import unicodedata
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import Any, Literal
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    CondPageBreak,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

Umfang = Literal["standard", "detail"]

SCHRIFTEN = Path(__file__).parent / "pdf_schriften"
BERLIN = ZoneInfo("Europe/Berlin")

HAFTUNG = (
    "Automatische Prüfung zum angegebenen Zeitpunkt. Keine bekannten Befunde heißt nicht, dass das "
    "Paket unbedenklich ist. luibui übernimmt keine Gewähr für Vollständigkeit und Richtigkeit."
)
OHNE_GEWAEHR = "Schnellscan mit eingeschränktem Umfang, ohne Gewähr"

REIHENFOLGE = ("K", "H", "M", "N", "I")
SCHWERE_TEXT = {"K": "Kritisch", "H": "Hoch", "M": "Mittel", "N": "Niedrig", "I": "Info"}
AMPEL_TEXT = {
    "gruen": "Grün",
    "gelb": "Gelb",
    "rot": "Rot",
    "gesperrt": "Gesperrt",
    "nicht_bewertet": "nicht bewertet",
}
FREIGABE_TEXT = {
    "freigegeben": "freigegeben",
    "pruefung_noetig": "Prüfung nötig",
    "blockiert": "blockiert",
}
SCAN_ART = {"schnell": "Schnellscan", "intensiv": "Intensivscan", "lokal": "Lokale Prüfung"}
UMFANG_TEXT = {
    "paket": "Paket",
    "auswahl": "Dateiauswahl ohne Manifest",
    "einzeldatei": "Einzeldatei",
}

# The colours of the web interface (apps/web/app/globals.css).
INK = colors.HexColor("#15171c")
MUTED = colors.HexColor("#5a5f6a")
LINIE = colors.HexColor("#e2ded3")
GRUND = colors.HexColor("#f5f3ec")
PETROL = colors.HexColor("#0e5e5b")
AMPEL_FARBE = {
    "gruen": (colors.HexColor("#e3f1e8"), colors.HexColor("#17613c")),
    "gelb": (colors.HexColor("#fbf0d5"), colors.HexColor("#7a5200")),
    "rot": (colors.HexColor("#fbe4e1"), colors.HexColor("#a3261b")),
    "gesperrt": (colors.HexColor("#5c1a13"), colors.white),
    "nicht_bewertet": (LINIE, colors.HexColor("#3f434c")),
}
SCHWERE_FARBE = {
    "K": (colors.HexColor("#5c1a13"), colors.white),
    "H": (colors.HexColor("#fbe4e1"), colors.HexColor("#a3261b")),
    "M": (colors.HexColor("#fbf0d5"), colors.HexColor("#7a5200")),
    "N": (colors.HexColor("#efede6"), colors.HexColor("#3f434c")),
    "I": (colors.HexColor("#efede6"), colors.HexColor("#3f434c")),
}


@cache
def _schriften() -> dict[str, frozenset[int]]:
    """Register the fonts once; return the code points each font can show."""
    abdeckung = {}
    for name, datei in (
        ("Plex", "IBMPlexSans-Regular.ttf"),
        ("Plex-SemiBold", "IBMPlexSans-SemiBold.ttf"),
        ("PlexMono", "IBMPlexMono-Regular.ttf"),
    ):
        font = TTFont(name, str(SCHRIFTEN / datei))
        pdfmetrics.registerFont(font)
        abdeckung[name] = frozenset(font.face.charToGlyph)
    return abdeckung


def _sichtbar(text: str, schrift: str) -> str:
    """Invisible and unprintable characters become ``[U+XXXX]``; newlines and tabs stay."""
    zeichen = _schriften()[schrift]
    out = []
    for ch in text:
        if ch in "\n\t":
            out.append(ch)
        elif unicodedata.category(ch) in ("Cc", "Cf", "Co", "Cs", "Zl", "Zp") or (
            ord(ch) not in zeichen and not ch.isspace()
        ):
            out.append(f"[U+{ord(ch):04X}]")
        else:
            out.append(" " if ch.isspace() else ch)
    return "".join(out)


def _t(value: Any, schrift: str = "Plex") -> str:
    """Package text, safe for paragraph markup."""
    return escape(_sichtbar(str(value if value is not None else ""), schrift))


def _mit_code(value: Any) -> str:
    """Engine texts mark names with backticks: shown in the mono font, still escaped."""
    teile = re.split(r"`([^`\n]+)`", str(value or ""))
    return "".join(
        f'<font name="PlexMono">{_t(teil, "PlexMono")}</font>' if i % 2 else _t(teil)
        for i, teil in enumerate(teile)
    )


def _block(value: Any) -> str:
    """Evidence and prompts: mono, line breaks and indentation kept."""
    zeilen = _t(value, "PlexMono").split("\n")
    return "<br/>".join(re.sub(r"^ +", lambda m: "&nbsp;" * len(m.group()), z) for z in zeilen)


def _datum(iso: Any) -> str:
    try:
        wert = datetime.fromisoformat(str(iso))
    except ValueError:
        return str(iso or "")
    if wert.tzinfo is None:
        wert = wert.replace(tzinfo=UTC)
    return wert.astimezone(BERLIN).strftime("%d.%m.%Y, %H:%M")


def _stile() -> dict[str, ParagraphStyle]:
    _schriften()
    basis = ParagraphStyle("basis", fontName="Plex", fontSize=9.5, leading=13.5, textColor=INK)
    return {
        "basis": basis,
        "klein": ParagraphStyle("klein", parent=basis, fontSize=8, leading=11, textColor=MUTED),
        "titel": ParagraphStyle(
            "titel", parent=basis, fontName="Plex-SemiBold", fontSize=22, leading=27
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=basis,
            fontName="Plex-SemiBold",
            fontSize=13,
            leading=17,
            spaceBefore=10,
            spaceAfter=5,
        ),
        "h3": ParagraphStyle(
            "h3", parent=basis, fontName="Plex-SemiBold", fontSize=10.5, leading=14
        ),
        "mono": ParagraphStyle(
            "mono", parent=basis, fontName="PlexMono", fontSize=8, leading=11, wordWrap="CJK"
        ),
        "rechts": ParagraphStyle("rechts", parent=basis, alignment=TA_RIGHT),
        "marke": ParagraphStyle(
            "marke", parent=basis, fontName="Plex-SemiBold", fontSize=8.5, leading=11
        ),
    }


def _marke(text: str, farbe: tuple[colors.Color, colors.Color], stil: ParagraphStyle) -> Table:
    """A label with background: the word is always there, colour is never alone."""
    hinten, vorne = farbe
    p = Paragraph(f'<font color="{vorne.hexval()}">{escape(text)}</font>', stil)
    tabelle = Table([[p]], hAlign="LEFT")
    tabelle.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), hinten),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ]
        )
    )
    return tabelle


def _kasten(inhalt: list[Any], breite: float, hintergrund: colors.Color = GRUND) -> Table:
    tabelle = Table([[inhalt]], colWidths=[breite])
    tabelle.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), hintergrund),
                ("BOX", (0, 0), (-1, -1), 0.5, LINIE),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return tabelle


def _ort(b: dict[str, Any]) -> str:
    datei = b.get("datei")
    if not datei:
        return "ganzes Paket"
    return f"{datei}:{b['zeile']}" if isinstance(b.get("zeile"), int) else str(datei)


def _sortiert(befunde: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rang = {s: i for i, s in enumerate(REIHENFOLGE)}
    return sorted(
        (b for b in befunde if isinstance(b, dict)),
        key=lambda b: (
            rang.get(str(b.get("schwere")), 9),
            str(b.get("datei") or ""),
            b.get("zeile") or 0,
        ),
    )


def _deckblatt(r: dict[str, Any], s: dict[str, ParagraphStyle], breite: float) -> list[Any]:
    paket = r.get("paket") or {}
    ampeln = r.get("ampeln") or {}
    gesamt = str(ampeln.get("gesamt") or "nicht_bewertet")
    teile: list[Any] = [Paragraph("Prüfbericht", s["titel"]), Spacer(1, 2)]
    name = _t(paket.get("name") or "Paket", "PlexMono")
    version = f" · v{_t(paket.get('version'), 'PlexMono')}" if paket.get("version") else ""
    teile.append(Paragraph(f'<font name="PlexMono">{name}{version}</font>', s["basis"]))
    art = SCAN_ART.get(str(r.get("scan_art")), str(r.get("scan_art") or ""))
    umfang = UMFANG_TEXT.get(str(r.get("pruefumfang")), str(r.get("pruefumfang") or ""))
    zeile = f"{art} · {umfang} · geprüft am {_datum(r.get('geprueft_am'))}"
    if (n := paket.get("dateien")) is not None:
        zeile += f" · {n} {'Datei' if n == 1 else 'Dateien'}"
    teile += [Paragraph(escape(zeile), s["klein"]), Spacer(1, 10)]

    def zelle(titel: str, wert: Any) -> list[Any]:
        return [Paragraph(escape(titel), s["klein"]), Spacer(1, 2), wert]

    def ampel(wert: Any) -> Table:
        w = str(wert or "nicht_bewertet")
        return _marke(
            AMPEL_TEXT.get(w, w), AMPEL_FARBE.get(w, AMPEL_FARBE["nicht_bewertet"]), s["marke"]
        )

    note = Paragraph(
        f'<font name="Plex-SemiBold" size="18">{escape(str(r.get("note", "–")))}</font>'
        f'<font color="{MUTED.hexval()}"> /100</font>',
        ParagraphStyle("note", parent=s["basis"], leading=20),
    )
    freigabe = str(r.get("freigabe") or "")
    uebersicht = Table(
        [
            [
                zelle("Gesamt", ampel(gesamt)),
                zelle("Sicherheit", ampel(ampeln.get("sicherheit"))),
                zelle("DSGVO", ampel(ampeln.get("dsgvo"))),
                zelle("Note", note),
                zelle(
                    "Freigabe", Paragraph(escape(FREIGABE_TEXT.get(freigabe, freigabe)), s["h3"])
                ),
            ]
        ],
        colWidths=[breite / 5] * 5,
        hAlign="LEFT",
    )
    uebersicht.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, LINIE),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    teile.append(uebersicht)
    if gesamt == "gruen":
        text = f"Keine bekannten Befunde, geprüft am {_datum(r.get('geprueft_am'))}."
        teile += [Spacer(1, 6), Paragraph(escape(text), s["basis"])]
    for h in r.get("hinweise") or []:
        teile += [Spacer(1, 4), Paragraph(_mit_code(h), s["klein"])]
    return teile


def _befunde_liste(
    befunde: list[dict[str, Any]], s: dict[str, ParagraphStyle], breite: float
) -> Table:
    zeilen: list[list[Any]] = [
        [Paragraph(escape(t), s["klein"]) for t in ("Schwere", "Befund", "Ort")]
    ]
    stil = [
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINIE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for b in befunde:
        schwere = str(b.get("schwere"))
        zeilen.append(
            [
                _marke(
                    SCHWERE_TEXT.get(schwere, schwere),
                    SCHWERE_FARBE.get(schwere, SCHWERE_FARBE["I"]),
                    s["marke"],
                ),
                [
                    Paragraph(_t(b.get("titel")), s["h3"]),
                    Paragraph(_t(b.get("rule_id"), "PlexMono"), s["klein"]),
                ],
                Paragraph(_t(_ort(b), "PlexMono"), s["mono"]),
            ]
        )
    tabelle = Table(zeilen, colWidths=[24 * mm, breite - 24 * mm - 52 * mm, 52 * mm], repeatRows=1)
    tabelle.setStyle(TableStyle(stil))
    return tabelle


def _befund_detail(b: dict[str, Any], s: dict[str, ParagraphStyle], breite: float) -> list[Any]:
    schwere = str(b.get("schwere"))
    kopf = Table(
        [
            [
                _marke(
                    SCHWERE_TEXT.get(schwere, schwere),
                    SCHWERE_FARBE.get(schwere, SCHWERE_FARBE["I"]),
                    s["marke"],
                ),
                Paragraph(_t(b.get("titel")), s["h3"]),
            ]
        ],
        colWidths=[24 * mm, breite - 24 * mm],
        hAlign="LEFT",
    )
    kopf.setStyle(
        TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)])
    )
    meta = [
        _t(b.get("rule_id"), "PlexMono"),
        "DSGVO" if b.get("achse") == "dsgvo" else "Sicherheit",
    ]
    if b.get("hochgestuft_von"):
        von = str(b.get("hochgestuft_von"))
        meta.append(f"hochgestuft von {escape(SCHWERE_TEXT.get(von, von))}")
    teile: list[Any] = [
        kopf,
        Spacer(1, 3),
        Paragraph(
            f'<font name="PlexMono">{_t(_ort(b), "PlexMono")}</font> · {" · ".join(meta)}',
            s["klein"],
        ),
        Spacer(1, 4),
        Paragraph(_mit_code(b.get("erklaerung")), s["basis"]),
    ]
    if b.get("beleg"):
        teile += [
            Spacer(1, 4),
            Paragraph(f"Beleg aus {_t(_ort(b), 'PlexMono')}", s["klein"]),
            _kasten([Paragraph(_block(b.get("beleg")), s["mono"])], breite),
        ]
    if b.get("fix"):
        teile += [
            Spacer(1, 4),
            Paragraph(
                f'<font name="Plex-SemiBold">So behebst du es:</font> {_mit_code(b.get("fix"))}',
                s["basis"],
            ),
        ]
    if b.get("fix_prompt"):
        teile += [
            Spacer(1, 4),
            Paragraph("Prompt für Claude Code oder andere Coding-Agents:", s["klein"]),
            _kasten([Paragraph(_block(b.get("fix_prompt")), s["mono"])], breite),
        ]
    normen = [n for n in b.get("normbezug") or [] if n]
    if normen:
        teile += [Spacer(1, 3), Paragraph("Bezug: " + _t(", ".join(map(str, normen))), s["klein"])]
    return [CondPageBreak(40 * mm), KeepTogether(teile[:5]), *teile[5:], Spacer(1, 12)]


def dateiname(r: dict[str, Any], umfang: Umfang) -> str:
    """Like the other downloads: package name and date, only characters safe in a header."""
    name = str((r.get("paket") or {}).get("name") or "")
    paket = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-.")[:60] or "paket"
    tag = str(r.get("geprueft_am") or "")[:10]
    datum = tag if re.fullmatch(r"\d{4}-\d{2}-\d{2}", tag) else "bericht"
    zusatz = "-detail" if umfang == "detail" else ""
    return f"luibui-{paket}-{datum}{zusatz}.pdf"


def bericht_als_pdf(
    report: dict[str, Any], umfang: Umfang = "standard", *, fest: bool = False
) -> bytes:
    """``fest``: same bytes for the same report (no creation time, fixed IDs), for the example
    PDF on the website that a test compares."""
    s = _stile()
    puffer = io.BytesIO()
    rand = 18 * mm
    breite = A4[0] - 2 * rand
    schnell = report.get("scan_art") == "schnell"
    paketname = _sichtbar(str((report.get("paket") or {}).get("name") or ""), "Plex")[:70]

    def seite(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        canvas.setFont("Plex-SemiBold", 8.5)
        canvas.setFillColor(PETROL)
        canvas.drawString(rand, A4[1] - 12 * mm, "luibui")
        canvas.setFont("Plex", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(rand + 11 * mm, A4[1] - 12 * mm, f"Prüfbericht · {paketname}")
        if schnell:
            canvas.setFillColor(AMPEL_FARBE["gelb"][1])
            canvas.setFont("Plex-SemiBold", 8)
            canvas.drawRightString(A4[0] - rand, A4[1] - 12 * mm, OHNE_GEWAEHR)
        canvas.setStrokeColor(LINIE)
        canvas.line(rand, A4[1] - 14 * mm, A4[0] - rand, A4[1] - 14 * mm)
        canvas.line(rand, 16 * mm, A4[0] - rand, 16 * mm)
        canvas.setFillColor(MUTED)
        canvas.setFont("Plex", 6.8)
        for i, zeile in enumerate(simpleSplit(HAFTUNG, "Plex", 6.8, breite - 16 * mm)[:2]):
            canvas.drawString(rand, (12 - 3 * i) * mm, zeile)
        canvas.drawRightString(A4[0] - rand, 9 * mm, f"Seite {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        puffer,
        pagesize=A4,
        leftMargin=rand,
        rightMargin=rand,
        topMargin=22 * mm,
        bottomMargin=22 * mm,
        title=f"Prüfbericht {paketname}",
        author="luibui",
        subject="Prüfbericht" + (" (Schnellscan, ohne Gewähr)" if schnell else ""),
        invariant=1 if fest else 0,
    )
    teile = _deckblatt(report, s, breite)
    befunde = _sortiert(report.get("befunde") or [])
    zaehlung = ", ".join(
        f"{n} {SCHWERE_TEXT[k]}"
        for k in REIHENFOLGE
        if (n := sum(1 for b in befunde if b.get("schwere") == k))
    )
    teile.append(Paragraph(f"Befunde ({len(befunde)})", s["h2"]))
    if not befunde:
        teile.append(Paragraph("Keine Befunde.", s["basis"]))
    else:
        teile += [Paragraph(escape(zaehlung), s["klein"]), Spacer(1, 6)]
        if umfang == "detail":
            for b in befunde:
                teile += _befund_detail(b, s, breite)
        else:
            teile.append(_befunde_liste(befunde, s, breite))
            teile += [
                Spacer(1, 6),
                Paragraph(
                    "Erklärung, Beleg und Fix zu jedem Befund stehen im Detailbericht.", s["klein"]
                ),
            ]
    nicht = [n for n in report.get("nicht_geprueft") or [] if isinstance(n, dict)]
    if nicht:
        teile.append(Paragraph("Nicht geprüft", s["h2"]))
        for eintrag in nicht:
            text = f"{_t(eintrag.get('pruefung'))}: {_mit_code(eintrag.get('grund'))}"
            teile.append(Paragraph(text, s["basis"]))
    if umfang == "detail" and report.get("abdeckung"):
        teile.append(Paragraph("Was geprüft wurde", s["h2"]))
        for a in report.get("abdeckung") or []:
            if not isinstance(a, dict):
                continue
            geprueft = ", ".join(map(str, a.get("geprueft") or [])) or "–"
            offen = ", ".join(map(str, a.get("offen") or []))
            art = f'<font name="Plex-SemiBold">{_t(a.get("dateiart"))}</font>'
            anzahl = a.get("dateien")
            text = f"{art} · {_t(anzahl)} {'Datei' if anzahl == 1 else 'Dateien'}: {_t(geprueft)}"
            if offen:
                text += f". Nicht geprüft: {_t(offen)}"
            teile += [Paragraph(text, s["basis"]), Spacer(1, 3)]
    if schnell:  # also in every page head; here once more in full words
        teile += [Spacer(1, 10), Paragraph(escape(OHNE_GEWAEHR + "."), s["basis"])]
    doc.build(teile, onFirstPage=seite, onLaterPages=seite)
    return puffer.getvalue()


def _beispiel() -> None:
    """``python -m luibui_api.pdf <beispielbericht.json> <ziel.pdf>``: the example PDF."""
    import json
    import sys

    quelle, ziel = sys.argv[1:3]
    report = json.loads(Path(quelle).read_text(encoding="utf-8"))
    Path(ziel).write_bytes(bericht_als_pdf(report, "detail", fest=True))


if __name__ == "__main__":
    _beispiel()
