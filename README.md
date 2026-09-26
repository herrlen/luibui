# luibui

**Offene Prüfstelle und Register für KI-Skills, Plugins, Tools und MCP-Server.**

luibui prüft, was KI-Chats erweitert, auf Sicherheit und Datenschutz, bevor man es installiert.
Jede Prüfung endet mit einem Bericht: zwei Ampeln (Sicherheit, DSGVO), eine Gesamtbewertung,
eine Note von 0 bis 100 und für jeden Befund einen Beleg, eine Erklärung und einen Vorschlag zur Behebung.

Grün heißt „Keine bekannten Befunde, geprüft am …“, nie „sicher“.

> Status: im Aufbau (Sprint 0). Öffentliche Beta geplant für den 20.11.2026.

## Wie geprüft wird

| Weg | Wo | Umfang |
|---|---|---|
| Schnellscan | luibui.com, ohne Anmeldung | eingeschränkt, ohne Gewähr |
| Intensivscan | app.luibui.com, kostenloses Konto | alle Prüfebenen, Verlauf, Befund-Status |
| Lokal | `luibui scan <pfad>` | offline auf dem eigenen Rechner, kein Upload |

Code aus Uploads wird nie ausgeführt. luibui liest und parst nur. Gehostet wird in Deutschland
bei mittwald, ohne US-Dienste.

## Aufbau

```
apps/web          Next.js: luibui.com und app.luibui.com
apps/api          FastAPI: Auth, Projekte, Annahme, Berichte, Register
apps/worker       Job-Loop, ruft die Engine
packages/engine   luibui-scan: Pipeline, Analyzer, Bewertung, Bericht
packages/cli      luibui: scan, init, lint, publish, install, audit
rules/            eigene Prüfregeln mit Testfällen
corpus/           Testpakete (bösartige nur als entschärfte Nachbildungen)
spec/             JSON-Schemas: Manifest, Befund, Bericht
infra/            docker-compose.yml, Cronjobs
docs/             Konzept, Sprintplanung, Bedrohungsmodell, ADRs
```

## Lokal starten

```sh
docker compose -f infra/docker-compose.yml up --build
```

Die Engine allein:

```sh
pip install -e packages/engine -e packages/cli
luibui scan ./mein-skill
```

## Mitmachen

Siehe [CONTRIBUTING.md](CONTRIBUTING.md). Sicherheitslücken in luibui selbst bitte nicht öffentlich
melden, sondern wie in [SECURITY.md](SECURITY.md) beschrieben.

## Lizenz

AGPL-3.0, siehe [LICENSE](LICENSE). Für `rules/` und `packages/engine` ist MIT vorgeschlagen,
aber noch nicht freigegeben. Bis dahin gilt auch dort AGPL-3.0.
