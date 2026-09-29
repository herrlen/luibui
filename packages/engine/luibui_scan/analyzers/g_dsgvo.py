"""Analyzer G – DSGVO und Rechte (Prüfkatalog G01–G06, S2-4). Achse dsgvo.

Endpoints come from the code only: URLs in string literals (not comments or docstrings), URLs in
shell commands, and SDK imports that imply a host (``import openai``). Countries come from the
maintained list ``rules/data/laender.yaml``; nothing is looked up online. With ``luibui.json``
the code is compared with what the manifest declares (G01, G03–G06).

Decisions (Len, 29.09.2026): a host whose country is unknown is only a hint (I); a US host is
Mittel until the manifest names a legal basis (the adequacy decision covers DPF-certified
recipients only).
"""

import ast
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from luibui_scan.analyzers._common import TextFile, finding, rules_dir, text_files, visible
from luibui_scan.analyzers.base import AnalyzerInfo
from luibui_scan.analyzers.registry import register
from luibui_scan.context import ScanContext
from luibui_scan.models import Achse, Ebene, Finding, Nachweisgrad, Pakettyp, ScanArt, Schwere

MANIFEST = "luibui.json"
MAX_MANIFEST_BYTES = 1_000_000
MAX_PER_RULE = 20

_URL = re.compile(
    r"(?i)\b(?:https?|wss?)://([a-z0-9.-]+\.[a-z]{2,63}|\d{1,3}(?:\.\d{1,3}){3})\b([^\s\"'`<>]*)"
)
_KENNUNG = re.compile(r"(?i)/(schemas?|ns|xmlns|dtd)(/|\b)|\.(xsd|dtd)\b")
"""Namespace and schema identifiers look like URLs but are never fetched."""
_PY = frozenset({".py", ".pyw"})
_JS = frozenset({".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts"})
_SH = frozenset({".sh", ".bash", ".zsh"})
_LOKAL = re.compile(
    r"(?i)^(localhost|.*\.localhost|127\.\d+\.\d+\.\d+|0\.0\.0\.0|10\.\d+\.\d+\.\d+|"
    r"192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+|"
    r"(.*\.)?example(\.(com|org|net))?|.*\.(invalid|test|local|internal|lan))$"
)
_NETZ_PY = frozenset(
    {
        "requests",
        "httpx",
        "urllib",
        "aiohttp",
        "http",
        "websockets",
        "websocket",
        "socket",
        "ftplib",
    }
)
_NETZ_JS = re.compile(r"\bfetch\(|\baxios\b|\bgot\(|\bhttps?\.(request|get)\(|\bnew\s+WebSocket\(")
_JS_COMMENT = re.compile(r"/\*.*?\*/|(?<![:\"'`\\\w])//[^\n]*", re.DOTALL)
_SECRET_ENV = re.compile(r"(?i)(key|token|secret|passw|credential|auth)")


@dataclass(frozen=True, slots=True)
class Laender:
    ewr: frozenset[str]
    angemessen: dict[str, str]
    teilweise: dict[str, str]
    hosts: dict[str, dict[str, str]]
    sdks: dict[str, str]
    keine: frozenset[str]

    def land(self, host: str) -> str | None:
        parts = host.split(".")
        for i in range(len(parts) - 1):
            entry = self.hosts.get(".".join(parts[i:]))
            if entry:
                return entry["land"]
        return None

    def betreiber(self, host: str) -> str:
        return self.hosts.get(host, {}).get("betreiber", "")


@lru_cache(maxsize=2)
def laender(rules: Path) -> Laender:
    d = yaml.safe_load((rules / "data" / "laender.yaml").read_text("utf-8"))
    return Laender(
        ewr=frozenset(d["ewr"]),
        angemessen=dict(d["angemessen"]),
        teilweise=dict(d["teilweise"]),
        hosts=dict(d["hosts"]),
        sdks=dict(d["sdks"]),
        keine=frozenset(d["keine_endpunkte"]),
    )


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = json.loads(
        resources.files("luibui_scan").joinpath("data/luibui.schema.json").read_text("utf-8")
    )
    return Draft202012Validator(schema)


# --- what the code does ------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Stelle:
    datei: str
    zeile: int
    beleg: str


