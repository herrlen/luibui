"""Analyzer E – MCP (Prüfkatalog E01–E06, S2-3). Servers are never started.

Tool names, descriptions and parameter descriptions come from the code (``_e_tools``). They are
what a model reads before it calls a tool, so every B rule (own and ATR) applies to them, plus
hidden characters (E01) and instructions aimed at other tools (B16 → E02). E03 compares what a
Python handler does with what its description says. E04–E06 look at transport, authentication
and tokens in the server code. JSON tool lists (e.g. ``manifest.json``) are already covered by
B08–B17 as instruction text.
"""

import re
from collections.abc import Iterator
from pathlib import PurePosixPath

from luibui_scan.analyzers._common import TextFile, finding, rules_dir, text_files, visible
from luibui_scan.analyzers._decode import tag_text
from luibui_scan.analyzers._e_tools import Text, Tool, tools
from luibui_scan.analyzers.b_inhalte import _VS_RUN, _suspicious_invisible
from luibui_scan.analyzers.base import AnalyzerInfo
from luibui_scan.analyzers.registry import register
from luibui_scan.context import ScanContext
from luibui_scan.inventory import _MCP_TEXT
from luibui_scan.models import Ebene, Finding, ScanArt, Schwere
from luibui_scan.textrules import load_all

_CODE = frozenset({".py", ".pyw", ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts"})
_BIDI = re.compile("[\u202a-\u202e\u2066-\u2069]")
_WAS = {"name": "Tool-Name", "beschreibung": "Tool-Beschreibung"}


def _wo(t: Text) -> str:
    return _WAS.get(t.art, "Parameter-Beschreibung")


# --- E01 / E02: what the model reads about a tool ---------------------------------------------


def _versteckt(text: str) -> str | None:
    if tag_text(text):
        return "unsichtbare Unicode-Tag-Zeichen"
    if _BIDI.search(text):
        return "Steuerzeichen für die Schreibrichtung"
    if _VS_RUN.search(text) or any(_suspicious_invisible(text, i) for i in range(len(text))):
        return "unsichtbare Zeichen"  # same rules as B02: emoji and joiners in scripts are fine
    return None


def _e01_e02(tool: Tool) -> Iterator[Finding]:
    rules = load_all(rules_dir())
    seen: set[str] = set()
    for t in tool.texte:
        art = _versteckt(t.text)
        if art and "LB-E01" not in seen:
            seen.add("LB-E01")
            yield _poisoning(tool, t, Schwere.K, f"Die {_wo(t)} enthält {art}.", None)
        for rule in rules:
            if rule.search(t.text) is None:
                continue
            shadow = rule.katalog == "B16"
            key = "LB-E02" if shadow else "LB-E01"
            if key in seen:
                continue
            seen.add(key)
            detail = f"Die {_wo(t)} trifft die Regel {rule.id}: {rule.titel}."
            yield _poisoning(tool, t, rule.schwere, detail, "E02" if shadow else None)


def _poisoning(tool: Tool, t: Text, schwere: Schwere, detail: str, e02: str | None) -> Finding:
    if e02:
        rule_id, titel = (
            "LB-E02-tool-shadowing",
            f"{tool.art} „{tool.name}“ will andere Tools steuern",
        )
        erklaerung = (
            "Das Modell liest die Beschreibung jedes Tools, bevor es eines aufruft. Diese "
            "Beschreibung macht Vorgaben für andere Tools oder Server, etwa zu Empfängern oder "
            f"zur Reihenfolge. So lässt sich deren Verhalten unbemerkt ändern. {detail}"
        )
    else:
        rule_id, titel = "LB-E01-tool-poisoning", f"Versteckte Anweisung: {tool.art} „{tool.name}“"
        erklaerung = (
            "Das Modell liest Name, Beschreibung und Parameter jedes Tools, bevor es eines "
            "aufruft. Dieser Text enthält eine Anweisung an das Modell oder etwas, das ein "
            f"Mensch nicht sieht. {detail}"
        )
    return finding(
        rule_id=rule_id,
        ebene=Ebene.E,
        schwere=schwere,
        titel=titel[:200],
        erklaerung=erklaerung[:4000],
        datei=tool.datei,
        zeile=t.zeile,
        beleg=visible(t.text),
        fix="Die Beschreibung auf das beschränken, was das Tool selbst tut und erwartet.",
        fix_prompt=(
            f"Kürze in {tool.datei}, Zeile {t.zeile}, die {_wo(t)} des Tools „{tool.name}“ auf "
            "eine sachliche Beschreibung ohne Anweisungen an das Modell und ohne Vorgaben für "
            "andere Tools."
        ),
        normbezug=("OWASP-ASI02", "OWASP-LLM01"),
    )


# --- E03: dangerous capability not mentioned ---------------------------------------------------

_GENANNT = {
    "befehle": re.compile(
        r"(?i)shell|command|befehl|terminal|execut|ausf[üu]hr|\brun\b|script|skript|bash|process|"
        r"prozess|cli\b|subprocess|kommando"
    ),
    "dateien": re.compile(
        r"(?i)writ|schreib|save|speicher|creat|erstell|anleg|delet|l[öo]sch|remov|entfern|file|"
        r"datei|modif|[äa]nder|updat|overwrit|[üu]berschreib|move|verschieb|copy|kopier|rename|"
        r"umbenenn|folder|ordner|director|verzeichnis|mkdir|path|pfad|disk"
    ),
}
_FAEHIGKEIT = {
    "befehle": "führt Befehle aus",
    "dateien": "schreibt, verschiebt oder löscht Dateien",
}


def _e03(tool: Tool) -> Iterator[Finding]:
    text = f"{tool.name} {tool.beschreibung}"
    for kind in sorted(tool.faehigkeiten):
        if _GENANNT[kind].search(text):
            continue
        yield finding(
            rule_id="LB-E03-faehigkeit-nicht-genannt",
            ebene=Ebene.E,
            schwere=Schwere.H,
            titel=f"Tool „{tool.name}“ {_FAEHIGKEIT[kind]}, sagt es aber nicht"[:200],
            erklaerung=(
                f"Der Code des Tools {_FAEHIGKEIT[kind]}. Name und Beschreibung, nach denen das "
                "Modell und der Nutzer entscheiden, erwähnen das nicht. So wird ein Aufruf "
                "erlaubt, dessen Folgen niemand erwartet."
            ),
            datei=tool.datei,
            zeile=tool.zeile,
            beleg=visible(tool.beschreibung or tool.name),
            fix="In der Beschreibung klar sagen, was das Tool ausführt oder verändert.",
            fix_prompt=(
                f"Ergänze in {tool.datei}, Zeile {tool.zeile}, die Beschreibung des Tools "
                f"„{tool.name}“ um den Hinweis, dass es {_FAEHIGKEIT[kind]}."
            ),
            normbezug=("OWASP-ASI02", "OWASP-LLM06"),
        )


# --- E04–E06: transport, authentication, tokens ------------------------------------------------

_HTTP_TRANSPORT = re.compile(
    r"""transport\s*=\s*["'](sse|streamable-http|streamable_http|http)["']|"""
    r"""\.(sse_app|streamable_http_app|http_app)\(|"""
    r"""\bnew\s+(SSEServerTransport|StreamableHTTPServerTransport)\b"""
)
_AUTH = re.compile(
    r"""(?i)\bauth\s*=|token_verifier|auth_server_provider|AuthSettings|BearerAuth|"""
    r"""requireBearerAuth|OAuth|verify_?token|jwt|passport|authMiddleware|"""
    r"""headers\.get\(\s*["']authorization["']|headers\[\s*["']authorization["']\]|"""
    r"""headers\.authorization|x-api-key"""
)
_QUERY_AUTH = re.compile(
    r"""(query_params|args)\.get\(\s*["'](token|api_key|apikey|api-key|key|access_token|auth)["']|"""
    r"""\breq(uest)?\.query\.(token|api_key|apiKey|key|access_token|auth)\b"""
)
_CORS_ALL = re.compile(
    r"""allow_origins\s*=\s*\[\s*["']\*["']\s*\]|\borigin\s*:\s*["']\*["']|"""
    r"""Access-Control-Allow-Origin["']\s*[,:]\s*["']\*["']|\bcors\(\s*\)"""
)
_PASSTHROUGH = re.compile(
    r"""(?i)(requests|httpx|session|client|axios)\.\w+\([^)\n]*headers\s*=\s*(dict\()?request\.headers|"""
    r"""fetch\([^)\n]*headers\s*:\s*req(uest)?\.headers\b|"""
    r"""["']Authorization["']\s*:\s*(req(uest)?\.headers(\.authorization|\[\s*["']authorization["']\])|"""
    r"""request\.headers(\.get)?[\[(]\s*["']authorization["'])"""
)


_ABLAGE_MUSTER = (
    r"(tokens?\.json|credentials?\.json|access_token|refresh_token|auth_token|oauth|"
    r"tokens?_?(path|file)|credentials?_(path|file))"
)
_KLARTEXT_TOKEN = re.compile(
    rf"""(?i)\bopen\([^\n]{{0,120}}?{_ABLAGE_MUSTER}[^\n]{{0,80}}?,\s*["'][wa]|"""
    rf"""{_ABLAGE_MUSTER}\w*\.write_text\(|"""
    rf"""json\.dump\(\s*\w*(token|credential)s?\w*\s*,\s*open\(|"""
    rf"""writeFile(Sync)?\([^\n]{{0,120}}?{_ABLAGE_MUSTER}"""
)
"""Where a server writes OAuth tokens or credential files, not any variable named "secret"."""
_TESTDATEI = re.compile(r"(^|/)(tests?|__tests__|spec)/|[._-](test|spec)\.\w+$|(^|/)test_\w+\.py$")
_GESCHUETZT = re.compile(r"(?i)\bkeyring\b|\bkeytar\b|safeStorage|Fernet|encrypt|cryptography")


def _line(text: str, m: re.Match[str]) -> tuple[int, str]:
    start = text.count("\n", 0, m.start()) + 1
    return start, text.split("\n")[start - 1]


def _server(files: list[TextFile], package_has_auth: bool) -> Iterator[Finding]:
    for f in files:
        if (m := _HTTP_TRANSPORT.search(f.text)) and not package_has_auth:
            zeile, code = _line(f.text, m)
            yield finding(
                rule_id="LB-E04-ohne-anmeldung",
                ebene=Ebene.E,
                schwere=Schwere.H,
                titel="MCP-Server über HTTP ohne Anmeldung",
                erklaerung=(
                    "Der Server ist über HTTP oder SSE erreichbar, und im Paket findet sich keine "
                    "Prüfung von Zugangsdaten. Wer die Adresse kennt, kann jedes Tool aufrufen."
                ),
                datei=f.path,
                zeile=zeile,
                beleg=visible(code.strip()),
                fix="Eine Anmeldung vorschalten (OAuth oder Bearer-Token im Header) oder nur "
                "über stdio anbieten.",
                fix_prompt=f"Sichere den HTTP-Transport in {f.path}, Zeile {zeile}, mit einer "
                "Token-Prüfung im Authorization-Header ab.",
                normbezug=("OWASP-ASI03", "OWASP-ASI07"),
            )
        for m in _QUERY_AUTH.finditer(f.text):
            zeile, code = _line(f.text, m)
            yield finding(
                rule_id="LB-E04-anmeldung-in-url",
                ebene=Ebene.E,
                schwere=Schwere.H,
                titel="Zugangsschlüssel in der Adresse (Query-Parameter)",
                erklaerung=(
                    "Der Server liest einen Schlüssel oder Token aus der URL. URLs landen in "
                    "Logs, im Browserverlauf und bei Proxys; der Schlüssel ist damit offen."
                ),
                datei=f.path,
                zeile=zeile,
                beleg=visible(code.strip()),
                fix="Den Schlüssel im Authorization-Header erwarten, nie in der URL.",
                fix_prompt=f"Lies in {f.path}, Zeile {zeile}, den Token aus dem "
                "Authorization-Header statt aus der URL.",
                normbezug=("OWASP-ASI03", "OWASP-ASI07"),
            )
            break
        if m := _CORS_ALL.search(f.text):
            zeile, code = _line(f.text, m)
            yield finding(
                rule_id="LB-E05-cors-alle",
                ebene=Ebene.E,
                schwere=Schwere.M,
                titel="MCP-Server erlaubt Anfragen von jeder Website (CORS *)",
                erklaerung=(
                    "Jede Website, die der Nutzer im Browser öffnet, darf den Server ansprechen. "
                    "Läuft er lokal, kann eine fremde Seite so Tools aufrufen."
                ),
                datei=f.path,
                zeile=zeile,
                beleg=visible(code.strip()),
                fix="Nur die eigenen Ursprünge zulassen oder CORS ganz weglassen.",
                fix_prompt=f"Beschränke CORS in {f.path}, Zeile {zeile}, auf die benötigten "
                "Ursprünge.",
                normbezug=("OWASP-ASI07",),
            )
        for m in _PASSTHROUGH.finditer(f.text):
            zeile, code = _line(f.text, m)
            yield finding(
                rule_id="LB-E06-token-weitergabe",
                ebene=Ebene.E,
                schwere=Schwere.H,
                titel="Server reicht den Token des Nutzers an Dritte weiter",
                erklaerung=(
                    "Der Server nimmt den Zugangs-Token aus der eingehenden Anfrage und schickt "
                    "ihn an einen anderen Dienst weiter (Token Passthrough). Der andere Dienst "
                    "erhält so Zugriff im Namen des Nutzers."
                ),
                datei=f.path,
                zeile=zeile,
                beleg=visible(code.strip()),
                fix="Für Aufrufe an andere Dienste eigene, eng begrenzte Zugangsdaten verwenden.",
                fix_prompt=f"Ersetze in {f.path}, Zeile {zeile}, den durchgereichten Token durch "
                "eigene Zugangsdaten des Servers für den anderen Dienst.",
                normbezug=("OWASP-ASI03", "OWASP-LLM02"),
            )
            break
        klartext = not _TESTDATEI.search(f.path) and not _GESCHUETZT.search(f.text)
        if klartext and (m := _KLARTEXT_TOKEN.search(f.text)):
            zeile, code = _line(f.text, m)
            yield finding(
                rule_id="LB-E06-token-im-klartext",
                ebene=Ebene.E,
                schwere=Schwere.H,
                titel="Server speichert Tokens im Klartext",
                erklaerung=(
                    "Der Server schreibt Zugangs-Token oder Zugangsdaten in eine Datei, ohne sie "
                    "zu verschlüsseln oder einen Schlüsselspeicher des Systems zu nutzen. Jedes "
                    "Programm mit Zugriff auf die Datei kann sie lesen."
                ),
                datei=f.path,
                zeile=zeile,
                beleg=visible(code.strip()),
                fix="Tokens im Schlüsselspeicher des Systems ablegen (keyring, keytar) oder "
                "verschlüsseln.",
                fix_prompt=f"Speichere die Tokens in {f.path}, Zeile {zeile}, im Schlüsselspeicher "
                "des Systems (Python: keyring, Node: keytar) statt in einer Datei.",
                normbezug=("OWASP-ASI03", "OWASP-LLM02"),
            )


@register
class McpAnalyzer:
    info = AnalyzerInfo(
        name="e_mcp",
        titel="E – MCP",
        ebenen=frozenset({Ebene.E}),
        scan_arts=frozenset({ScanArt.INTENSIV, ScanArt.LOKAL}),
    )

    def analyze(self, ctx: ScanContext) -> list[Finding]:
        code = [f for f in text_files(ctx) if PurePosixPath(f.path).suffix.lower() in _CODE]
        findings: list[Finding] = []
        for tool in tools(code):
            findings += _e01_e02(tool)
            findings += _e03(tool)
        if any(_MCP_TEXT.search(f.text) for f in code):  # transport checks: MCP servers only
            has_auth = any(_AUTH.search(f.text) for f in code)
            findings += _server(code, has_auth)
        return findings
