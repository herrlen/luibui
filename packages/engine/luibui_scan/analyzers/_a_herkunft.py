"""Analyzer A, part 2: where code comes from (Prüfkatalog A10–A12)."""

import os
import re
from collections.abc import Iterator

from luibui_scan.analyzers._common import file_name, finding, read_text, visible
from luibui_scan.context import ScanContext
from luibui_scan.models import Ebene, Finding, Schwere

# --- A10 Git symlinks, A11 submodules ------------------------------------------------------


def _a10(ctx: ScanContext) -> Iterator[Finding]:
    by_path = {e.path: e for e in ctx.inventory}
    for path in ctx.options.get("git_symlinks", []):
        entry = by_path.get(path)
        if entry is None:
            continue
        target = read_text(ctx, entry, 1024).strip()
        resolved = os.path.normpath(os.path.join(os.path.dirname(path), target))
        if target.startswith("/") or resolved == ".." or resolved.startswith("../"):
            yield finding(
                rule_id="LB-A10-symlink-nach-aussen",
                ebene=Ebene.A,
                schwere=Schwere.M,
                titel="Verknüpfung zeigt aus dem Paket heraus",
                erklaerung=(
                    "Im Repository ist diese Datei eine Verknüpfung auf ein Ziel außerhalb des "
                    "Pakets. Beim Installieren kann sie auf Dateien des Nutzers zeigen. luibui hat "
                    "sie nur als Text mit dem Ziel übernommen."
                ),
                datei=path,
                zeile=None,
                beleg="Ziel: " + visible(target, 200),
                fix="Die Verknüpfung durch eine echte Datei im Paket ersetzen.",
                fix_prompt=f"Ersetze die Verknüpfung {path} durch eine echte Datei im Paket.",
                normbezug=("OWASP-ASI04",),
            )


_SUBMODULE_URL = re.compile(r"^\s*url\s*=\s*(\S+)", re.MULTILINE)


def _a11(ctx: ScanContext) -> Iterator[Finding]:
    for entry in ctx.inventory:
        if file_name(entry) == ".gitmodules":
            urls = _SUBMODULE_URL.findall(read_text(ctx, entry, 64 * 1024))
            yield finding(
                rule_id="LB-A11-submodule",
                ebene=Ebene.A,
                schwere=Schwere.M,
                titel="Submodule werden nicht mitgeprüft",
                erklaerung=(
                    "Das Paket bindet weitere Repositories als Submodule ein. Sie werden bei der "
                    "Installation nachgeladen, sind aber nicht Teil dieser Prüfung."
                ),
                datei=entry.path,
                zeile=None,
                beleg=visible(", ".join(urls[:5]) or "(keine URL)"),
                fix="Den benötigten Code direkt ins Paket übernehmen.",
                fix_prompt="Übernimm den Code der Submodule ins Paket und entferne .gitmodules.",
                normbezug=("OWASP-ASI04", "OWASP-LLM03"),
            )


# --- A12 foreign package sources -----------------------------------------------------------

_PIP_INDEX = re.compile(r"^\s*(--index-url|--extra-index-url|-i|--find-links|-f)[\s=]+(\S+)", re.M)
_PIP_CONF = re.compile(r"^\s*(index-url|extra-index-url|find-links)\s*=\s*(\S+)", re.M)
_NPM_REGISTRY = re.compile(r"^\s*(@[\w.-]+:)?registry\s*=\s*(\S+)", re.M)
_TOML_INDEX = re.compile(
    r"\[\[?tool\.(uv\.index|poetry\.source|pdm\.source)\]?\][^\[]*?url\s*=\s*\"([^\"]+)\"", re.S
)
_OFFICIAL = re.compile(
    r"^https://(pypi\.org|files\.pythonhosted\.org|registry\.npmjs\.org|registry\.yarnpkg\.com)(/|$)"
)


def _a12(ctx: ScanContext) -> Iterator[Finding]:
    for entry in ctx.inventory:
        name = file_name(entry).lower()
        if entry.kind not in ("text", "script"):
            continue
        patterns: list[re.Pattern[str]] = []
        if name.startswith("requirements") and name.endswith((".txt", ".in")):
            patterns = [_PIP_INDEX]
        elif name in ("pip.conf", "pip.ini"):
            patterns = [_PIP_CONF]
        elif name in (".npmrc", ".yarnrc", ".yarnrc.yml"):
            patterns = [_NPM_REGISTRY]
        elif name == "pyproject.toml":
            patterns = [_TOML_INDEX]
        if not patterns:
            continue
        text = read_text(ctx, entry)
        for pattern in patterns:
            for m in pattern.finditer(text):
                url = m.group(2).strip("\"'")
                if _OFFICIAL.match(url):
                    continue
                yield finding(
                    rule_id="LB-A12-fremde-paketquelle",
                    ebene=Ebene.A,
                    schwere=Schwere.H,
                    titel="Pakete kommen aus einer fremden Quelle",
                    erklaerung=(
                        "Die Installation lädt Pakete nicht nur vom offiziellen Verzeichnis. Unter "
                        "gleichem Namen kann dort etwas anderes liegen (Dependency Confusion)."
                    ),
                    datei=entry.path,
                    zeile=text.count("\n", 0, m.start()) + 1,
                    beleg=visible(m.group(0).strip()),
                    fix="Nur das offizielle Paketverzeichnis verwenden oder die Quelle begründen.",
                    fix_prompt=f"Entferne in {entry.path} die Paketquelle {visible(url, 100)}.",
                    normbezug=("OWASP-ASI04", "OWASP-LLM03"),
                )
                break
