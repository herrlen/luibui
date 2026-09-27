"""Analyzer B – Inhalte, versteckte Inhalte (Prüfkatalog B01–B07, S1-6).

Finds text that people do not see but a language model reads. One finding per file and check,
with the number of hits, so a file full of hidden characters does not flood the report.
"""

import base64
import binascii
import re
import unicodedata
from collections.abc import Iterator

from luibui_scan.analyzers._common import TextFile, finding, text_files, visible
from luibui_scan.analyzers.base import AnalyzerInfo
from luibui_scan.analyzers.registry import register
from luibui_scan.context import ScanContext
from luibui_scan.models import Ebene, Finding, Schwere

NORM_INJECTION = ("OWASP-ASI01", "OWASP-LLM01")

# --- B01 Unicode tags ------------------------------------------------------------------------

_TAGS = re.compile("[\U000e0000-\U000e007f]+")


def _b01(f: TextFile) -> Iterator[Finding]:
    hits = list(_TAGS.finditer(f.text))
    if not hits:
        return
    count = sum(len(m.group()) for m in hits)
    hidden = "".join(
        chr(ord(c) - 0xE0000) for m in hits for c in m.group() if 0x20 <= ord(c) - 0xE0000 < 0x7F
    )
    line = f.line_of(hits[0].start())
    beleg = visible(
        _TAGS.sub(lambda m: f"[{len(m.group())} unsichtbare Zeichen]", f.line_text(line))
    )
    if hidden:
        beleg += "\nverborgen: " + visible(hidden, 200)
    yield finding(
        rule_id="LB-B01-unicode-tags",
        ebene=Ebene.B,
        schwere=Schwere.K,
        titel="Unsichtbare Anweisung in Unicode-Tag-Zeichen",
        erklaerung=(
            f"Die Datei enthält {count} Unicode-Tag-Zeichen (U+E0000 bis U+E007F). Menschen sehen "
            "sie nicht, ein Sprachmodell liest sie als Text. So werden Anweisungen versteckt."
        ),
        datei=f.path,
        zeile=line,
        beleg=beleg,
        fix="Alle Zeichen von U+E0000 bis U+E007F aus der Datei entfernen.",
        fix_prompt=(
            f"Entferne in {f.path} alle Unicode-Tag-Zeichen (U+E0000 bis U+E007F) und prüfe, "
            "ob der sichtbare Text danach noch vollständig und gewollt ist."
        ),
        normbezug=NORM_INJECTION,
    )


# --- B02 zero-width and invisible format characters --------------------------------------------

_INVISIBLE = frozenset("​‌‍⁠⁡⁢⁣⁤᠎­")
_VARIATION_SUPPLEMENT = (0xE0100, 0xE01EF)
_RTL_OR_INDIC = re.compile(r"[֐-ࣿऀ-෿יִ-﷿ﹰ-﻿]")


def _pictographic(c: str) -> bool:
    return ord(c) >= 0x1F000 or unicodedata.category(c) == "So" or c in "️⃣"


def _suspicious_invisible(text: str, i: int) -> bool:
    c = text[i]
    prev = text[i - 1] if i else ""
    nxt = text[i + 1] if i + 1 < len(text) else ""
    if c == "﻿":
        return i != 0
    if _VARIATION_SUPPLEMENT[0] <= ord(c) <= _VARIATION_SUPPLEMENT[1]:
        return True
    if c not in _INVISIBLE:
        return False
    if c == "‍" and prev and nxt and _pictographic(prev) and _pictographic(nxt):
        return False  # emoji sequences like 👨‍👩‍👧
    if c in "‌‍" and (_RTL_OR_INDIC.match(prev or " ") or _RTL_OR_INDIC.match(nxt or " ")):
        return False  # joiners are part of Arabic, Persian and Indic writing
    return not (c == "­" and prev.isalpha() and nxt.isalpha())  # soft hyphen inside a word


