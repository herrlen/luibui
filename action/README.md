# luibui GitHub Action

Prüft ein KI-Skill-, Plugin- oder MCP-Paket bei jedem Push mit luibui, legt die Befunde als SARIF
in GitHub Code Scanning ab und lässt den Lauf ab einer gewählten Gesamtampel fehlschlagen.

## Einrichten

1. Auf app.luibui.com ein Projekt anlegen, dort unter „In der CI prüfen“ einen **Projekt-Token**
   erzeugen. Er darf nur Prüfungen dieses einen Projekts starten und lesen.
2. Den Token im Repository als Secret `LUIBUI_TOKEN` eintragen.
3. Den Workflow aus dem Entwicklerbereich als `.github/workflows/luibui.yml` anlegen:

```yaml
name: luibui
on:
  push:
    branches: [main]
  pull_request:
permissions:
  contents: read
  security-events: write
jobs:
  pruefen:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - id: luibui
        uses: herrlen/luibui/action@main
        with:
          token: ${{ secrets.LUIBUI_TOKEN }}
          projekt: <Projekt-ID>
          pfad: .
          schwelle: rot
      - if: always() && steps.luibui.outputs.sarif != ''
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: ${{ steps.luibui.outputs.sarif }}
          category: luibui
```

## Eingaben

| Eingabe | Standard | Bedeutung |
| --- | --- | --- |
| `token` | – | Projekt-Token (Secret) |
| `projekt` | – | ID des luibui-Projekts |
| `pfad` | `.` | Ordner des Pakets; geprüft werden nur eingecheckte Dateien (`git archive`) |
| `schwelle` | `rot` | Ab welcher Gesamtampel der Schritt fehlschlägt: `gesperrt`, `rot`, `gelb` oder `nie` |
| `sarif` | `luibui.sarif` | Zieldatei des SARIF-Berichts |
| `zeitlimit` | `900` | Sekunden Wartezeit auf das Ergebnis |
| `api` | `https://api.luibui.com` | Adresse der API |

Ausgaben: `ampel`, `note`, `bericht` (Link in den Entwicklerbereich), `sarif`.

Jede Prüfung kostet wie eine manuelle. Grün heißt „Keine bekannten Befunde“, nicht „sicher“.
Befunde, die du im Entwicklerbereich akzeptiert hast oder die als Fehlalarm bestätigt sind,
erscheinen in Code Scanning als unterdrückt.

## Codeberg und Forgejo

Forgejo Actions führen dieselbe Action aus, wenn sie mit voller URL eingebunden wird. Code
Scanning gibt es dort nicht; die SARIF-Datei lässt sich als Artefakt ablegen, die Ampel und der
Link zum Bericht stehen im Log.

```yaml
on: [push]
jobs:
  pruefen:
    runs-on: docker
    steps:
      - uses: https://code.forgejo.org/actions/checkout@v4
      - uses: https://github.com/herrlen/luibui/action@main
        with:
          token: ${{ secrets.LUIBUI_TOKEN }}
          projekt: <Projekt-ID>
```

Der Runner braucht `bash`, `curl`, `jq` und `git` (oder `zip`).
