"""Runs inside the separate Presidio venv (``LUIBUI_PRESIDIO_PYTHON``), started by
``tools/presidio.py`` with ``python -I`` and an empty environment. Not imported by the engine.

Input on stdin: ``{"texte": [{"id": "...", "text": "..."}]}``, each text one table column with
one value per line. Output on stdout: ``{"ergebnisse": {"<id>": {"werte": 60, "personen": 54}}}``:
how many lines there are and how many of them are mostly a person's name. Values never leave
this process, so they cannot end up in a report or a log.

Per value, not per free text: the small German model calls countries, airports and currencies
persons when it reads whole files (measured on public code lists, docs/log.md 02.10.2026). A
column where most values are names is a much stronger signal than many name-like words.
"""

import json
import sys
from collections.abc import Callable, Iterable, Iterator
from typing import Any

BLOCK = 20_000
"""spaCy handles long texts slowly and with much memory; lines go in blocks of about this size."""
MIN_SCORE = 0.6
MIN_ANTEIL = 0.5
"""A line counts as a name when PERSON spans cover at least half of its characters."""


def _bloecke(zeilen: list[str]) -> Iterator[list[str]]:
    block: list[str] = []
    laenge = 0
    for z in zeilen:
        if block and laenge + len(z) > BLOCK:
            yield block
            block, laenge = [], 0
        block.append(z)
        laenge += len(z) + 1
    if block:
        yield block


def zaehlen(text: str, analysieren: Callable[[str], Iterable[Any]]) -> dict[str, int]:
    """Lines, and lines that are mostly a person's name. ``analysieren`` returns Presidio
    RecognizerResults for one block of lines joined by line breaks."""
    zeilen = text.split("\n")
    personen = 0
    for block in _bloecke(zeilen):
        anfaenge, pos = [], 0
        for z in block:
            anfaenge.append(pos)
            pos += len(z) + 1
        abdeckung = [0] * len(block)
        for r in analysieren("\n".join(block)):
            if r.entity_type != "PERSON" or r.score < MIN_SCORE:
                continue
            for i, a in enumerate(anfaenge):
                ueberlappung = min(r.end, a + len(block[i])) - max(r.start, a)
                if ueberlappung > 0:
                    abdeckung[i] += ueberlappung
        for i, z in enumerate(block):
            zeichen = len(z.strip())
            if zeichen and abdeckung[i] / zeichen >= MIN_ANTEIL:
                personen += 1
    return {"werte": sum(1 for z in zeilen if z.strip()), "personen": personen}


def main() -> int:
    # Imported here: presidio exists only in the separate Presidio venv.
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider

    eingabe = json.load(sys.stdin)
    nlp = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "de", "model_name": "de_core_news_sm"}],
        }
    ).create_engine()
    engine = AnalyzerEngine(nlp_engine=nlp, supported_languages=["de"])

    def analysieren(block: str) -> Iterable[Any]:
        return engine.analyze(text=block, language="de", entities=["PERSON"])  # type: ignore[no-any-return]

    ergebnisse = {
        str(t["id"]): zaehlen(str(t["text"]), analysieren) for t in eingabe.get("texte", [])
    }
    json.dump({"ergebnisse": ergebnisse}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
