"""S3-13: lists of people in data files (G07) via Presidio, one value per line in a separate
subprocess that returns counts only, and personal data in notebook outputs via the regular
expressions. Most tests replace Presidio; the last one runs the real thing when
``LUIBUI_PRESIDIO_PYTHON`` points to a Presidio venv (worker image, benchmark)."""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from luibui_scan.analyzers import g_personendaten
from luibui_scan.analyzers.g_personendaten import PersonendatenAnalyzer
from luibui_scan.context import ScanContext
from luibui_scan.inventory import build_inventory
from luibui_scan.models import Achse, Pruefumfang, ScanArt, Schwere
from luibui_scan.scoring import is_blocklisted
from luibui_scan.tools import ToolError, presidio
from luibui_scan.tools._presidio_runner import zaehlen

MARK = "LUIBUI-TESTFIXTURE: entschärft, nicht ausführen"
NAMEN = [f"{v} {n}" for v in ("Anna", "Bert", "Clara") for n in ("Becker", "Yilmaz", "Wagner")]
STAEDTE = ["Berlin", "Hamburg", "Köln", "München", "Leipzig", "Bremen"]


def ctx_for(tmp_path: Path, files: dict[str, str]) -> ScanContext:
    root = tmp_path / "pkg"
    for rel, content in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(content)
    return ScanContext(
        root=root,
        scan_art=ScanArt.INTENSIV,
        pruefumfang=Pruefumfang.PAKET,
        inventory=build_inventory(root).entries,
    )


def notebook(*ausgaben: str) -> str:
    zellen = [
        {"cell_type": "markdown", "source": [MARK]},
        {
            "cell_type": "code",
            "source": ["df.head()"],
            "outputs": [{"output_type": "stream", "text": list(ausgaben)}],
        },
    ]
    return json.dumps({"cells": zellen, "nbformat": 4})


class FakePresidio:
    """A value is a name when it is in NAMEN; records what it received."""

    def __init__(self) -> None:
        self.texte: dict[str, str] = {}

    def __call__(self, texte: dict[str, str], arbeitsordner: Path) -> dict[str, dict[str, int]]:
        self.texte = dict(texte)
        return {
            k: {"werte": len(v.split("\n")), "personen": sum(z in NAMEN for z in v.split("\n"))}
            for k, v in texte.items()
        }


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakePresidio:
    f = FakePresidio()
    monkeypatch.setattr(presidio, "zaehlen", f)
    return f


def csv_mit(namen: list[str], trenner: str = ";") -> str:
    zeilen = [f"name{trenner}ort{trenner}betrag"]
    zeilen += [f"{n}{trenner}{STAEDTE[i % 6]}{trenner}{i}.50" for i, n in enumerate(namen)]
    return "\n".join(zeilen) + "\n"


# --- analyzer ----------------------------------------------------------------------------------


def test_a_column_of_names_is_reported_without_values(tmp_path: Path, fake: FakePresidio) -> None:
    ctx = ctx_for(tmp_path, {"daten/kunden.csv": csv_mit(NAMEN), "SKILL.md": f"<!-- {MARK} -->"})
    [f] = PersonendatenAnalyzer().analyze(ctx)
    assert (f.rule_id, f.schwere, f.achse) == (
        "LB-G07-personenbezogene-daten",
        Schwere.M,
        Achse.DSGVO,
    )
    assert f.datei == "daten/kunden.csv"
    assert "in der Spalte „name“ 9 von 9 Werten mit Personennamen" in f.erklaerung
    assert not is_blocklisted(f)
    assert all(n not in (f.beleg or "") + f.erklaerung for n in NAMEN)
    # One value per line, one text per column; amounts never go out, cities do (no names there).
    gesendet = sorted(fake.texte.values())
    assert "\n".join(NAMEN) in gesendet and "\n".join(STAEDTE) in gesendet
    assert not any("50" in t for t in gesendet)


@pytest.mark.parametrize("trenner", [",", "\t", "|"])
def test_other_separators_and_tsv(tmp_path: Path, fake: FakePresidio, trenner: str) -> None:
    datei = "k.tsv" if trenner == "\t" else "k.csv"
    [f] = PersonendatenAnalyzer().analyze(ctx_for(tmp_path, {datei: csv_mit(NAMEN, trenner)}))
    assert "Spalte „name“" in f.erklaerung