def _b02(f: TextFile) -> Iterator[Finding]:
    positions = [
        i
        for i, c in enumerate(f.text)
        if (c in _INVISIBLE or c == "﻿" or ord(c) >= _VARIATION_SUPPLEMENT[0])
        and _suspicious_invisible(f.text, i)
    ]
    if not positions:
        return
    line = f.line_of(positions[0])
    yield finding(
        rule_id="LB-B02-unsichtbare-zeichen",
        ebene=Ebene.B,
        schwere=Schwere.H,
        titel="Unsichtbare Zeichen im Text",
        erklaerung=(
            f"Die Datei enthält {len(positions)} unsichtbare Zeichen (Zero-Width, Variation "
            "Selectors oder ähnliche) an Stellen, an denen sie keine sprachliche Aufgabe haben. "
            "Damit lassen sich Anweisungen oder Daten verstecken."
        ),
        datei=f.path,
        zeile=line,
        beleg=visible(f.line_text(line)),
        fix="Die unsichtbaren Zeichen entfernen; sie sind im Beleg als <U+…> markiert.",
        fix_prompt=(
            f"Entferne in {f.path} alle Zero-Width-Zeichen (U+200B–U+200D, U+2060–U+2064, "
            "U+FEFF außer am Dateianfang) und Variation Selectors U+E0100–U+E01EF."
        ),
        normbezug=NORM_INJECTION,
    )


# --- B03 bidi control characters (text and file names) -----------------------------------------

_BIDI = re.compile("[‪-‮⁦-⁩]")


def _b03_text(f: TextFile) -> Iterator[Finding]:
    hits = list(_BIDI.finditer(f.text))
    if not hits:
        return
    line = f.line_of(hits[0].start())
    yield finding(
        rule_id="LB-B03-bidi-steuerzeichen",
        ebene=Ebene.B,
        schwere=Schwere.H,
        titel="Steuerzeichen für die Schreibrichtung",
        erklaerung=(
            f"Die Datei enthält {len(hits)} Bidi-Steuerzeichen. Sie drehen die Anzeigereihenfolge "
            "um, sodass Menschen etwas anderes lesen als Programm oder Sprachmodell "
            "(Trojan Source)."
        ),
        datei=f.path,
        zeile=line,
        beleg=visible(f.line_text(line)),
        fix="Bidi-Steuerzeichen (U+202A–U+202E, U+2066–U+2069) entfernen.",
        fix_prompt=f"Entferne in {f.path} alle Bidi-Steuerzeichen U+202A–U+202E und U+2066–U+2069.",
        normbezug=NORM_INJECTION,
    )


def _b03_names(ctx: ScanContext) -> Iterator[Finding]:
    for entry in ctx.inventory:
        if _BIDI.search(entry.path) or any(
            unicodedata.category(c) == "Cf" for c in entry.path if c not in "‍"
        ):
            yield finding(
                rule_id="LB-B03-bidi-dateiname",
                ebene=Ebene.B,
                schwere=Schwere.H,
                titel="Unsichtbare Steuerzeichen im Dateinamen",
                erklaerung=(
                    "Der Dateiname enthält Steuerzeichen für die Schreibrichtung oder andere "
                    "unsichtbare Zeichen. So kann `rechnung‮gpj.exe` als `rechnungexe.jpg` "
                    "erscheinen."
                ),
                datei=entry.path,
                zeile=None,
                beleg=visible(entry.path),
                fix="Die Datei ohne unsichtbare Zeichen umbenennen.",
                fix_prompt=f"Benenne die Datei {visible(entry.path)} ohne Steuerzeichen um.",
                normbezug=NORM_INJECTION,
            )


# --- B04 homoglyphs ------------------------------------------------------------------------

_WORD = re.compile(r"[^\W\d_]{3,}")


def _script(c: str) -> str | None:
    try:
        name = unicodedata.name(c)
    except ValueError:
        return None
    for script in ("LATIN", "CYRILLIC", "GREEK"):
        if name.startswith(script):
            return script
    return None


def _b04(f: TextFile) -> Iterator[Finding]:
    mixed = []
    for m in _WORD.finditer(f.text):
        scripts = {s for c in m.group() if (s := _script(c))}
        if "LATIN" in scripts and len(scripts) > 1:
            mixed.append(m)
    if not mixed:
        return
    line = f.line_of(mixed[0].start())
    words = ", ".join(sorted({m.group() for m in mixed})[:5])
    yield finding(
        rule_id="LB-B04-gemischte-schrift",
        ebene=Ebene.B,
        schwere=Schwere.M,
        titel="Wörter aus gemischten Schriftsystemen",
        erklaerung=(
            f"{len(mixed)} Wörter mischen lateinische mit kyrillischen oder griechischen "
            "Buchstaben, die gleich aussehen (Homoglyphen). So werden Befehle, Domains oder "
            "Namen vorgetäuscht."
        ),
        datei=f.path,
        zeile=line,
        beleg=visible(words),
        fix="Die betroffenen Wörter nur mit lateinischen Buchstaben schreiben.",
        fix_prompt=(
            f"Ersetze in {f.path} kyrillische und griechische Buchstaben in lateinischen Wörtern "
            f"durch die lateinischen Entsprechungen: {visible(words)}."
        ),
        normbezug=("OWASP-ASI09",),
    )


