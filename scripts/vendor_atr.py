"""Vendor ATR rules into rules/external/atr/ (S1-7).

Usage: uv run python scripts/vendor_atr.py <atr-checkout> <tag> <benign-repo> [<benign-repo> …]

Takes only rules usable on static package text (maturity stable/experimental, not deprecated or
draft, regex conditions on text fields), only those that pass their own test cases with our regex
engine, and only those that stay silent on the instruction texts of trusted benign repositories and
of our own benign corpus ``corpus/benign/`` (false-positive calibration, Prüfkatalog §1). Files are
copied unchanged (MIT, see LICENSE).
"""

import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from luibui_scan.textrules import RuleTimeoutError, TextRule, atr_rule, failing_tests

REPO = Path(__file__).resolve().parents[1]
DEST = REPO / "rules" / "external" / "atr"
OWN_BENIGN = REPO / "corpus" / "benign"


TEXT_SUFFIXES = {".md", ".txt", ".yaml", ".yml", ".json", ".toml"}


def git_head(repo: Path) -> str:
    return subprocess.run(  # noqa: S603 - developer script, fixed argv
        ["git", "-C", str(repo), "rev-parse", "HEAD"],  # noqa: S607
        check=True, capture_output=True, text=True,
    ).stdout.strip()  # fmt: skip


def benign_texts(repos: list[Path]) -> list[tuple[str, str]]:
    texts = []
    for repo in repos:
        for path in sorted(repo.rglob("*")):
            if ".git" in path.parts or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if path.is_file() and not path.is_symlink() and path.stat().st_size < 5_000_000:
                texts.append(
                    (f"{repo.name}/{path.relative_to(repo)}", path.read_text("utf-8", "replace"))
                )
    return texts


def benign_hit(rule: TextRule, texts: list[tuple[str, str]]) -> str | None:
    for name, text in texts:
        try:
            if rule.search(text) is not None:
                return name
        except RuleTimeoutError:
            return f"{name} (Zeitlimit)"
    return None


def main(src: Path, tag: str, benign: list[Path]) -> None:
    commit = git_head(src)
    texts = benign_texts([*benign, OWN_BENIGN])
    if DEST.exists():
        shutil.rmtree(DEST)
    (DEST / "rules").mkdir(parents=True)
    shutil.copy(src / "LICENSE", DEST / "LICENSE")
    taken, skipped, failed, noisy = [], 0, [], []
    for path in sorted((src / "rules").rglob("ATR-*.yaml")):
        rule = atr_rule(yaml.safe_load(path.read_text("utf-8")))
        if rule is None:
            skipped += 1
            continue
        try:
            bad = failing_tests(rule)
        except RuleTimeoutError:
            bad = ["Zeitlimit"]
        if bad or not rule.treffer:
            failed.append(f"{rule.id}: {bad[0] if bad else 'keine Testfälle'}")
            continue
        hit = benign_hit(rule, texts)
        if hit is not None:
            noisy.append(f"{rule.id}: schlägt an in `{hit}`")
            continue
        target = DEST / "rules" / path.relative_to(src / "rules")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, target)
        taken.append(rule.id)
    lines = [
        "# ATR-Regeln (übernommen)",
        "",
        "Quelle: https://github.com/Agent-Threat-Rule/agent-threat-rules",
        f"Stand: Tag `{tag}`, Commit `{commit}`. Lizenz: MIT (siehe `LICENSE`).",
        "Die Namen „ATR“ und „Agent Threat Rules“ sind Marken der Urheber und nicht Teil der",
        "MIT-Lizenz; luibui nennt die Regeln nur sachlich mit ihrer ID.",
        "",
        "Erzeugt mit `scripts/vendor_atr.py`. Übernommen werden nur Regeln mit Reifegrad",
        "`stable` oder `experimental`, reinen Regex-Bedingungen auf Textfeldern und bestandenen",
        "eigenen Testfällen unter unserer Regex-Engine.",
        "",
        f"- übernommen: {len(taken)}",
        f"- nicht geeignet (Reifegrad, Status, Felder, Operatoren): {skipped}",
        f"- eigene Testfälle nicht bestanden: {len(failed)}",
        f"- Fehlalarm im gutartigen Vergleichsbestand: {len(noisy)}",
        "",
        "## Gutartiger Vergleichsbestand",
        "",
        *[f"- `{r.name}` Commit `{git_head(r)[:12]}`" for r in benign],
        "- `corpus/benign/` (eigener Korpus, Stand dieses Repositorys)",
        f"- zusammen {len(texts)} Textdateien (Markdown, Text, YAML, JSON, TOML)",
        "",
        "## Nicht übernommen wegen Testfällen",
        "",
        *[f"- {line}" for line in failed],
        "",
        "## Nicht übernommen wegen Fehlalarmen",
        "",
        *[f"- {line}" for line in noisy],
        "",
    ]
    (DEST / "QUELLE.md").write_text("\n".join(lines), "utf-8")
    print(
        f"übernommen {len(taken)}, ungeeignet {skipped}, Tests nicht bestanden {len(failed)}, "
        f"Fehlalarm {len(noisy)}"
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2], [Path(p) for p in sys.argv[3:]])
