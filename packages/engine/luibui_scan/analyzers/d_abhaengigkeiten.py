"""Analyzer D – Abhängigkeiten (Prüfkatalog D01–D05, S1-9).

Two analyzers, so a missing OSV database does not hide the other checks:
- ``d_abhaengigkeiten``: typosquatting (D03), missing lockfile (D04), unsafe sources (D05).
  Manifests are read as data (``json``, ``tomllib``, line patterns), never executed.
- ``d_osv``: known malicious packages (D01) and vulnerabilities (D02) via OSV-Scanner offline.
"""

import json
import re
import tomllib
from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath

from luibui_scan.analyzers._common import finding, read_bytes, visible
from luibui_scan.analyzers.a_dateien import rules_dir
from luibui_scan.analyzers.base import AnalyzerInfo
from luibui_scan.analyzers.registry import register
from luibui_scan.context import InventoryEntry, ScanContext
from luibui_scan.models import Ebene, Finding, Pruefumfang, Schwere
from luibui_scan.tools import osv

SCOPES = frozenset({Pruefumfang.PAKET, Pruefumfang.AUSWAHL})
NORM = ("OWASP-ASI04", "OWASP-LLM03")

NPM_LOCKS = frozenset(
    {
        "package-lock.json",
        "npm-shrinkwrap.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "bun.lock",
        "bun.lockb",
    }
)
PY_LOCKS = frozenset({"uv.lock", "poetry.lock", "pdm.lock", "pipfile.lock", "pylock.toml"})
_REQ_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_SHA = re.compile(r"[0-9a-f]{40}")


@dataclass(frozen=True, slots=True)
class Dep:
    name: str
    spec: str
    """Version specifier or source as written."""
    ecosystem: str
    """``pypi`` or ``npm``."""
    datei: str
    zeile: int | None


def _text(ctx: ScanContext, entry: InventoryEntry) -> str:
    return read_bytes(ctx, entry, 2 * 1024 * 1024).decode("utf-8", errors="replace")