def test_json_lines_by_key(tmp_path: Path, fake: FakePresidio) -> None:
    zeilen = "\n".join(json.dumps({"kunde": n, "plz": "10115", "aktiv": True}) for n in NAMEN)
    [f] = PersonendatenAnalyzer().analyze(ctx_for(tmp_path, {"k.jsonl": zeilen + "\nkaputt\n"}))
    assert "in der Spalte „kunde“ 9 von 9 Werten" in f.erklaerung


def test_few_names_or_a_minority_of_names_stay_quiet(tmp_path: Path, fake: FakePresidio) -> None:
    gemischt = NAMEN[:4] + [f"Produkt {c}" for c in "ABCDEFGHIJ"]
    files = {"wenige.csv": csv_mit(NAMEN[:4]), "gemischt.csv": csv_mit(gemischt)}
    assert PersonendatenAnalyzer().analyze(ctx_for(tmp_path, files)) == []


def test_presidio_is_not_started_without_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def nie(texte: dict[str, str], _: Path) -> dict[str, dict[str, int]]:
        assert not texte, "Presidio darf nicht starten"
        return {}

    monkeypatch.setattr(presidio, "zaehlen", nie)
    files = {"SKILL.md": "# x\n" + "\n".join(NAMEN), "app.py": "x = 1\n", "z.csv": "a;b\n1;2\n"}
    assert PersonendatenAnalyzer().analyze(ctx_for(tmp_path, files)) == []


def test_files_the_regex_already_reports_are_left_to_a_dateien(
    tmp_path: Path, fake: FakePresidio
) -> None:
    mails = "\n".join(f"{n};{i}@firma-{i}.de" for i, n in enumerate(NAMEN))
    assert PersonendatenAnalyzer().analyze(ctx_for(tmp_path, {"k.csv": "n;m\n" + mails})) == []
    assert fake.texte == {}


def test_notebook_outputs_get_the_regex_but_never_presidio(
    tmp_path: Path, fake: FakePresidio
) -> None:
    mails = "".join(f"{i}@firma-{i}.de\n" for i in range(6))
    files = {
        "mails.ipynb": notebook(mails),
        "namen.ipynb": notebook(*(f"{n}  Berlin\n" for n in NAMEN)),
        "leer.ipynb": notebook(),
    }
    [f] = PersonendatenAnalyzer().analyze(ctx_for(tmp_path, files))
    assert f.datei == "mails.ipynb" and "6 E-Mail-Adressen" in f.erklaerung
    assert "Ausgaben des Notebooks" in f.erklaerung
    assert fake.texte == {}


