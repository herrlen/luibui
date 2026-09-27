"""Text rules from YAML: luibui's own rules (``rules/b-muster/``) and vendored ATR rules
(``rules/external/atr/``). Every regex runs with a timeout (ReDoS); a timeout is an error, never a
silent miss, so a crafted input cannot slip through unnoticed.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import regex
import yaml

from luibui_scan.models import Schwere

REGEX_TIMEOUT_SECONDS = 0.5

# ATR category → Prüfkatalog check (docs/luibui_Pruefkatalog.md §3).
ATR_KATALOG = {
    "prompt-injection": "B08",
    "agent-manipulation": "B17",
    "context-exfiltration": "B10",
    "privilege-escalation": "B14",
    "tool-poisoning": "B16",
    "skill-compromise": "B13",
    "excessive-autonomy": "B15",
    "model-abuse": "B17",
    "data-poisoning": "B08",
    "model-security": "B14",
}
# ATR rules never lock a package on their own: many are machine-generated. Critical becomes H.
ATR_SCHWERE = {"critical": Schwere.H, "high": Schwere.H, "medium": Schwere.M, "low": Schwere.N}
ATR_FIELDS = frozenset({"content", "user_input", "tool_description", "tool_response", "tool_args"})
ATR_MATURITY = frozenset({"stable", "experimental"})
ATR_STATUS_EXCLUDED = frozenset({"deprecated", "draft"})


class RuleTimeoutError(Exception):
    """A rule exceeded its time budget on this input."""


class RuleFormatError(Exception):
    """A rule file does not have the expected shape."""


@dataclass(frozen=True, slots=True)
class TextRule:
    id: str
    katalog: str
    schwere: Schwere
    titel: str
    erklaerung: str
    fix: str
    normbezug: tuple[str, ...]
    patterns: tuple[Any, ...]
    """Compiled ``regex`` patterns."""
    mode: str
    """``any``: one pattern suffices; ``all``: every pattern must match somewhere."""
    quelle: str
    """``luibui`` or ``atr``."""
    treffer: tuple[str, ...]
    kein_treffer: tuple[str, ...]

    def search(self, text: str) -> tuple[int, int] | None:
        """First match as ``(start, end)``, or None. Raises ``RuleTimeoutError``."""
        spans = []
        for pattern in self.patterns:
            try:
                m: Any = pattern.search(text, timeout=REGEX_TIMEOUT_SECONDS)
            except TimeoutError:
                raise RuleTimeoutError(self.id) from None
            if m is None:
                if self.mode == "all":
                    return None
                continue
            spans.append(m.span())
            if self.mode == "any":
                start, end = m.span()
                return int(start), int(end)
        if spans and self.mode == "all":
            start, end = min(spans)
            return int(start), int(end)
        return None


def _compile(pattern: str) -> Any:
    return regex.compile(pattern, regex.VERSION0)


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text("utf-8"))
    if not isinstance(data, dict):
        raise RuleFormatError(path.name)
    return data


def load_own(directory: Path) -> list[TextRule]:
    rules = []
    for path in sorted(directory.glob("*.yaml")):
        d = _load_yaml(path)
        try:
            tests = d.get("tests", {})
            rules.append(
                TextRule(
                    id=str(d["id"]),
                    katalog=str(d["katalog"]),
                    schwere=Schwere(d["schwere"]),
                    titel=str(d["titel"]),
                    erklaerung=" ".join(str(d["erklaerung"]).split()),
                    fix=" ".join(str(d["fix"]).split()),
                    normbezug=tuple(d.get("normbezug", [])),
                    patterns=tuple(_compile(p) for p in d["muster"]),
                    mode="any",
                    quelle="luibui",
                    treffer=tuple(tests.get("treffer", [])),
                    kein_treffer=tuple(tests.get("kein_treffer", [])),
                )
            )
        except (KeyError, ValueError, regex.error) as exc:
            raise RuleFormatError(f"{path.name}: {exc}") from None
    return rules


def _atr_norm(refs: Any) -> tuple[str, ...]:
    out: list[str] = []
    if isinstance(refs, dict):
        for key, prefix in (("owasp_agentic", "OWASP-ASI"), ("owasp_llm", "OWASP-LLM")):
            for ref in refs.get(key) or []:
                code = str(ref).split(":")[0].strip()
                num = "".join(c for c in code if c.isdigit())[:2]
                if num and f"{prefix}{num.zfill(2)}" not in out:
                    out.append(f"{prefix}{num.zfill(2)}")
    return tuple(out)


def atr_rule(data: dict[str, Any]) -> TextRule | None:
    """Convert an ATR rule; None if it is not usable for static package text."""
    if str(data.get("maturity", "")).strip('"') not in ATR_MATURITY:
        return None
    if str(data.get("status", "")).strip('"') in ATR_STATUS_EXCLUDED:
        return None
    category = str((data.get("tags") or {}).get("category", ""))
    detection = data.get("detection") or {}
    conditions = detection.get("conditions") or []
    patterns = []
    for c in conditions:
        if not isinstance(c, dict) or c.get("operator") != "regex":
            return None
        if c.get("field") not in ATR_FIELDS:
            return None
        patterns.append(str(c.get("value", "")))
    if not patterns or category not in ATR_KATALOG:
        return None
    try:
        compiled = tuple(_compile(p) for p in patterns)
    except regex.error:
        return None
    tests = data.get("test_cases") or {}
    return TextRule(
        id=str(data["id"]),
        katalog=ATR_KATALOG[category],
        schwere=ATR_SCHWERE.get(str(data.get("severity")), Schwere.M),
        titel=str(data.get("title", data["id"]))[:150],
        erklaerung=" ".join(str(data.get("description", "")).split())[:1000],
        fix="Die betroffene Formulierung entfernen oder so umschreiben, dass sie keine Anweisung "
        "an das Sprachmodell mehr ist.",
        normbezug=_atr_norm(data.get("references")),
        patterns=compiled,
        mode="all" if detection.get("condition") == "all" else "any",
        quelle="atr",
        treffer=tuple(str(t.get("input", "")) for t in tests.get("true_positives") or []),
        kein_treffer=tuple(str(t.get("input", "")) for t in tests.get("true_negatives") or []),
    )


def load_atr(directory: Path) -> list[TextRule]:
    rules = []
    for path in sorted(directory.rglob("ATR-*.yaml")):
        rule = atr_rule(_load_yaml(path))
        if rule is not None:
            rules.append(rule)
    return rules


def failing_tests(rule: TextRule) -> list[str]:
    """Test inputs the rule gets wrong (a positive it misses or a negative it hits)."""
    bad = [f"verpasst: {t[:60]}" for t in rule.treffer if rule.search(t) is None]
    bad += [f"fälschlich: {t[:60]}" for t in rule.kein_treffer if rule.search(t) is not None]
    return bad


@lru_cache(maxsize=4)
def load_all(rules_root: Path) -> tuple[TextRule, ...]:
    own = load_own(rules_root / "b-muster") if (rules_root / "b-muster").is_dir() else []
    atr_dir = rules_root / "external" / "atr" / "rules"
    atr = load_atr(atr_dir) if atr_dir.is_dir() else []
    return tuple(own + atr)