def _norm_py(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirements(ctx: ScanContext, entry: InventoryEntry) -> Iterator[Dep]:
    for i, raw in enumerate(_text(ctx, entry).splitlines(), start=1):
        line = raw.split(" #", 1)[0].strip()
        if not line or line.startswith(("#", "-")):
            continue
        m = _REQ_NAME.match(line)
        if m:
            yield Dep(_norm_py(m.group(1)), line[m.end() :].strip(), "pypi", entry.path, i)


def _pyproject(ctx: ScanContext, entry: InventoryEntry) -> Iterator[Dep]:
    try:
        data = tomllib.loads(_text(ctx, entry))
    except tomllib.TOMLDecodeError:
        return
    project = data.get("project") or {}
    specs = list(project.get("dependencies") or [])
    for group in (project.get("optional-dependencies") or {}).values():
        specs += list(group or [])
    for spec in specs:
        m = _REQ_NAME.match(str(spec))
        if m:
            yield Dep(_norm_py(m.group(1)), str(spec)[m.end() :].strip(), "pypi", entry.path, None)
    poetry = ((data.get("tool") or {}).get("poetry") or {}).get("dependencies") or {}
    for name, value in poetry.items():
        if name.lower() != "python":
            yield Dep(_norm_py(name), json.dumps(value), "pypi", entry.path, None)


def _package_json(ctx: ScanContext, entry: InventoryEntry) -> Iterator[Dep]:
    try:
        data = json.loads(_text(ctx, entry))
    except (ValueError, RecursionError):
        return
    if not isinstance(data, dict):
        return
    for key in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        deps = data.get(key)
        if isinstance(deps, dict):
            for name, spec in deps.items():
                yield Dep(str(name).lower(), str(spec), "npm", entry.path, None)


def dependencies(ctx: ScanContext) -> list[Dep]:
    deps: list[Dep] = []
    for entry in ctx.inventory:
        name = PurePosixPath(entry.path).name.lower()
        if entry.kind not in ("text", "script"):
            continue
        if name.startswith("requirements") and name.endswith((".txt", ".in")):
            deps += _requirements(ctx, entry)
        elif name == "pyproject.toml":
            deps += _pyproject(ctx, entry)
        elif name == "package.json" and "node_modules/" not in entry.path:
            deps += _package_json(ctx, entry)
    return deps


# --- D03 typosquatting ---------------------------------------------------------------------


@lru_cache(maxsize=4)
def popular(ecosystem: str, root: Path) -> frozenset[str]:
    path = root / "data" / f"beliebte-pakete-{ecosystem}.txt"
    try:
        lines = path.read_text("utf-8").splitlines()
    except FileNotFoundError:
        return frozenset()
    return frozenset(n for line in lines if (n := line.split("#", 1)[0].strip().lower()))


def distance(a: str, b: str) -> int:
    """Optimal string alignment distance (Levenshtein plus swapped neighbours)."""
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        d[i][0] = i
    for j in range(len(b) + 1):
        d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[len(a)][len(b)]


def lookalike(name: str, known: frozenset[str]) -> str | None:
    if name in known or len(name) < 5:
        return None
    base = name.split("/")[-1]
    for target in sorted(known):
        t_base = target.split("/")[-1]
        limit = 1 if len(t_base) < 10 else 2
        if abs(len(base) - len(t_base)) <= limit and 0 < distance(base, t_base) <= limit:
            return target
    return None


def _d03(deps: list[Dep]) -> Iterator[Finding]:
    root = rules_dir()
    seen: set[str] = set()
    for dep in deps:
        target = lookalike(dep.name, popular(dep.ecosystem, root))
        if target is None or dep.name in seen:
            continue
        seen.add(dep.name)
        yield finding(
            rule_id="LB-D03-namensverwechslung",
            ebene=Ebene.D,
            schwere=Schwere.H,
            titel=f"Paketname ähnelt „{target}“",
            erklaerung=(
                f"Die Abhängigkeit „{dep.name}“ unterscheidet sich nur in ein, zwei Zeichen vom "
                f"verbreiteten Paket „{target}“. Angreifer registrieren solche Namen, damit ein "
                "Tippfehler Schadcode installiert (Typosquatting)."
            ),
            datei=dep.datei,
            zeile=dep.zeile,
            beleg=visible(f"{dep.name} {dep.spec}".strip()),
            fix=f"Prüfen, ob „{target}“ gemeint ist, und den Namen korrigieren.",
            fix_prompt=f"Ersetze in {dep.datei} {dep.name} durch {target}, falls gemeint.",
            normbezug=NORM,
        )


# --- D04 missing lockfile ------------------------------------------------------------------


def _d04(ctx: ScanContext, deps: list[Dep]) -> Iterator[Finding]:
    names = {PurePosixPath(e.path).name.lower() for e in ctx.inventory}
    npm = [d for d in deps if d.ecosystem == "npm"]
    if npm and not names & NPM_LOCKS:
        yield _d04_finding(npm[0].datei, "npm", "package-lock.json oder pnpm-lock.yaml")
    py = [d for d in deps if d.ecosystem == "pypi"]
    unpinned = [d for d in py if "==" not in d.spec and "@" not in d.spec]
    if unpinned and not names & PY_LOCKS:
        yield _d04_finding(
            unpinned[0].datei,
            "Python",
            "uv.lock, poetry.lock oder feste Versionen mit ==",
            ", ".join(d.name for d in unpinned[:8]),
        )


def _d04_finding(datei: str, welt: str, lock: str, beleg: str | None = None) -> Finding:
    return finding(
        rule_id="LB-D04-kein-lockfile",
        ebene=Ebene.D,
        schwere=Schwere.M,
        titel=f"Versionen der {welt}-Abhängigkeiten nicht festgelegt",
        erklaerung=(
            "Ohne Lockfile installiert jeder Nutzer die jeweils neueste Version. Wird ein Paket "
            "übernommen oder kompromittiert, landet die neue Version ungeprüft beim Nutzer."
        ),
        datei=datei,
        zeile=None,
        beleg=visible(beleg) if beleg else None,
        fix=f"Ein Lockfile beilegen ({lock}).",
        fix_prompt=f"Erzeuge für {datei} ein Lockfile ({lock}) und lege es ins Paket.",
        normbezug=NORM,
    )


# --- D05 unsafe sources --------------------------------------------------------------------

_NPM_REMOTE = re.compile(
    r"^(git\+|git:|github:|gitlab:|bitbucket:|https?:|file:|link:)|^[\w.-]+/[\w.-]+(#.*)?$"
)


def _unsafe(dep: Dep) -> str | None:
    spec = dep.spec.strip()
    if dep.ecosystem == "npm":
        if not _NPM_REMOTE.match(spec):
            return None
        if spec.startswith(("file:", "link:")):
            return "lokaler Pfad außerhalb des Pakets" if "../" in spec else None
        if spec.startswith("http:"):
            return "unverschlüsselte Adresse"
        if "git" in spec.split(":", 1)[0] or re.match(r"^[\w.-]+/[\w.-]+", spec):
            return None if _SHA.search(spec) else "Git-Quelle ohne festen Commit"
        return "direkter Download statt Paketverzeichnis"
    if "http://" in spec:
        return "unverschlüsselte Adresse"
    if "git+" in spec:
        return None if _SHA.search(spec) else "Git-Quelle ohne festen Commit"
    if re.search(r"@\s*(file:|\.\./)", spec):
        return "lokaler Pfad außerhalb des Pakets"
    return None


def _d05(deps: list[Dep]) -> Iterator[Finding]:
    for dep in deps:
        why = _unsafe(dep)
        if why is None:
            continue
        yield finding(
            rule_id="LB-D05-unsichere-quelle",
            ebene=Ebene.D,
            schwere=Schwere.M,
            titel=f"Abhängigkeit aus unsicherer Quelle: {why}",
            erklaerung=(
                f"„{dep.name}“ kommt nicht aus dem Paketverzeichnis, sondern aus einer Quelle, "
                "deren Inhalt sich ändern kann oder nicht nachprüfbar ist."
            ),
            datei=dep.datei,
            zeile=dep.zeile,
            beleg=visible(f"{dep.name} {dep.spec}".strip()),
            fix="Die Abhängigkeit aus dem offiziellen Verzeichnis mit fester Version beziehen.",
            fix_prompt=f"Ersetze in {dep.datei} die Quelle von {dep.name} durch eine Version.",
            normbezug=NORM,
        )


@register
class AbhaengigkeitenAnalyzer:
    info = AnalyzerInfo(
        name="d_abhaengigkeiten",
        titel="D – Abhängigkeiten",
        ebenen=frozenset({Ebene.D}),
        scopes=SCOPES,
    )

    def analyze(self, ctx: ScanContext) -> list[Finding]:
        deps = dependencies(ctx)
        return [*_d03(deps), *_d04(ctx, deps), *_d05(deps)]


# --- D01, D02 via OSV ----------------------------------------------------------------------


def _d02_schwere(cvss: float | None) -> Schwere:
    if cvss is None:
        return Schwere.M
    if cvss >= 9.0:
        return Schwere.H
    if cvss >= 7.0:
        return Schwere.M
    return Schwere.N


@register
class OsvAnalyzer:
    info = AnalyzerInfo(
        name="d_osv",
        titel="D – Bekannte Schwachstellen und Schadpakete (OSV)",
        ebenen=frozenset({Ebene.D}),
        scopes=SCOPES,
    )

    def analyze(self, ctx: ScanContext) -> list[Finding]:
        findings = []
        for v in osv.scan(ctx.root):
            malicious = v.id.startswith("MAL-")
            label = f"{v.package} {v.version}".strip()
            findings.append(
                finding(
                    rule_id=f"osv:{v.id}",
                    ebene=Ebene.D,
                    schwere=Schwere.K if malicious else _d02_schwere(v.cvss),
                    titel=(
                        f"Bekanntes Schadpaket: {label}"
                        if malicious
                        else f"Bekannte Schwachstelle in {label}"
                    )[:200],
                    erklaerung=(
                        (
                            "Dieses Paket steht in der Datenbank bekannter Schadpakete. "
                            "Es darf nicht installiert werden."
                            if malicious
                            else "Die Version hat eine bekannte Schwachstelle"
                            + (f" (CVSS {v.cvss:.1f})" if v.cvss is not None else "")
                            + "."
                        )
                        + (f" Kurzbeschreibung laut OSV: {v.summary}" if v.summary else "")
                        + f" Quelle: https://osv.dev/{v.id} (CC-BY 4.0)."
                    ),
                    datei=v.datei or None,
                    zeile=None,
                    beleg=visible(" · ".join([label, v.ecosystem, v.id, *v.aliases[:2]])),
                    fix=(
                        "Die Abhängigkeit entfernen und prüfen, ob sie schon installiert wurde."
                        if malicious
                        else "Auf eine Version ohne diese Schwachstelle aktualisieren."
                    ),
                    fix_prompt=(
                        f"Entferne {v.package} aus {v.datei or 'den Abhängigkeiten'}."
                        if malicious
                        else f"Aktualisiere {v.package} in {v.datei or 'den Abhängigkeiten'} auf "
                        f"eine Version, die {v.id} behebt."
                    ),
                    normbezug=NORM,
                )
            )
        return findings
