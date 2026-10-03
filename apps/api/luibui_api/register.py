"""Names in the register (S4-1): rules for namespace and package names, reserved names and the
check for names that can be mistaken for an existing one (Prüfkatalog H04).

A name that only differs from an existing one by look-alike characters (``0``/``o``, ``1``/``l``,
``rn``/``m``), by hyphens, or, from five characters on, by one typing step (one letter more,
less, different or two swapped) is too close: ``anthrop1c``, ``open-ai``, ``modelcontextprotocoll``.
Names of the same owner may be close to each other; they cannot fool anyone.
"""

import re
from collections.abc import Iterable

NAME = re.compile(r"^[a-z0-9](?:[a-z0-9]|-(?=[a-z0-9])){1,38}$")
"""2 to 39 characters: lower-case letters, digits, single hyphens inside (like GitHub)."""

RESERVIERT = frozenset(
    {
        # luibui itself and words that would look official
        "luibui", "admin", "administrator", "api", "app", "www", "root", "system", "support",
        "security", "sicherheit", "hilfe", "help", "info", "kontakt", "offiziell", "official",
        "verified", "geprueft", "register", "registry", "moderation", "abuse", "test",
        # providers and well-known projects whose names an attacker would borrow
        "anthropic", "claude", "openai", "chatgpt", "gpt", "google", "gemini", "deepmind",
        "microsoft", "copilot", "github", "gitlab", "codeberg", "mistral", "mistralai", "meta",
        "llama", "huggingface", "ollama", "openwebui", "modelcontextprotocol", "mcp", "cursor",
        "apple", "amazon", "aws", "azure", "mittwald", "npm", "pypi", "python", "node",
    }
)  # fmt: skip

_ERSATZ = (
    # single characters first, so that "c1aude" becomes "claude" before "cl" is folded
    ("0", "o"), ("1", "l"), ("i", "l"), ("3", "e"), ("4", "a"), ("5", "s"), ("7", "t"),
    ("8", "b"), ("-", ""), ("_", ""), ("rn", "m"), ("vv", "w"), ("cl", "d"),
)  # fmt: skip


PAKETNAME = re.compile(r"^[a-z0-9](?:[a-z0-9]|-(?=[a-z0-9])){1,49}$")
"""Package names: like namespaces, up to 50 characters (spec/luibui.schema.json)."""


def name_fehler(name: str) -> str | None:
    """German reason why ``name`` is not a valid name, or None."""
    if not NAME.match(name):
        return (
            "2 bis 39 Zeichen: Kleinbuchstaben, Ziffern und einzelne Bindestriche, nicht am "
            "Anfang oder Ende."
        )
    return None


def skelett(name: str) -> str:
    """The name as it looks: look-alike characters folded, hyphens dropped."""
    s = name.lower()
    for alt, neu in _ERSATZ:
        s = s.replace(alt, neu)
    return s


def _ein_schritt(a: str, b: str) -> bool:
    """True if ``a`` and ``b`` differ by at most one insertion, deletion, substitution or swap
    of two neighbouring characters (Damerau-Levenshtein ≤ 1)."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        diff = [i for i in range(la) if a[i] != b[i]]
        if len(diff) == 1:
            return True
        return (
            len(diff) == 2
            and diff[1] == diff[0] + 1
            and a[diff[0]] == b[diff[1]]
            and a[diff[1]] == b[diff[0]]
        )
    kurz, lang = (a, b) if la < lb else (b, a)
    i = 0
    while i < len(kurz) and kurz[i] == lang[i]:
        i += 1
    return kurz[i:] == lang[i + 1 :]


def zu_nah(a: str, b: str) -> bool:
    sa, sb = skelett(a), skelett(b)
    if sa == sb:
        return True
    return min(len(sa), len(sb)) >= 5 and _ein_schritt(sa, sb)


def verwechslung(name: str, bestehende: Iterable[str]) -> str | None:
    """The reserved or existing name that ``name`` can be mistaken for, or None."""
    for r in sorted(RESERVIERT):
        if zu_nah(name, r):
            return r
    for b in bestehende:
        if b != name and zu_nah(name, b):
            return b
    return None