@dataclass(slots=True)
class Code:
    hosts: dict[str, Stelle] = field(default_factory=dict)
    """Hosts the code talks to (network context or SDK), with the first place found."""
    links: dict[str, Stelle] = field(default_factory=dict)
    """URLs in strings of files without network use: shown, never counted as endpoints."""
    shell: Stelle | None = None
    netz: Stelle | None = None
    schreiben: Stelle | None = None
    env: dict[str, Stelle] = field(default_factory=dict)


def _host(m: re.Match[str], ld: Laender) -> str | None:
    host = m.group(1).lower().rstrip(".")
    if _LOKAL.match(host) or host in ld.keine or _KENNUNG.search(m.group(2)):
        return None
    return host


def _add(target: dict[str, Stelle], host: str | None, stelle: Stelle) -> None:
    if host and host not in target:
        target[host] = stelle


_SHELL_PY = {("subprocess", n) for n in ("run", "call", "check_call", "check_output", "Popen")}
_SHELL_PY |= {("os", "system"), ("os", "popen"), ("os", "execv"), ("os", "execvp")}
_WRITE_PY = {
    "write_text",
    "write_bytes",
    "unlink",
    "rmtree",
    "remove",
    "rename",
    "move",
    "copy",
    "copyfile",
    "copytree",
    "mkdir",
    "makedirs",
}