# --- B05 hidden text in HTML/SVG/CSS/Markdown ----------------------------------------------

_HIDDEN_STYLE = re.compile(
    r"display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0(?:px|pt|em|rem)?\s*(?:;|$)"
    r"|opacity\s*:\s*0(?:\.0+)?\s*(?:;|$)|color\s*:\s*transparent",
    re.IGNORECASE,
)
_STYLED_ELEMENT = re.compile(
    r"<(?P<tag>[a-z][a-z0-9]*)\b[^>]*?\bstyle\s*=\s*(?P<q>[\"'])(?P<style>[^\"']*)(?P=q)[^>]*>"
    r"(?P<body>.{0,600}?)</(?P=tag)\s*>",
    re.IGNORECASE | re.DOTALL,
)
_HTML_COMMENT = re.compile(r"<!--(.*?)-->", re.DOTALL)
_INSTRUCTION_WORDS = re.compile(
    r"\b(ignore|disregard|instead|you must|do not tell|don't tell|never mention|execute|run the|"
    r"curl|wget|send|upload|exfiltrat|system prompt|password|secret|token|api[_ -]?key|\.ssh|"
    r"ignoriere|vergiss|führe|sende|lade hoch|verschweige|sag nicht|erwähne nicht|geheim)",
    re.IGNORECASE,
)
_INSTRUCTION_FILES = frozenset({"markdown", "svg"})
"""Files a model reads as instructions or content. In HTML/CSS of an app, hidden elements (menus,
collapsible sections) are normal and not reported."""


def _is_markup(f: TextFile) -> bool:
    return f.entry.sprache in _INSTRUCTION_FILES or f.path.lower().endswith((".md", ".txt"))


def _b05(f: TextFile) -> Iterator[Finding]:
    if not _is_markup(f):
        return
    for m in _HTML_COMMENT.finditer(f.text):
        body = m.group(1)
        if len(body.split()) >= 4 and _INSTRUCTION_WORDS.search(body):
            yield _b05_finding(f, m.start(), "HTML-Kommentar mit Anweisung", body)
            return
    for m in _STYLED_ELEMENT.finditer(f.text):
        if not _HIDDEN_STYLE.search(m.group("style")):
            continue
        text_inside = " ".join(re.sub(r"<[^>]*>", " ", m.group("body")).split())
        if len(text_inside.split()) >= 3:
            yield _b05_finding(f, m.start(), "Versteckt gestalteter Text", text_inside)
            return


def _b05_finding(f: TextFile, offset: int, art: str, content: str) -> Finding:
    line = f.line_of(offset)
    return finding(
        rule_id="LB-B05-versteckter-text",
        ebene=Ebene.B,
        schwere=Schwere.H,
        titel=f"{art}: für Menschen unsichtbar",
        erklaerung=(
            "Der Text ist so eingebettet, dass er in der Vorschau nicht erscheint (Kommentar, "
            "unsichtbare Formatierung), ein Sprachmodell ihn aber liest."
        ),
        datei=f.path,
        zeile=line,
        beleg=visible(" ".join(content.split()), 300),
        fix="Den versteckten Text entfernen oder sichtbar machen.",
        fix_prompt=(
            f"Entferne in {f.path} ab Zeile {line} den versteckten Text oder mach ihn sichtbar."
        ),
        normbezug=NORM_INJECTION,
    )


# --- B06 encoded blocks ----------------------------------------------------------------------

_BASE64 = re.compile(r"(?<![A-Za-z0-9+/=_-])[A-Za-z0-9+/]{120,}={0,2}(?![A-Za-z0-9+/=])")
_HEX = re.compile(r"(?<![0-9A-Fa-f])(?:[0-9A-Fa-f]{2}){80,}(?![0-9A-Fa-f])")
_INSTRUCTION_LANGS = frozenset({"markdown", "yaml", "json", "toml", "html", None})