def test_sample_per_file_and_per_check(tmp_path: Path, fake: FakePresidio) -> None:
    n = 2 * g_personendaten.STICHPROBE_DATEI // 100

    def buchstaben(j: int) -> str:  # values with digits count as identifiers, not names
        return "".join(chr(97 + (j // 26**k) % 26) for k in range(3))

    def gross(i: int) -> str:
        zeilen = (f"Datei{'ABCDEF'[i]} {buchstaben(j)};{'x' * 80}\n" for j in range(n))
        return "name;notiz\n" + "".join(zeilen)

    PersonendatenAnalyzer().analyze(ctx_for(tmp_path, {f"t{i}.csv": gross(i) for i in range(6)}))
    namen = [t for t in fake.texte.values() if t.startswith("Datei")]
    assert sorted(t.split()[0] for t in namen) == [f"Datei{c}" for c in "ABCD"]
    # 4 × 64 KB, the rest is beyond the per-check budget; per column at most MAX_WERTE values.
    assert all(len(t.split("\n")) == g_personendaten.MAX_WERTE for t in namen)


def test_missing_presidio_fails_the_analyzer_only_when_needed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LUIBUI_PRESIDIO_PYTHON", raising=False)
    assert PersonendatenAnalyzer().analyze(ctx_for(tmp_path / "a", {"SKILL.md": "# x"})) == []
    with pytest.raises(ToolError):
        PersonendatenAnalyzer().analyze(ctx_for(tmp_path / "b", {"k.csv": csv_mit(NAMEN)}))


# --- runner and adapter ------------------------------------------------------------------------


def test_runner_counts_lines_that_are_mostly_a_name() -> None:
    def analysieren(block: str) -> list[Any]:
        treffer = []
        for name, score in (("Anna Becker", 0.85), ("Bert", 0.85), ("Clara Wagner", 0.4)):
            start = 0
            while (i := block.find(name, start)) >= 0:
                treffer.append(
                    SimpleNamespace(entity_type="PERSON", start=i, end=i + len(name), score=score)
                )
                start = i + 1
        treffer.append(SimpleNamespace(entity_type="LOCATION", start=0, end=4, score=0.9))
        return treffer

    text = "\n".join(["Anna Becker", "Bert Yilmaz", "Bert-Brunnen-Platz 12", "Clara Wagner", ""])
    # "Bert" covers 4 of 11 characters in "Bert Yilmaz": not mostly a name; Clara: score too low.
    assert zaehlen(text, analysieren) == {"werte": 4, "personen": 1}


def test_runner_splits_long_columns_into_blocks() -> None:
    bloecke: list[str] = []

    def analysieren(block: str) -> list[Any]:
        bloecke.append(block)
        return [
            SimpleNamespace(entity_type="PERSON", start=i, end=i + 11, score=0.9)
            for i in range(0, len(block), 12)
        ]

    text = "\n".join(["Anna Becker"] * 5000)
    assert zaehlen(text, analysieren) == {"werte": 5000, "personen": 5000}
    assert len(bloecke) > 1 and all(not b.startswith("\n") for b in bloecke)


def _fake_runner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: str) -> None:
    runner = tmp_path / "runner.py"
    runner.write_text(code)
    monkeypatch.setattr(presidio, "RUNNER", runner)
    monkeypatch.setenv("LUIBUI_PRESIDIO_PYTHON", sys.executable)


def test_adapter_passes_texts_and_reads_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_runner(
        tmp_path,
        monkeypatch,
        "import json, os, sys\n"
        "e = json.load(sys.stdin)\n"
        "erlaubt = {'PATH', 'HOME', 'LANG', 'LC_CTYPE', '__CF_USER_TEXT_ENCODING'}\n"
        "assert set(os.environ) <= erlaubt, sorted(os.environ)\n"
        "n = {t['id']: {'werte': len(t['text'])} for t in e['texte']}\n"
        "print(json.dumps({'ergebnisse': n}))\n",
    )
    assert presidio.zaehlen({"0": "abc", "1": "x"}, tmp_path) == {
        "0": {"werte": 3},
        "1": {"werte": 1},
    }
    assert presidio.zaehlen({}, tmp_path) == {}
    assert [p.name for p in tmp_path.iterdir()] == ["runner.py"]  # temporary HOME removed


@pytest.mark.parametrize(
    "code",
    [
        "import sys; sys.exit(3)",
        "print('kein json')",
        "print('[1, 2]')",
        'print(\'{"ergebnisse": {"0": [1]}}\')',
        "import time; time.sleep(5)",
    ],
)
def test_adapter_errors_become_tool_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: str
) -> None:
    _fake_runner(tmp_path, monkeypatch, code)
    with pytest.raises(ToolError):
        presidio.zaehlen({"0": "abc"}, tmp_path, timeout=2)


@pytest.mark.skipif(
    not os.environ.get("LUIBUI_PRESIDIO_PYTHON"),
    reason="Presidio nicht installiert (LUIBUI_PRESIDIO_PYTHON setzen)",
)
def test_real_presidio_finds_a_customer_list_but_not_code_lists(tmp_path: Path) -> None:
    laender = "code;land;hauptstadt\n" + "\n".join(
        f"{c};{land};{stadt}"
        for c, land, stadt in [
            ("DE", "Deutschland", "Berlin"),
            ("FR", "Frankreich", "Paris"),
            ("IT", "Italien", "Rom"),
            ("ES", "Spanien", "Madrid"),
            ("PL", "Polen", "Warschau"),
            ("AT", "Österreich", "Wien"),
            ("NL", "Niederlande", "Amsterdam"),
        ]
    )
    ctx = ctx_for(tmp_path, {"kunden.csv": csv_mit(NAMEN), "laender.csv": laender})
    assert [f.datei for f in PersonendatenAnalyzer().analyze(ctx)] == ["kunden.csv"]