def _python(f: TextFile, ld: Laender, code: Code) -> None:
    try:
        tree = ast.parse(f.text, filename=f.path)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                docstrings.add(id(body[0].value))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    netz = any(mod.split(".")[0] in _NETZ_PY for mod in modules)
    for mod in sorted(modules):
        for sdk, host in ld.sdks.items():
            if mod == sdk or mod.startswith(sdk + "."):
                _add(code.hosts, host, Stelle(f.path, 1, f"import {mod}"))
                netz = True
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            # Docstrings and multi-line texts (sample HTML, templates) are content, not targets.
            if id(node) in docstrings or "\n" in node.value.strip():
                continue
            for m in _URL.finditer(node.value):
                stelle = Stelle(f.path, node.lineno, f.line_text(node.lineno).strip())
                _add(code.hosts if netz else code.links, _host(m, ld), stelle)
        elif isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            owner = getattr(fn.value, "id", "") if isinstance(fn, ast.Attribute) else ""
            stelle = Stelle(f.path, node.lineno, f.line_text(node.lineno).strip())
            if (owner, name) in _SHELL_PY or (owner == "asyncio" and "subprocess" in name):
                code.shell = code.shell or stelle
            elif name in _WRITE_PY and owner not in ("json", "re", "str", "dict", "list"):
                code.schreiben = code.schreiben or stelle
            elif name == "open" and len(node.args) >= 2:
                mode = node.args[1].value if isinstance(node.args[1], ast.Constant) else ""
                if isinstance(mode, str) and any(c in mode for c in "wax+"):
                    code.schreiben = code.schreiben or stelle
            elif (
                name in ("getenv", "get")
                and owner in ("os", "environ")
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                code.env.setdefault(node.args[0].value, stelle)
        elif (
            isinstance(node, ast.Subscript)
            and ast.unparse(node.value) in ("os.environ", "environ")
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            code.env.setdefault(
                node.slice.value, Stelle(f.path, node.lineno, f.line_text(node.lineno).strip())
            )
    if netz:
        code.netz = code.netz or Stelle(f.path, 1, "Netzwerkbibliothek oder SDK importiert")


_JS_IMPORT = re.compile(r"""(?:from\s+|require\(\s*|import\(\s*)["']([^"']+)["']""")
_JS_SHELL = re.compile(r"""["'](node:)?child_process["']""")
_JS_WRITE = re.compile(
    r"\bfs(?:/promises)?\.\w*(writeFile|appendFile|unlink|rm|rmdir|mkdir|rename)"
)
_JS_ENV = re.compile(r"""process\.env(?:\.([A-Za-z_]\w*)|\[\s*["']([^"']+)["']\s*\])""")


def _javascript(f: TextFile, ld: Laender, code: Code) -> None:
    text = _JS_COMMENT.sub(lambda m: "\n" * m.group().count("\n"), f.text)
    netz = bool(_NETZ_JS.search(text))
    for m in _JS_IMPORT.finditer(text):
        host = ld.sdks.get(m.group(1))
        if host:
            _add(code.hosts, host, Stelle(f.path, f.line_of(m.start()), m.group().strip()))
            netz = True
        if _JS_SHELL.search(m.group()):
            code.shell = code.shell or Stelle(f.path, f.line_of(m.start()), m.group().strip())
    for m in _URL.finditer(text):
        zeile = text.count("\n", 0, m.start()) + 1
        stelle = Stelle(f.path, zeile, f.line_text(zeile).strip())
        _add(code.hosts if netz else code.links, _host(m, ld), stelle)
    if m2 := _JS_WRITE.search(text):
        z = text.count("\n", 0, m2.start()) + 1
        code.schreiben = code.schreiben or Stelle(f.path, z, f.line_text(z).strip())
    for m in _JS_ENV.finditer(text):
        z = text.count("\n", 0, m.start()) + 1
        code.env.setdefault(m.group(1) or m.group(2), Stelle(f.path, z, f.line_text(z).strip()))
    if netz:
        code.netz = code.netz or Stelle(f.path, 1, "fetch, axios oder ein SDK")


def _shell(f: TextFile, ld: Laender, code: Code) -> None:
    for i, line in enumerate(f.text.split("\n"), 1):
        if line.lstrip().startswith("#") or not re.search(r"\b(curl|wget|http)\b", line):
            continue
        for m in _URL.finditer(line):
            _add(code.hosts, _host(m, ld), Stelle(f.path, i, line.strip()))
            code.netz = code.netz or Stelle(f.path, i, line.strip())


# Further languages: URLs in quoted strings of files that use a network client.
_ANDERE_NETZ = {
    ".go": r"net/http|http\.(Get|Post|NewRequest)|resty",
    ".rb": r"Net::HTTP|HTTParty|Faraday|RestClient|open-uri|URI\.open",
    ".php": r"curl_init|file_get_contents\s*\(|Guzzle|wp_remote_|fsockopen",
    ".rs": r"reqwest|ureq|hyper::|surf::",
    ".java": r"HttpClient|HttpURLConnection|OkHttp|RestTemplate|WebClient",
    ".kt": r"HttpClient|HttpURLConnection|OkHttp|RestTemplate|WebClient|ktor",
    ".cs": r"HttpClient|WebClient|RestSharp|HttpWebRequest",
    ".ps1": r"(?i)Invoke-WebRequest|Invoke-RestMethod|\biwr\b|\birm\b|WebClient",
    ".psm1": r"(?i)Invoke-WebRequest|Invoke-RestMethod|\biwr\b|\birm\b|WebClient",
    ".bat": r"(?i)\bcurl\b|\bpowershell\b|\bbitsadmin\b|\bcertutil\b",
    ".cmd": r"(?i)\bcurl\b|\bpowershell\b|\bbitsadmin\b|\bcertutil\b",
}
_KOMMENTAR = {
    "slash": re.compile(r"/\*.*?\*/|(?<![:\"'`\\\w])//[^\n]*", re.DOTALL),
    "hash": re.compile(r"(?m)^\s*#[^\n]*|(?<=\s)#(?![{\[])[^\n]*"),
    "batch": re.compile(r"(?im)^\s*(rem\b|::)[^\n]*"),
}
_KOMMENTAR_ART = {".rb": "hash", ".ps1": "hash", ".psm1": "hash", ".bat": "batch", ".cmd": "batch"}


def _andere(f: TextFile, ld: Laender, code: Code) -> None:
    suffix = PurePosixPath(f.path).suffix.lower()
    kommentar = _KOMMENTAR[_KOMMENTAR_ART.get(suffix, "slash")]
    text = kommentar.sub(lambda m: "\n" * m.group().count("\n"), f.text)
    if not re.search(_ANDERE_NETZ[suffix], text):
        return
    code.netz = code.netz or Stelle(f.path, 1, "Netzwerk-Client")
    for m in _URL.finditer(text):
        zeile = text.count("\n", 0, m.start()) + 1
        _add(code.hosts, _host(m, ld), Stelle(f.path, zeile, f.line_text(zeile).strip()))


# Configuration: keys that name a target (base_url, API_ENDPOINT, webhook …), never project links.
_KONFIG_KEY = re.compile(r"(?i)(url|uri|endpoint|host|base|api|server|webhook|remote)")
_KONFIG_NICHT = re.compile(
    r"(?i)(homepage|repository|repo|documentation|docs|bugs|issues|changelog|license|source|"
    r"funding|schema|image|icon|logo|avatar|website|help|support|privacy|terms)"
)
_KONFIG_ZEILE = re.compile(
    r"""(?m)(?:^|[{,])\s*(?:export\s+)?["']?([\w.-]+)["']?\s*[:=]\s*["']?((?:https?|wss?)://[^"'\s,}]+)"""
)
_KONFIG_DATEIEN = re.compile(r"(?i)(^|/)\.env(\.[\w-]+)?$|\.(ya?ml|toml|json|ini|cfg|conf)$")
_KONFIG_AUSGENOMMEN = re.compile(
    r"(?i)(^|/)(package(-lock)?\.json|composer\.(json|lock)|tsconfig[\w.-]*\.json|luibui\.json|"
    r"pyproject\.toml|cargo\.toml|\.eslintrc[\w.]*|renovate\.json|\.github/.*|"
    r"[\w.-]*lock\.(json|ya?ml))$"
)


def _konfig(f: TextFile, ld: Laender, code: Code) -> None:
    for m in _KONFIG_ZEILE.finditer(f.text):
        key = m.group(1).rsplit(".", 1)[-1]
        if not _KONFIG_KEY.search(key) or _KONFIG_NICHT.search(key):
            continue
        inner = _URL.search(m.group(2))
        if inner is None:
            continue
        zeile = f.line_of(m.start(2))
        stelle = Stelle(f.path, zeile, f.line_text(zeile).strip())
        _add(code.hosts, _host(inner, ld), stelle)


def _code(ctx: ScanContext, ld: Laender) -> Code:
    code = Code()
    for f in text_files(ctx):
        suffix = PurePosixPath(f.path).suffix.lower()
        if suffix in _PY:
            _python(f, ld, code)
        elif suffix in _JS:
            _javascript(f, ld, code)
        elif suffix in _SH:
            _shell(f, ld, code)
        elif suffix in _ANDERE_NETZ:
            _andere(f, ld, code)
        elif _KONFIG_DATEIEN.search(f.path) and not _KONFIG_AUSGENOMMEN.search(f.path):
            _konfig(f, ld, code)
    return code


# --- findings ----------------------------------------------------------------------------------


def _g(
    rule_id: str,
    schwere: Schwere,
    titel: str,
    erklaerung: str,
    stelle: Stelle | None,
    fix: str,
    normbezug: tuple[str, ...],
    nachweisgrad: Nachweisgrad = Nachweisgrad.STATISCH_ERKANNT,
) -> Finding:
    ort = f"{stelle.datei}, Zeile {stelle.zeile}" if stelle else MANIFEST
    return finding(
        rule_id=rule_id,
        ebene=Ebene.G,
        schwere=schwere,
        achse=Achse.DSGVO,
        titel=titel[:200],
        erklaerung=erklaerung[:4000],
        datei=stelle.datei if stelle else MANIFEST,
        zeile=stelle.zeile if stelle else None,
        beleg=visible(stelle.beleg) if stelle else None,
        fix=fix,
        fix_prompt=f"{fix} Betroffen: {ort}.",
        normbezug=normbezug,
        nachweisgrad=nachweisgrad,
    )


_GARANTIEN = {"standardvertragsklauseln", "binding_corporate_rules", "einwilligung"}
_ART_44 = ("DSGVO-Art-44", "DSGVO-Art-45", "DSGVO-Art-46")


def _land_befund(
    host: str, land: str, grundlage: str | None, stelle: Stelle | None, ld: Laender
) -> Finding | None:
    if land in ld.ewr or land in ld.angemessen:
        return None
    betreiber = ld.betreiber(host)
    wer = f"{host} ({betreiber}, {land})" if betreiber else f"{host} ({land})"
    if land in ld.teilweise:
        if grundlage in _GARANTIEN | {"angemessenheitsbeschluss"}:
            return _g(
                "LB-G02-drittland",
                Schwere.I,
                f"Übermittlung in die USA: {host}",
                f"Daten gehen an {wer}. Das Manifest nennt als Grundlage „{grundlage}“. Der "
                f"Angemessenheitsbeschluss gilt {ld.teilweise[land]}.",
                stelle,
                "Die Zertifizierung des Empfängers prüfen und in der Doku belegen.",
                _ART_44,
                Nachweisgrad.SELBSTAUSKUNFT,
            )
        return _g(
            "LB-G02-drittland",
            Schwere.M,
            f"Übermittlung in die USA: {host}",
            f"Daten gehen an {wer}. Zulässig ist das nur, wenn der Empfänger unter dem EU-US Data "
            "Privacy Framework zertifiziert ist oder andere Garantien bestehen, etwa "
            "Standardvertragsklauseln. Das Paket sagt dazu nichts.",
            stelle,
            "Im Manifest (luibui.json) je Endpunkt Land und Rechtsgrundlage angeben.",
            _ART_44,
        )
    if grundlage in _GARANTIEN:
        return _g(
            "LB-G02-drittland",
            Schwere.I,
            f"Übermittlung in ein Drittland: {host}",
            f"Daten gehen an {wer}. Für dieses Land gibt es keinen Angemessenheitsbeschluss; das "
            f"Manifest nennt als Grundlage „{grundlage}“.",
            stelle,
            "Die Garantien in der Doku belegen.",
            _ART_44,
            Nachweisgrad.SELBSTAUSKUNFT,
        )
    return _g(
        "LB-G02-drittland",
        Schwere.H,
        f"Übermittlung in ein Drittland ohne Schutzniveau: {host}",
        f"Daten gehen an {wer}. Für dieses Land gibt es keinen Angemessenheitsbeschluss der EU, "
        "und das Paket nennt keine anderen Garantien. Eine Übermittlung ist so nicht zulässig.",
        stelle,
        "Einen Anbieter im EWR wählen oder Standardvertragsklauseln abschließen und im "
        "Manifest angeben.",
        _ART_44,
    )


def _passt(host: str, deklariert: str) -> bool:
    deklariert = deklariert.lower()
    if deklariert.startswith("*."):
        return host.endswith(deklariert[1:])
    return host == deklariert


def _ohne_manifest(code: Code, ld: Laender) -> Iterator[Finding]:
    unbekannt = []
    for host, stelle in sorted(code.hosts.items()):
        land = ld.land(host)
        if land is None:
            unbekannt.append((host, stelle))
        elif befund := _land_befund(host, land, None, stelle, ld):
            yield befund
    if unbekannt:
        yield _g(
            "LB-G02-land-unbekannt",
            Schwere.I,
            f"{len(unbekannt)} Endpunkt(e) ohne bekanntes Land",
            "Der Code spricht mit Hosts, deren Verarbeitungsort luibui nicht kennt: "
            + ", ".join(h for h, _ in unbekannt[:10])
            + ". Ob Daten den EWR verlassen, lässt sich so nicht sagen.",
            unbekannt[0][1],
            "Im Manifest (luibui.json) je Endpunkt Land und Rechtsgrundlage angeben.",
            ("DSGVO-Art-13", "DSGVO-Art-44"),
        )


def _manifest(ctx: ScanContext) -> tuple[dict[str, Any] | None, list[Finding]]:
    path = ctx.root / MANIFEST
    fix = "luibui.json nach dem Schema unter luibui.com/spec/luibui.schema.json ausfüllen."
    try:
        if path.stat().st_size > MAX_MANIFEST_BYTES:
            raise ValueError("zu groß")
        data = json.loads(path.read_text("utf-8"))
    except (OSError, ValueError) as exc:
        text = "Die Datei ist zu groß." if str(exc) == "zu groß" else "Die Datei ist kein JSON."
        return None, [
            _g(
                "LB-G01-manifest-ungueltig",
                Schwere.M,
                "luibui.json ist nicht lesbar",
                f"{text} Ohne gültiges Manifest lässt sich nicht abgleichen, was das Paket "
                "deklariert.",
                None,
                fix,
                ("DSGVO-Art-13",),
            )
        ]
    if not isinstance(data, dict):
        return None, [
            _g(
                "LB-G01-manifest-ungueltig",
                Schwere.M,
                "luibui.json ist kein Objekt",
                "Das Manifest muss ein JSON-Objekt sein.",
                None,
                fix,
                ("DSGVO-Art-13",),
            )
        ]
    out = []
    fehler = sorted(_validator().iter_errors(data), key=lambda e: list(e.path))
    if fehler:
        details = "; ".join(
            f"{'/'.join(str(p) for p in e.path) or '(oben)'}: {e.message}" for e in fehler[:5]
        )
        out.append(
            _g(
                "LB-G01-manifest-ungueltig",
                Schwere.M,
                "luibui.json entspricht nicht dem Schema",
                f"{len(fehler)} Abweichung(en) vom Schema, etwa: {visible(details, 600)}",
                None,
                fix,
                ("DSGVO-Art-13",),
            )
        )
    typ = data.get("typ")
    erkannt = ctx.pakettyp
    if (
        isinstance(typ, str)
        and erkannt not in (None, Pakettyp.GEMISCHT, Pakettyp.UNBEKANNT)
        and typ != erkannt.value
    ):
        out.append(
            _g(
                "LB-G01-typ-abweichend",
                Schwere.M,
                "Pakettyp im Manifest passt nicht",
                f"luibui.json nennt „{visible(typ, 40)}“, erkannt wurde „{erkannt.value}“.",
                None,
                "Den Typ im Manifest korrigieren.",
                ("DSGVO-Art-13",),
            )
        )
    return data, out


def _mit_manifest(data: dict[str, Any], code: Code, ld: Laender) -> Iterator[Finding]:
    endpunkte = [e for e in data.get("endpunkte") or [] if isinstance(e, dict)]
    rechte: dict[str, Any] = data["rechte"] if isinstance(data.get("rechte"), dict) else {}
    art13 = ("DSGVO-Art-5", "DSGVO-Art-13")
    for e in endpunkte:
        host, land = str(e.get("host", "")).lower(), e.get("land")
        grundlage = e.get("rechtsgrundlage")
        stelle = next((s for h, s in code.hosts.items() if _passt(h, host)), None)
        if not isinstance(land, str) or not land:
            yield _g(
                "LB-G02-land-fehlt",
                Schwere.M,
                f"Endpunkt ohne Land: {visible(host, 80)}",
                "Das Manifest nennt für diesen Endpunkt kein Land.",
                stelle,
                "Im Manifest das Land (ISO-Code) angeben.",
                _ART_44,
            )
        elif befund := _land_befund(host, land.upper(), grundlage, stelle, ld):
            yield befund
    undeklariert = [
        (h, s)
        for h, s in sorted(code.hosts.items())
        if not any(_passt(h, str(e.get("host", ""))) for e in endpunkte)
    ]
    for host, stelle in undeklariert[:MAX_PER_RULE]:
        land = ld.land(host)
        yield _g(
            "LB-G03-endpunkt-undeklariert",
            Schwere.H,
            f"Endpunkt nicht im Manifest: {host}",
            f"Der Code spricht mit {host}"
            + (f" ({land})" if land else "")
            + ", luibui.json nennt diesen Endpunkt nicht. Nutzer erfahren so nicht, wohin ihre "
            "Daten gehen.",
            stelle,
            f"{host} mit Zweck, Land und Datenkategorien unter „endpunkte“ eintragen.",
            art13,
        )
        if land and (befund := _land_befund(host, land, None, stelle, ld)):
            yield befund
    art25 = ("DSGVO-Art-25", "OWASP-LLM06")
    dateien: dict[str, Any] = rechte["dateien"] if isinstance(rechte.get("dateien"), dict) else {}
    fehlende = [
        ("Shell", code.shell, rechte.get("shell") is True, "rechte.shell auf true setzen."),
        ("Netzwerk", code.netz, rechte.get("netzwerk") is True, "rechte.netzwerk auf true setzen."),
        (
            "Dateien schreiben",
            code.schreiben,
            bool(dateien.get("schreiben")),
            "Die Pfade unter rechte.dateien.schreiben eintragen.",
        ),
    ]
    for was, stelle, deklariert, fix in fehlende:
        if stelle is not None and not deklariert:
            yield _g(
                "LB-G04-recht-undeklariert",
                Schwere.H,
                f"Recht nicht deklariert: {was}",
                f"Der Code nutzt „{was}“, luibui.json deklariert dieses Recht nicht.",
                stelle,
                fix,
                art25,
            )
    env_dekl = {str(v) for v in rechte.get("umgebungsvariablen") or []}
    env_neu = {k: s for k, s in code.env.items() if k not in env_dekl}
    if env_neu:
        namen = sorted(env_neu)
        yield _g(
            "LB-G04-recht-undeklariert",
            Schwere.H,
            "Umgebungsvariablen nicht deklariert",
            f"Der Code liest {', '.join(visible(n, 60) for n in namen[:10])}; "
            "rechte.umgebungsvariablen nennt sie nicht.",
            env_neu[namen[0]],
            "Die Namen unter rechte.umgebungsvariablen eintragen.",
            art25,
        )
    secret = next((s for k, s in sorted(code.env.items()) if _SECRET_ENV.search(k)), None)
    if secret is not None and rechte.get("zugangsdaten") is not True:
        yield _g(
            "LB-G04-recht-undeklariert",
            Schwere.H,
            "Recht nicht deklariert: Zugangsdaten",
            "Der Code liest einen Schlüssel oder Token aus der Umgebung, luibui.json setzt "
            "rechte.zugangsdaten nicht.",
            secret,
            "rechte.zugangsdaten auf true setzen.",
            art25,
        )
    kategorien = {str(k) for k in data.get("datenkategorien") or []}
    art30 = ("DSGVO-Art-13", "DSGVO-Art-30")
    if secret is not None and "zugangsdaten" not in kategorien:
        yield _g(
            "LB-G05-datenkategorie-fehlt",
            Schwere.M,
            "Datenkategorie fehlt: Zugangsdaten",
            "Das Paket verarbeitet Zugangsdaten, datenkategorien nennt sie nicht.",
            secret,
            "„zugangsdaten“ unter datenkategorien ergänzen.",
            art30,
        )
    if code.hosts and kategorien <= {"keine"}:
        stelle = next(iter(code.hosts.values()))
        yield _g(
            "LB-G05-datenkategorie-fehlt",
            Schwere.M,
            "Keine Datenkategorien trotz Endpunkten",
            "Das Paket schickt Daten an Endpunkte, datenkategorien ist leer oder „keine“.",
            stelle,
            "Unter datenkategorien angeben, was an die Endpunkte geht.",
            art30,
        )
    auskunft = [
        f"{e.get('host')}: {e.get('betreiber') or 'Betreiber ohne Angabe'}, {e.get('land')}"
        + (f", {e.get('rechtsgrundlage')}" if e.get("rechtsgrundlage") else "")
        for e in endpunkte
    ]
    speicherung = data.get("speicherung")
    if isinstance(speicherung, dict) and speicherung.get("dauer"):
        auskunft.append(f"Speicherung: {speicherung.get('dauer')}")
    if auskunft:
        yield _g(
            "LB-G06-selbstauskunft",
            Schwere.I,
            "Angaben laut Manifest (Selbstauskunft)",
            "Diese Angaben stammen aus luibui.json und lassen sich statisch nicht prüfen: "
            + visible("; ".join(auskunft), 1500),
            None,
            "Nichts zu tun, solange die Angaben stimmen.",
            ("DSGVO-Art-13",),
            Nachweisgrad.SELBSTAUSKUNFT,
        )


@register
class DsgvoAnalyzer:
    info = AnalyzerInfo(
        name="g_dsgvo",
        titel="G – DSGVO",
        ebenen=frozenset({Ebene.G}),
        scan_arts=frozenset({ScanArt.INTENSIV, ScanArt.LOKAL}),
    )

    def analyze(self, ctx: ScanContext) -> list[Finding]:
        ld = laender(rules_dir())
        code = _code(ctx, ld)
        if not (ctx.root / MANIFEST).is_file():
            return list(_ohne_manifest(code, ld))
        data, findings = _manifest(ctx)
        if data is None:
            return findings + list(_ohne_manifest(code, ld))
        return findings + list(_mit_manifest(data, code, ld))