def _printable_ratio(data: bytes) -> float:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return 0.0
    return sum(c.isprintable() or c in "\n\t" for c in text) / max(len(text), 1)


def _b06(f: TextFile) -> Iterator[Finding]:
    if f.entry.sprache not in _INSTRUCTION_LANGS:
        return
    for m in _BASE64.finditer(f.text):
        if f.text[max(0, m.start() - 40) : m.start()].rstrip().endswith("base64,"):
            continue  # data: URL (images, fonts)
        try:
            decoded = base64.b64decode(m.group() + "=" * (-len(m.group()) % 4))
        except (binascii.Error, ValueError):
            continue
        if _printable_ratio(decoded) >= 0.9:
            yield _b06_finding(f, m.start(), "Base64", decoded)
            return
    for m in _HEX.finditer(f.text):
        decoded = bytes.fromhex(m.group())
        if _printable_ratio(decoded) >= 0.9:
            yield _b06_finding(f, m.start(), "Hex", decoded)
            return


def _b06_finding(f: TextFile, offset: int, art: str, decoded: bytes) -> Finding:
    line = f.line_of(offset)
    return finding(
        rule_id="LB-B06-kodierter-text",
        ebene=Ebene.B,
        schwere=Schwere.M,
        titel=f"{art}-kodierter Text",
        erklaerung=(
            f"Ein {art}-Block enthält lesbaren Text. Kodierung verbirgt Anweisungen oder Befehle "
            "vor Menschen und einfachen Filtern."
        ),
        datei=f.path,
        zeile=line,
        beleg="dekodiert: " + visible(decoded.decode("utf-8", errors="replace"), 200),
        fix="Den Inhalt im Klartext ablegen oder entfernen.",
        fix_prompt=f"Ersetze in {f.path}, Zeile {line}, den {art}-Block durch Klartext.",
        normbezug=NORM_INJECTION,
    )


# --- B07 markdown image exfiltration -------------------------------------------------------

_IMAGE_URL = re.compile(
    r"(?:!\[[^\]]*\]\(\s*<?|<img\b[^>]*\bsrc\s*=\s*[\"']?)(https?://[^\s)\"'>]+)", re.IGNORECASE
)
_PLACEHOLDER = re.compile(r"[{}<>$]|%s|\[\[|\]\]|%7B|%7D|%24", re.IGNORECASE)


def _b07(f: TextFile) -> Iterator[Finding]:
    for m in _IMAGE_URL.finditer(f.text):
        url = m.group(1)
        query = url.split("?", 1)[1] if "?" in url else ""
        path = url.split("?", 1)[0].split("://", 1)[-1].split("/", 1)[-1]
        if _PLACEHOLDER.search(query) or _PLACEHOLDER.search(path):
            line = f.line_of(m.start())
            yield finding(
                rule_id="LB-B07-bild-exfiltration",
                ebene=Ebene.B,
                schwere=Schwere.K,
                titel="Bild-Link mit Platzhalter für Daten",
                erklaerung=(
                    "Ein Bild soll von einer Adresse geladen werden, in die Daten eingesetzt "
                    "werden. Rendert der Chat das Bild, gehen die Daten unbemerkt an diesen "
                    "Server (Markdown-Image-Exfiltration)."
                ),
                datei=f.path,
                zeile=line,
                beleg=visible(f.line_text(line)),
                fix="Den Bild-Link entfernen.",
                fix_prompt=(
                    f"Entferne in {f.path}, Zeile {line}, den Bild-Link auf {visible(url, 80)}."
                ),
                normbezug=("OWASP-ASI01", "OWASP-LLM02", "OWASP-LLM05"),
            )
            return


@register
class InhalteAnalyzer:
    info = AnalyzerInfo(
        name="b_inhalte", titel="B – Versteckte Inhalte", ebenen=frozenset({Ebene.B})
    )

    def analyze(self, ctx: ScanContext) -> list[Finding]:
        findings = list(_b03_names(ctx))
        for f in text_files(ctx):
            for check in (_b01, _b02, _b03_text, _b04, _b05, _b06, _b07):
                findings.extend(check(f))
        return findings
