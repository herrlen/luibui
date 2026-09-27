# Mitwirken an luibui

luibui ist ein nicht-kommerzielles Projekt unter proprietärer Lizenz (siehe `LICENSE`). Beiträge
von außen nur nach Absprache mit Len; die Rechte an Beiträgen gehen dabei an den Rechteinhaber über.
Die wertvollsten Beiträge sind neue Prüfregeln, Testfälle und gemeldete Fehlalarme.

## Grundregeln

- **Produkttexte auf Deutsch** (UI, Befundtexte, Doku): klar, sachlich, ohne Alarmismus.
  Code, Bezeichner und Commit-Messages auf Englisch.
- **Niemals Code aus geprüften Paketen ausführen**, importieren oder evaluieren. Analyzer lesen und parsen nur.
- **Jede Regel braucht mindestens einen positiven und einen negativen Testfall.** Keine Regel ohne Test.
- Regel-IDs: eigene Regeln `LB-<Prüfkatalog-ID>-<kurzname>`, z. B. `LB-B01-unicode-tags`.

## Testpakete in `corpus/malicious/`

Nur **entschärfte Nachbildungen**:

- Endpunkte ausschließlich `*.invalid` oder `*.example`
- Befehle harmlos (`echo`), keine echte Schadsoftware, keine echten Zugangsdaten, keine funktionierenden Exploits
- Jede Datei beginnt mit dem Kommentar `LUIBUI-TESTFIXTURE: entschärft, nicht ausführen`

Pull Requests, die dagegen verstoßen, werden ohne Diskussion geschlossen.

## Entwicklung

```sh
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e "packages/engine[dev]" -e "apps/api[dev]" -e "apps/worker[dev]"
pytest
ruff check . && ruff format --check . && mypy packages apps/api apps/worker
```

Web: `pnpm install && pnpm lint && pnpm test` in `apps/web`.

## Commits

Ein Commit pro Aufgabe. Gehört er zu einer Task-ID der Sprintplanung, beginnt die Message mit ihr:
`S1-5: add file-layer analyzer`.

## Fehlalarme melden

Öffne ein Issue mit der Regel-ID, einem minimalen Beispiel (ohne echte Zugangsdaten) und der Begründung,
warum der Befund falsch ist.
