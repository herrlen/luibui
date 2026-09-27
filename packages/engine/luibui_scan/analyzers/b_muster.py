"""Analyzer B – Anweisungsmuster (Prüfkatalog B08–B17, S1-7).

Runs luibui's own rules (``rules/b-muster/``, may lock) and vendored ATR rules
(``rules/external/atr/``, at most H) over text a model reads as instructions: Markdown, plain
text, YAML, JSON, TOML. Code is layer C. A match inside inline code, a code block or quotes is
treated as a quoted example and lowered to M, so documentation about attacks is not locked.
"""

import re
from pathlib import PurePosixPath

from luibui_scan.analyzers._common import TextFile, finding, rules_dir, text_files, visible
from luibui_scan.analyzers.base import AnalyzerInfo
from luibui_scan.analyzers.registry import register
from luibui_scan.context import ScanContext
from luibui_scan.models import Ebene, Finding, Schwere
from luibui_scan.textrules import TextRule, load_all

INSTRUCTION_SUFFIXES = frozenset(
    {".md", ".mdx", ".markdown", ".txt", ".prompt", ".yaml", ".yml", ".json", ".jsonc", ".toml", ""}
)
LOCKFILES = frozenset(
    {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock", "uv.lock", "cargo.lock",
     "composer.lock", "gemfile.lock", "pipfile.lock", "bun.lock", "npm-shrinkwrap.json"}
)  # fmt: skip
"""Dependency data, not instructions; checked by layer D."""
CHUNK = 256 * 1024
OVERLAP = 2 * 1024
_FENCE = re.compile(r"^\s*(```|~~~)", re.MULTILINE)
_QUOTES = (("`", "`"), ('"', '"'), ("„", "“"), ("“", "”"), ("«", "»"), ("'", "'"))


def _is_instruction_text(f: TextFile) -> bool:
    path = PurePosixPath(f.path.lower())
    return (
        f.entry.kind == "text"
        and path.suffix in INSTRUCTION_SUFFIXES
        and path.name not in LOCKFILES
    )


def _search(rule: TextRule, text: str) -> tuple[int, int] | None:
    """Search in overlapping chunks so no single regex call works on a huge text."""
    if len(text) <= CHUNK:
        return rule.search(text)
    for base in range(0, len(text), CHUNK - OVERLAP):
        span = rule.search(text[base : base + CHUNK])
        if span is not None:
            return base + span[0], base + span[1]
    return None


def _in_code_block(text: str, offset: int) -> bool:
    return len(_FENCE.findall(text, 0, offset)) % 2 == 1


def _quoted(f: TextFile, start: int, end: int) -> bool:
    if _in_code_block(f.text, start):
        return True
    line_start = f.text.rfind("\n", 0, start) + 1
    line_end = f.text.find("\n", end)
    before = f.text[line_start:start]
    after = f.text[end : line_end if line_end != -1 else len(f.text)]
    for open_q, close_q in _QUOTES:
        if open_q == close_q:
            if before.count(open_q) % 2 == 1 and close_q in after:
                return True
        elif before.rfind(open_q) > before.rfind(close_q) and close_q in after:
            return True
    return False


def _finding(rule: TextRule, f: TextFile, start: int, end: int) -> Finding:
    line = f.line_of(start)
    quoted = _quoted(f, start, end)
    schwere = Schwere.M if quoted and rule.schwere in (Schwere.K, Schwere.H) else rule.schwere
    titel = rule.titel + (" (als Beispiel zitiert)" if quoted and schwere != rule.schwere else "")
    erklaerung = rule.erklaerung
    if rule.quelle == "atr":
        erklaerung = (
            f"Regel {rule.id} (Prüfkatalog {rule.katalog}): {erklaerung}"
            if erklaerung
            else f"Regel {rule.id} (Prüfkatalog {rule.katalog})."
        )
    if schwere != rule.schwere:
        erklaerung += (
            " Die Stelle steht in Code oder Anführungszeichen und wirkt wie ein Beispiel; prüfe, "
            "ob sie trotzdem als Anweisung gelesen werden kann."
        )
    return finding(
        rule_id=rule.id,
        ebene=Ebene.B,
        schwere=schwere,
        titel=titel[:200],
        erklaerung=erklaerung[:4000],
        datei=f.path,
        zeile=line,
        beleg=visible(f.line_text(line)),
        fix=rule.fix,
        fix_prompt=(
            f"Entferne oder entschärfe in {f.path}, Zeile {line}, die Formulierung, die "
            f"{rule.titel.lower()} ({rule.id}). Sie darf keine Anweisung an ein Sprachmodell sein."
        ),
        normbezug=rule.normbezug,
    )


@register
class MusterAnalyzer:
    info = AnalyzerInfo(name="b_muster", titel="B – Anweisungsmuster", ebenen=frozenset({Ebene.B}))

    def analyze(self, ctx: ScanContext) -> list[Finding]:
        rules = load_all(rules_dir())
        if not rules:
            raise FileNotFoundError("keine Regeln für B08–B17 gefunden")
        findings = []
        for f in text_files(ctx):
            if not _is_instruction_text(f):
                continue
            for rule in rules:
                span = _search(rule, f.text)  # RuleTimeoutError fails the analyzer: never green
                if span is not None:
                    findings.append(_finding(rule, f, *span))
        return findings
