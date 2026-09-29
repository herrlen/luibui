"""Korrelation (Konzept §4 Schritt 11, S2-5) and finding fingerprints.

An agent follows its instructions: when ``SKILL.md`` tells it to run ``scripts/setup.sh`` or to
read ``references/x.md``, findings in that file matter more than in a file nobody points to. Such
findings move up one level (M → H, H → K) and keep the original level in ``hochgestuft_von``.
Hints (N, I) stay as they are. Only instruction files an agent reads count as the source of a
reference, followed through linked Markdown up to ``MAX_TIEFE`` steps.

Only code is raised, and only findings of what code does (Ebenen A, C, E): a script the agent is
told to run. Markdown on the way is followed but not raised; calibrated on claude-skills-main,
where raising Markdown undid deliberate downgrades of quoted examples and tool-right hints.

Not for single files or the quick scan (Konzept §5): there is nothing to point to or no time.
"""

import hashlib
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath

from luibui_scan.analyzers._common import TextFile
from luibui_scan.context import InventoryEntry
from luibui_scan.models import Achse, Ebene, Finding, Schwere

MAX_TIEFE = 3
_HOCH = {Schwere.M: Schwere.H, Schwere.H: Schwere.K}
_EBENEN = frozenset({Ebene.A, Ebene.C, Ebene.E})

_ANLEITUNG_NAMEN = frozenset({"skill.md", "agents.md", "claude.md", "gemini.md", ".cursorrules",
                              ".windsurfrules", ".clinerules"})  # fmt: skip
_ANLEITUNG_ORDNER = frozenset({"commands", "agents", "prompts", "rules"})
_MARKDOWN = frozenset({".md", ".mdx", ".mdc", ".markdown"})

_LINK = re.compile(r"\]\(\s*<?([^)\s#?>]+)")
_BACKTICK = re.compile(r"`([^`\s]{2,200}\.[A-Za-z0-9]{1,6})`")
_BEFEHL = re.compile(
    r"(?i)(?:\bpython[0-9.]*|\bbash|\bsh|\bzsh|\bnode|\bdeno\s+run|\bbun(?:\s+run)?|\buv\s+run|"
    r"\bnpx\s+tsx|\bruby|\bphp|\bpwsh|\bpowershell(?:\.exe)?(?:\s+-file)?|\bsource)\s+"
    r"([^\s;|&\"'`<>()]+)"
)
_DIREKT = re.compile(r"(?<![\w/.])\./([^\s;|&\"'`<>()]+)")
_PLATZHALTER = re.compile(
    r"^(\$\{?[A-Za-z_][A-Za-z0-9_]*\}?|\{[A-Za-z_]+\}|~|<[^>]+>)/"
)  # ${CLAUDE_PLUGIN_ROOT}/, $SKILL_DIR/, {baseDir}/, <skill>/


def fingerprint(f: Finding) -> str:
    """Stable across versions: rule, file and evidence, never the line number."""
    beleg = " ".join((f.beleg or f.titel).split())
    raw = f"{f.rule_id}\0{f.datei or ''}\0{beleg}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def mit_fingerprints(findings: Iterable[Finding]) -> list[Finding]:
    return [
        f if f.fingerprint else f.model_copy(update={"fingerprint": fingerprint(f)})
        for f in findings
    ]


def ist_anleitung(path: str) -> bool:
    p = PurePosixPath(path.lower())
    return (
        p.name in _ANLEITUNG_NAMEN
        or p.suffix == ".mdc"
        or (p.suffix in _MARKDOWN and bool(_ANLEITUNG_ORDNER & set(p.parts[:-1])))
    )


_CODE = frozenset(
    {".py", ".pyw", ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts", ".sh", ".bash",
     ".zsh", ".go", ".rb", ".php", ".rs", ".java", ".kt", ".cs", ".ps1", ".psm1", ".bat", ".cmd"}
)  # fmt: skip


def ist_code(entry: InventoryEntry) -> bool:
    return PurePosixPath(entry.path.lower()).suffix in _CODE or entry.kind == "script"


@dataclass(frozen=True, slots=True)
class Verweis:
    quelle: str
    zeile: int
    ziel: str


def _kandidaten(text: str) -> Iterable[tuple[int, str]]:
    for pattern in (_LINK, _BACKTICK, _BEFEHL, _DIREKT):
        for m in pattern.finditer(text):
            yield m.start(1), m.group(1)


def _aufloesen(roh: str, quelle: str, dateien: set[str]) -> str | None:
    if "://" in roh or roh.startswith(("#", "mailto:")):
        return None
    pfad = _PLATZHALTER.sub("", roh.strip().rstrip(".,:;")).lstrip("/")
    if pfad.startswith("./"):
        pfad = pfad[2:]
    basis = PurePosixPath(quelle).parent
    for kandidat in (basis / pfad, PurePosixPath(pfad)):
        teile: list[str] = []
        for teil in kandidat.parts:
            if teil == "..":
                if not teile:
                    break  # above the package root
                teile.pop()
            elif teil != ".":
                teile.append(teil)
        else:
            norm = "/".join(teile)
            if norm in dateien and norm != quelle:
                return norm
    return None


def verweise(files: list[TextFile], dateien: set[str]) -> dict[str, Verweis]:
    """Files an agent is pointed to, each with the first instruction that points there."""
    texte = {f.path: f for f in files}
    ziele: dict[str, Verweis] = {}
    offen = [(p, 0) for p in texte if ist_anleitung(p)]
    gesehen = {p for p, _ in offen}
    while offen:
        quelle, tiefe = offen.pop(0)
        f = texte[quelle]
        for pos, roh in _kandidaten(f.text):
            ziel = _aufloesen(roh, quelle, dateien)
            if ziel is None:
                continue
            ziele.setdefault(ziel, Verweis(quelle, f.line_of(pos), ziel))
            weiter = PurePosixPath(ziel).suffix.lower() in _MARKDOWN
            if weiter and ziel in texte and ziel not in gesehen and tiefe + 1 < MAX_TIEFE:
                gesehen.add(ziel)
                offen.append((ziel, tiefe + 1))
    return ziele


def korreliere(findings: list[Finding], ziele: dict[str, Verweis], code: set[str]) -> list[Finding]:
    """Raise findings in code an instruction points to; link findings of one chain."""
    in_quelle: dict[str, list[str]] = defaultdict(list)
    for f in findings:
        if f.datei and f.fingerprint:
            in_quelle[f.datei].append(f.fingerprint)
    out = []
    for f in findings:
        v = ziele.get(f.datei or "") if f.datei in code else None
        passend = v is not None and f.achse is Achse.SICHERHEIT and f.ebene in _EBENEN
        neu = _HOCH.get(f.schwere) if passend else None
        if v is None or neu is None or f.hochgestuft_von is not None:
            out.append(f)
            continue
        verbunden = tuple(
            dict.fromkeys(fp for fp in in_quelle.get(v.quelle, []) if fp != f.fingerprint)
        )
        out.append(
            f.model_copy(
                update={
                    "schwere": neu,
                    "hochgestuft_von": f.schwere,
                    "erklaerung": (
                        f"{f.erklaerung} Hochgestuft: Die Anleitung in {v.quelle}, Zeile "
                        f"{v.zeile}, verweist auf diese Datei; ein Agent folgt ihr."
                    )[:4000],
                    "verweise": verbunden[:50] or None,
                }
            )
        )
    return out
