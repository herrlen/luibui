# luibui – Konzept v2: Prüfstelle und Register für KI-Skills, Plugins und MCP-Server

> Stand: 26.09.2026 · Owner: Len · Domain: **luibui.com** · Lizenz: **AGPL-3.0**
> Hosting: mittwald, Projekt `p-yw5cv5` · Ausrichtung wie lensuh.de: offen, kostenlos, nicht-kommerziell, spendenfinanziert
> Gehört zusammen mit: `luibui_Sprintplanung.md`, `luibui_Pruefkatalog.md`, `CLAUDE.md`

---

## 1. Was luibui ist

**Eine offene Prüfstelle für alles, was KI-Chats erweitert: Skills, Plugins, Tools und MCP-Server. Mit Register.**

Jeder lädt ein Projekt hoch oder gibt eine Git-URL an. luibui prüft es auf Sicherheit und Datenschutz und liefert einen Bericht mit Ampel. Wer will, veröffentlicht das geprüfte Paket danach im Register. Dort kann es jeder in Claude, ChatGPT, Gemini, Mistral, Open WebUI oder jedem MCP-Client installieren.

**Warum das gebraucht wird:** 2026 hatte mehr als jeder dritte öffentlich angebotene Skill ein Sicherheitsproblem, jeder achte ein kritisches (Snyk ToxicSkills). Schadcode in MCP-Servern ist dokumentiert. Die Marketplaces der Anbieter prüfen nur einmalig oder gar nicht, und niemand prüft herstellerübergreifend und DSGVO-konform in Europa.

**Kernversprechen**
1. **Prüfen, bevor man installiert.** Jedes Projekt, egal ob eigenes oder fremdes, bekommt einen nachvollziehbaren Bericht.
2. **Zwei Ampeln:** Sicherheit und DSGVO. Dazu eine Gesamtbewertung.
3. **Ehrlich:** „Keine bekannten Befunde, geprüft am …“, nie „sicher“.
4. **Offen:** Regeln, Engine und Bericht-Format sind Open Source. Die Community kann Regeln ergänzen.
5. **Eigener Bereich:** Jeder Entwickler hat auf app.luibui.com seinen privaten Bereich mit Projekten, Dateien und dem Verlauf seiner Prüfungen.
6. **In Deutschland:** Hosting bei mittwald, keine US-Dienste, Dateien verschlüsselt und nur für den Eigentümer sichtbar.

**Zielgruppe:** Entwickler:innen, die ihre Skills vor der Veröffentlichung prüfen wollen, und alle, die fremde Skills installieren wollen. Dazu gehören auch Agenturen, Vereine, Behörden und Unternehmen.

**Was luibui nicht ist:** kein Model Hub, kein KI-Chat als Hauptprodukt, keine Zertifizierungsstelle mit Haftung.

---

## 2. Ablauf

```
 ┌───────────────┐   ┌──────────────┐   ┌──────────────┐   ┌───────────────────┐
 │ Datei(en),    │   │              │   │  Bericht     │   │ privat behalten   │
 │ Ordner, ZIP,  │──▶│   Prüfung    │──▶│  2 Ampeln    │──▶│ oder              │
 │ Git, CLI      │   │ (Warteschl.) │   │  Note 0–100  │   │ veröffentlichen → │
 └───────────────┘   └──────────────┘   │  Fix-Prompts │   │ Register          │
                                        └──────────────┘   └───────────────────┘
```

| Eingang | Wer | Wohin | Limit |
|---|---|---|---|
| **Einzelne Datei** (z. B. `SKILL.md`, `server.py`, `tools.json`, ein Skript) | angemeldete Entwickler auf **app.luibui.com** | eigener Bereich, gespeichert | 10 MB pro Datei |
| **Mehrere Dateien oder ganzer Ordner** per Drag & Drop | angemeldete Entwickler auf **app.luibui.com** | eigener Bereich, gespeichert | 1.000 Dateien, 50 MB gesamt |
| **Text einfügen** (z. B. eine Skill-Anweisung oder Tool-Beschreibung) | angemeldete Entwickler auf **app.luibui.com** | eigener Bereich, gespeichert | 200 KB |
| **Archiv** (ZIP, tar, tar.gz/bz2/xz) | angemeldete Entwickler auf **app.luibui.com** | eigener Bereich, gespeichert | 50 MB gepackt, 200 MB entpackt, 10.000 Dateien |
| Git-Repository verbinden | angemeldete Entwickler auf **app.luibui.com** | eigener Bereich, Scan bei jedem Push/Tag | wie Upload |
| **Schnellscan** per öffentlicher Git-URL oder einer einzelnen Datei | alle, ohne Anmeldung, auf luibui.com | nur Bericht (eingeschränkter Umfang, **ohne Gewähr**), nichts gespeichert, 7 Tage abrufbar | 3 Scans pro Tag und IP, Datei bis 2 MB |
| `luibui scan` lokal | alle | läuft offline auf dem eigenen Rechner, kein Upload | – |
| `luibui scan --remote` / CI-Action | Entwickler mit API-Token | in das verknüpfte Projekt | wie Upload |

**Zwei Scan-Arten**

| | Schnellscan (luibui.com) | Intensivscan (app.luibui.com) |
|---|---|---|
| Anmeldung | nein | ja, kostenlos |
| Eingabe | öffentliche Git-URL oder eine Datei bis 2 MB | alle Eingabearten |
| Prüfungen | Ebene A (Dateien), B (versteckte Inhalte und Anweisungsmuster, nur Regeln), Secrets, D (Abhängigkeiten, bei Git) | alle Ebenen A–H, Code-Analyse (Opengrep, Bandit, Cisco-Scanner), MCP, DSGVO-Abgleich, Korrelation, LLM-Prüfer, ClamAV, ab Sprint 6 Sandbox |
| Dauer | unter 30 Sekunden | bis 5 Minuten |
| Ergebnis | vorläufige Ampel mit Hinweis **„Schnellscan – eingeschränkter Umfang, ohne Gewähr“** | vollständiger Bericht mit Verlauf, Befund-Status, Dateiansicht |
| Speicherung | nichts, Bericht 7 Tage per Link | im eigenen Bereich |
| Download | **PDF und CSV** | **PDF und CSV**, dazu JSON und SARIF |

Der Schnellscan endet immer mit dem Hinweis, dass nur ein Teil geprüft wurde, und dem Button „Kostenlos registrieren für den Intensivscan“. Eine grüne Ampel im Schnellscan heißt ausdrücklich nicht, dass das Paket unbedenklich ist.

**Bericht als Download**
- **PDF:** Deckblatt mit Ampeln, Note, Prüfumfang, Scan-Art und Datum; Befunde nach Schwere mit Beleg, Erklärung und Fix; Haftungsausschluss auf jeder Seite; beim Schnellscan zusätzlich der Hinweis „ohne Gewähr“ im Kopf jeder Seite.
- **CSV:** eine Zeile pro Befund mit `scan_id, scan_art, datum, paket, rule_id, ebene, schwere, achse, titel, datei, zeile, beleg, nachweisgrad, normbezug, fix, status`. UTF-8 mit BOM und Semikolon als Trennzeichen, damit Excel sie direkt öffnet.

**Die Engine ist ein eigenes Python-Paket (`luibui-scan`).** Server, Worker und CLI nutzen denselben Code. Entwickler können deshalb lokal und in CI genau das prüfen, was auch luibui prüft.

---

## 3. Der Entwicklerbereich: app.luibui.com

Jeder Entwickler bekommt nach der Anmeldung einen eigenen, privaten Bereich. Dort liegen seine Projekte, Dateien, Prüfberichte und deren Verlauf. Niemand außer ihm (und später seinem Team) sieht etwas davon, bis er ein Paket veröffentlicht.

**Aufteilung der Domains**

| Domain | Inhalt | Anmeldung |
|---|---|---|
| `luibui.com` | **Marketingseite und Einstieg:** Startseite mit **Schnellscan**, „So prüfen wir“, Prüfkatalog, Doku, Spenden, Buttons **Anmelden** und **Kostenlos registrieren**; ab Sprint 4 Register und öffentliche Berichte | nein |
| `app.luibui.com` | Entwicklerbereich: Projekte, Dateien, Auswertungen, Einstellungen. Die Anmelde- und Registrierungsseiten liegen technisch hier (`/anmelden`, `/registrieren`), sehen aber aus wie die Marketingseite. So bleibt das Login-Cookie auf app.luibui.com beschränkt | ja |
| `api.luibui.com` | API für CLI, CI und die beiden Oberflächen | Token/Session |

**Bereiche in app.luibui.com**

| Bereich | Inhalt | Sprint |
|---|---|---|
| **Übersicht** | alle Projekte mit aktueller Gesamtampel, Note, letzter Prüfung; offene K/H-Befunde oben | 2 |
| **Projekt anlegen** | Name, Typ (Skill, MCP-Server, Plugin, Einzeldatei), Quelle: einzelne Datei, mehrere Dateien, Ordner, ZIP, Text einfügen oder Git-Repository | 2 |
| **Schnell eine Datei prüfen** | Drag & Drop direkt auf der Übersicht, ohne Projekt anzulegen; landet im automatischen Projekt „Einzelprüfungen“ | 2 |
| **Projekt → Prüfungen** | alle Scans eines Projekts als Liste mit Ampel, Note, Version/Commit, Datum | 2 |
| **Projekt → Bericht** | zwei Ampeln, Note, Befunde nach Schwere, Belege, Fix und Fix-Prompt, Download CSV, JSON, SARIF (ab Sprint 2) und PDF (ab Sprint 3) | 2–3 |
| **Projekt → Dateien** | Dateibaum der geprüften Version, Dateiansicht mit Befunden direkt an der Zeile markiert | 4 |
| **Projekt → Verlauf** | Note und Befundzahl über die Zeit, Vergleich zweier Prüfungen: neu, behoben, unverändert | 3 |
| **Befund-Status** | pro Befund: offen, behoben, akzeptiert (mit Begründung), bestritten (Einspruch) | 3 |
| **Projekt → Veröffentlichen** | Paket aus einer Prüfung ins Register stellen, Versionen verwalten | 4 |
| **Projekt → Automatisierung** | Git-Webhook (Scan bei Push/Tag), CI-Snippet, API-Token für dieses Projekt | 5 |
| **Benachrichtigungen** | Mail bei neuen Befunden durch die nächtliche Neuprüfung, bei Einspruchs-Entscheidungen, bei Meldungen | 5 |
| **Konto** | Profil, 2FA, API-Tokens, Speicherverbrauch, Datenexport, Konto löschen | 2 |
| **Organisationen** | Team-Bereich mit Rollen (Owner, Maintainer, Leser) | nach Sprint 7 |

**Speicherung der Dateien**

- Dateien eines Projekts werden **verschlüsselt** gespeichert (pro Projekt ein eigener Schlüssel, der mit einem Hauptschlüssel aus der Umgebung verschlüsselt ist).
- **Nur der Eigentümer** kann sie sehen oder herunterladen. Admin-Zugriff nur im Missbrauchsfall, und jeder Zugriff wird protokolliert.
- **Kontingent:** 500 MB pro Konto, die letzten 10 Versionen pro Projekt. Ältere Versionen werden gelöscht, ihre Berichte bleiben.
- **Option „Dateien nach der Prüfung löschen“** pro Projekt. Dann bleiben nur Berichte und Hashes, wie beim Schnellscan.
- **Git-Projekte** speichern keine Kopie, sondern den Commit. Für die Dateiansicht wird der Commit bei Bedarf neu geholt.
- **Schadsoftware wird nie gespeichert.** Trifft ein Befund aus der Sperrliste der Ebene A (bekannte Schadsoftware), werden die Dateien sofort gelöscht, nur der Hash bleibt.
- **Dateien werden nie ausgeführt oder als Webseite ausgeliefert.** Die Dateiansicht zeigt escaped Text, Downloads gehen als `application/octet-stream` mit `Content-Disposition: attachment`.

---

## 4. Die Prüfung

Den vollständigen Katalog mit rund 80 Prüfungen enthält `luibui_Pruefkatalog.md`. Hier nur die Pipeline:

| # | Schritt | Inhalt | Sprint |
|---|---|---|---|
| 1 | **Annahme** | Einzeldatei, Dateiauswahl, Ordner, Text, ZIP/tar oder Git-Clone (flach, ohne Hooks, ohne Submodule); Dateinamen und Ordnerpfade werden wie ZIP-Einträge geprüft (kein `..`, keine absoluten Pfade); Größenlimits. Paketformate im Paket (`.whl`, `.dxt`, `.vsix` …) werden eine Ebene tief mitgeprüft, andere Archive bleiben gepackt | 1 |
| 2 | **Sicher entpacken** | Zip-Bomben, `../`-Pfade, Symlinks, verschlüsselte Archive erkennen und abbrechen | 1 |
| 3 | **Inventar** | Dateiliste, echte Dateitypen (Magic Bytes), SHA-256, Sprachen, Pakettyp (Skill, MCP-Server, Plugin) | 1 |
| 4 | **Ebene A – Dateien** | Autostart-Dateien, Install-Skripte, Binaries, versteckte Dateien, Paketquellen | 1 |
| 5 | **Ebene B – Inhalte** | unsichtbare Unicode-Zeichen, Bidi, Homoglyphen, versteckter Text, kodierte Blöcke, Injection-Muster (ATR-Regeln) | 1 |
| 6 | **Geheimnisse** | gitleaks, Werte im Bericht maskiert | 1 |
| 7 | **Ebene D – Abhängigkeiten** | OSV-Scanner offline: CVEs und bekannte Schadpakete, Typosquatting, fehlende Lockfiles | 1 |
| 8 | **Ebene C – Code** | Opengrep mit eigenen Regeln, Bandit, Cisco skill-scanner (Datenfluss, YARA) | 2 |
| 9 | **Ebene E – MCP** | Cisco mcp-scanner offline, Tool-Beschreibungen, Auth, Transport | 2 |
| 10 | **DSGVO und Rechte** | Endpunkte und Rechte im Code gegen Manifest, Länderzuordnung | 2 |
| 11 | **Korrelation** | Anweisung im Markdown verweist auf eine Datei mit Befund → Befund wird hochgestuft | 2 |
| 12 | **LLM-Prüfer** | semantische Prüfung von Anweisungen und Tool-Beschreibungen, „Beschreibung ≠ Verhalten“, über mittwald AI Hosting | 3 |
| 13 | **ClamAV** | klassische Signaturen (braucht ca. 1,2 GB RAM, deshalb abhängig vom Server) | 4 |
| 14 | **Bewertung und Bericht** | Ampeln, Note, Belege, Fix-Prompts; HTML, CSV, JSON, SARIF, PDF | 1–3 |
| 15 | **Ablegen oder löschen** | Scratch immer löschen. Projekt-Dateien verschlüsselt im Entwicklerbereich ablegen (außer Option „nach Prüfung löschen“, Schnellscan oder Schadsoftware) | 1–2 |
| 16 | **Sandbox** | Ausführung ohne Netz, strace, Köder-Zugangsdaten, vorgedrehte Uhr | 6 (eigener Server) |

**Warum Schritt 11 wichtig ist:** Die gefährlichsten Skills verteilen den Angriff auf Anweisung und Skript. Einzelne Scanner sehen jeweils nur eine Hälfte (MalSkillBench 2026). luibui führt die Befunde beider Hälften zusammen.

---

## 5. Bewertung

**Befund-Schwere:** K kritisch · H hoch · M mittel · N niedrig · I Info

**Prüfumfang:** Nicht jede Prüfung ist bei jeder Eingabe möglich. Der Bericht zeigt immer, welcher Umfang geprüft wurde.

| Umfang | Was geprüft wird | Was nicht geht |
|---|---|---|
| **Paket** (Ordner, ZIP, Git mit `luibui.json`) | alle Ebenen A–H | – |
| **Dateiauswahl ohne Manifest** | A, B, C, E, Secrets, Abhängigkeiten, wenn Lockfile dabei ist, Korrelation zwischen den gewählten Dateien | Abgleich mit Manifest (G1, G3–G5) |
| **Einzeldatei oder Text** | A (Dateityp, Schadsoftware), B (versteckte Inhalte, Anweisungen), C (Code), Secrets, E (bei Tool-Beschreibungen) | Abhängigkeiten, Korrelation, Manifest-Abgleich |

Bei Einzeldatei, Text oder Auswahl ohne Manifest steht die DSGVO-Achse auf **„nicht bewertet“** (grau). Nur gefundene Endpunkte in Drittländern führen dort zu Gelb oder Rot. Die Gesamtampel folgt dann der Sicherheitsachse, der Bericht trägt den Hinweis „Einzeldatei-Prüfung“. Veröffentlichen im Register geht nur als Paket mit Manifest.

| | Grün | Gelb | Rot | Gesperrt |
|---|---|---|---|---|
| **Sicherheit** | höchstens N/I | mindestens ein M | mindestens ein H | ein K aus der Sperrliste* |
| **DSGVO** | alles deklariert, Betrieb in der EU oder mit Angemessenheitsbeschluss | Angaben fehlen | Drittland ohne Grundlage, undeklarierte Endpunkte | – |
| **Gesamt** | die schlechtere der beiden Achsen | | | |

\* Sperrliste: bekannte Schadsoftware, Autostart-Dateien mit Befehlen, unsichtbare Unicode-Anweisungen, Anweisungs-Übernahme, Geheimhaltung vor dem Nutzer, Datenabfluss, Zugriff auf Zugangsdaten, Persistenz, Tool Poisoning, `curl | bash`, verschleierter Code, Zeitbomben, Schadmuster, echte Secrets, bekannte Schadpakete, Code-Ausführung beim Laden eines Modells (Pickle, Chat-Vorlage). Gesperrte Pakete können nicht veröffentlicht werden.

**Note 0–100:** 100 minus Abzüge (K 40, H 15, M 5, N 1), mindestens 0. Die Note zeigt Fortschritt, die Ampel entscheidet.

**Freigabe-Stufen:**

| Freigabe | Gesamtampel |
|---|---|
| freigegeben | Grün |
| Prüfung nötig | Gelb oder Rot |
| blockiert | gesperrt |

**Ein Befund enthält:**

| Feld | Inhalt |
|---|---|
| `rule_id` | z. B. `LB-B01-unicode-tags`, `ATR-2026-00258`, `gitleaks:aws-key` |
| `ebene`, `schwere`, `achse` | A–H · K–I · sicherheit/dsgvo |
| `titel`, `erklaerung` | in einfachem Deutsch, was das Risiko ist |
| `datei`, `zeile`, `beleg` | max. 5 Zeilen Ausschnitt, Secrets maskiert |
| `nachweisgrad` | statisch erkannt · per LLM bewertet · in Sandbox beobachtet · Selbstauskunft |
| `normbezug` | OWASP Agentic (ASI01–10), OWASP LLM Top 10, DSGVO-Artikel |
| `fix` | konkrete Behebung |
| `fix_prompt` | fertiger Prompt für Claude Code oder andere Coding-Agents |

---

## 6. Sichtbarkeit und Fairness

| Situation | Wer sieht den Bericht |
|---|---|
| Projekt im Entwicklerbereich, nicht veröffentlicht | nur ich (Standard); Teilen per Link mit Zufalls-Token möglich |
| Schnellscan eines fremden Repositorys | nur ich, 7 Tage per Link; Details zu K/H-Befunden erst nach Bestätigung, dass ich sie verantwortungsvoll melde |
| Veröffentlichtes Paket | alle, mit Ampeln, Rechte-Label und Befundliste |
| Neuer K/H-Befund in veröffentlichtem Paket | Autor sofort mit vollem Bericht; öffentlich 14 Tage nur „Sicherheitsbefund offen“, danach Details |

- **Einspruch:** Autoren können einen Befund als Fehlalarm anfechten, mit Begründung. Nach Prüfung wird er als „vom Autor bestritten“ oder „Fehlalarm, Regel angepasst“ markiert.
- **Formulierung:** sachlich, am Befund, nie wertend über die Person. „Liest ~/.aws/credentials“ statt „gefährliches Paket“.
- **Haftung:** Die Prüfung ist automatisch und ohne Gewähr. Das steht an jedem Bericht und in den Nutzungsbedingungen.

---

## 7. Register (ab Sprint 4)

Ein Paket kann aus einem Bericht heraus veröffentlicht werden, wenn es nicht gesperrt ist.

- **Paketformat:** `luibui.json` (Manifest mit Rechten, Endpunkten, Datenkategorien) + `SKILL.md` / Tools / MCP-Server
- **Paketseite:** zwei Ampeln, Note, **Rechte-Label** (Netzwerk · Dateien · Shell · Zugangsdaten · Drittland), Befundliste, README, Versionen
- **Installieren:** `luibui install org/paket --target claude|chatgpt|gemini|mistral|openwebui|mcp`
- **Updates:** Jede neue Version wird geprüft. Bekommt sie neue Rechte oder Endpunkte, bekommen Nutzer der Vorversion einen Hinweis (Diff-Prüfung).
- **Nächtliche Neuprüfung:** mit aktuellen Regeln und CVE-Daten; `luibui audit` zeigt, welche installierten Pakete betroffen sind.
- **Herkunft:** Veröffentlichung per signiertem Git-Tag möglich; Paketinhalt wird mit dem Repository abgeglichen.
- **Badge:** `![luibui](https://luibui.com/badge/org/paket.svg)` für die README.

---

## 8. Architektur auf mittwald

```
     luibui.com   app.luibui.com            api.luibui.com
          │              │                         │
          └──── web ─────┘                        api ──── Volume luibui-projects
         (ein Next.js, Routing nach Host)          │       (Projekt-Dateien, verschlüsselt)
                         └────────────┬────────────┘
                                      │  Jobs in Postgres (SKIP LOCKED)
                               ┌──────┴──────┐
                               │  postgres   │
                               └──────┬──────┘
                                      │
                               ┌──────┴──────┐     Volume luibui-scratch (tmp, wird geleert)
                               │   worker    │──── Volume luibui-rules  (Regeln, OSV-DB, ClamAV-DB)
                               │ luibui-scan │
                               └─────────────┘
```

| Container | Aufgabe | Technik | RAM-Limit (Start) |
|---|---|---|---|
| `web` | öffentliche Seite (luibui.com) und Entwicklerbereich (app.luibui.com) in einer Next.js-App, getrennt per Host-Routing | Next.js 15, TS, Tailwind | 384 MB |
| `api` | Auth, Annahme, Git-Clone, Projekte, verschlüsselte Dateiablage, Berichte, Register | FastAPI, SQLAlchemy 2, Alembic | 512 MB |
| `worker` | Pipeline, eine Prüfung gleichzeitig, Timeout 5 min | Python 3.12 + gitleaks, osv-scanner, opengrep, bandit, skill-scanner, mcp-scanner (+ ClamAV ab Sprint 4) | 1,5 GB (2,5 GB mit ClamAV) |
| `postgres` | Nutzer, Scans, Befunde, Pakete, Jobs, Audit-Log | PostgreSQL 17 | 768 MB |

**Monorepo**

```
luibui/
├── CLAUDE.md
├── apps/web          Next.js: luibui.com (öffentlich) + app.luibui.com (Entwicklerbereich)
├── apps/api          FastAPI
├── apps/worker       Job-Loop, ruft packages/engine
├── packages/engine   luibui-scan: Pipeline, Analyzer, Bewertung, Bericht (pip-installierbar)
├── packages/cli      luibui: scan, init, lint, publish, install, audit
├── rules/            eigene Regeln (YAML/YARA/Opengrep) + Testfälle, MIT-lizenziert
├── corpus/           Testpakete: gutartig und entschärft-bösartig
├── spec/             luibui.json-Schema, Befund- und Bericht-Schema
├── infra/            docker-compose.yml, Cronjobs
└── docs/             Konzept, Sprintplanung, Prüfkatalog, ADRs
```

**Die Prüfstelle schützt sich selbst.** Jeder Upload ist potenziell feindlich:
- Code aus Uploads wird **nie ausgeführt** (bis zur Sandbox auf eigenem Server).
- Entpacken mit harten Limits, keine Symlinks, keine absoluten Pfade.
- Git: `--depth 1`, keine Submodule, `core.hooksPath=/dev/null`, `protocol.file.allow=never`, Größenlimit.
- Scanner laufen als unprivilegierter Nutzer, mit Timeout und ohne Netzwerkzugriff (Offline-Datenbanken, nächtlich per Cronjob aktualisiert).
- Der Bericht rendert Belege nur als maskierten Text, nie als HTML oder Markdown. Sonst würde ein Beleg selbst zum Angriff.
- Scratch-Verzeichnis pro Job, wird nach dem Job gelöscht, auch bei Fehlern.
- Session-Cookie gilt nur für `app.luibui.com` (host-only, `Secure`, `HttpOnly`, `SameSite=Lax`). Die öffentliche Seite hat keinen Zugriff auf angemeldete Sitzungen. app.luibui.com erreicht die API über den eigenen Pfad `/api/*` (interne Weiterleitung an den api-Container); `api.luibui.com` ist nur für CLI, CI und Webhooks und akzeptiert nur Tokens.
- Gespeicherte Projekt-Dateien: verschlüsselt, Zugriff nur über die API mit Eigentümer-Prüfung, Auslieferung nur als Download oder escaped Text.

**Keine US-Dienste:** kein VirusTotal-Upload, keine Google Fonts, kein Analytics, keine externen CDNs. Das LLM läuft über mittwald AI Hosting (OpenAI-kompatibel, `https://llm.aihosting.mittwald.de/v1`).

**websecureaudit:** Für Remote-MCP-URLs prüft websecureaudit den laufenden Endpunkt (TLS, Header, Erreichbarkeit) über eine interne API. Der Bericht übernimmt das Bewertungsmodell von websecureaudit (Freigabe, Schwere, Nachweisgrad, Fix-Prompts).

---

## 9. Werkzeuge

| Werkzeug | Lizenz | Einsatz |
|---|---|---|
| Cisco skill-scanner | Apache-2.0 | Skills: statisch, YARA, Datenfluss; LLM-Teil über mittwald statt Cloud |
| Cisco mcp-scanner | Apache-2.0 | MCP-Server-Code und Tool-Beschreibungen, nur Offline-Analyzer |
| ATR – Agent Threat Rules | MIT | 818 Regeln für Injection u. a., mit Testfällen |
| gitleaks | MIT | Secrets |
| OSV-Scanner + OSV-Offline-DB | Apache-2.0 | CVEs und Schadpakete (`MAL-…`) |
| Opengrep | LGPL-2.1 | Code-Muster mit **eigenen** Regeln (Regeln der Semgrep-Registry sind lizenzrechtlich für einen Dienst nicht nutzbar) |
| Bandit | Apache-2.0 | Python |
| ClamAV | GPL-2.0 | Signaturen, ab Sprint 4 |
| YARA | BSD-3 | eigene Regeln |

Lizenzen und aktuellen Stand jedes Werkzeugs in Sprint 0 verifizieren (`docs/scanner-tools.md`).

---

## 10. Recht

**DSGVO:** Einziger Subprozessor ist mittwald (AVV im AV Manager). Projekt-Dateien und Berichte im Entwicklerbereich bleiben, bis der Entwickler sie löscht (Kontingent 500 MB, letzte 10 Versionen). Konten ohne Anmeldung seit 24 Monaten werden nach Vorwarnung gelöscht. Schnellscans: keine Dateien, Bericht 7 Tage. Audit-Log nur Metadaten. Export und Löschung pro Konto. Für Dateien mit personenbezogenen Daten Dritter ist luibui Auftragsverarbeiter, deshalb einen AVV-Text für Entwickler bereitstellen.

**DSA:** luibui ist Hosting-Dienst. Es braucht ein Meldeformular, eine Kontaktstelle, einen Takedown-Prozess und Moderationsregeln in den Nutzungsbedingungen.

**Prüfberichte:** Sie werden nur für Pakete veröffentlicht, die der Autor selbst veröffentlicht hat. Die Befunde sind sachlich und belegbar, mit Einspruchsverfahren. Dazu kommt ein Haftungsausschluss für die automatische Prüfung. **Fachanwalt IT-Recht** für Nutzungsbedingungen, Haftungsausschluss, Disclosure- und Einspruchsprozess.

**Urheberrecht an Uploads:** Dateien bleiben Eigentum des Entwicklers. luibui speichert sie nur für ihn und nur zur Prüfung, Anzeige und Veröffentlichung auf seinen Wunsch. Veröffentlicht werden nur Pakete mit SPDX-Lizenz.

**Schadsoftware in Uploads:** Sie wird nicht aufbewahrt, nur ihr Hash kommt auf eine Blockliste.

---

## 11. Finanzierung

Kostenlos, Spenden für Server und Domains, Transparenzbericht.

| Stufe | Kosten netto/Monat |
|---|---|
| Start auf geteiltem Server | ca. 0–20 € zusätzlich |
| LLM-Prüfer (AI Hosting Starter/Pro) | 9–39 € |
| Eigener vServer für Worker und ClamAV (voraussichtlich vor Launch nötig) | ca. 40–80 € |
| Sandbox-Server (Sprint 6) | ca. 40–80 € |

---

## 12. Risiken

| Risiko | Gegenmaßnahme |
|---|---|
| Fehlalarme schaden Autoren | Testkorpus mit Fehlalarm-Quote als Abnahmekriterium, Einspruch, Meta-Analyse, Belege pro Befund |
| Unentdeckte Angriffe (falsche Sicherheit) | „geprüft am, keine bekannten Befunde“, Kombination Regeln + LLM + später Sandbox, nächtliche Neuprüfung |
| Prüfstelle wird selbst angegriffen | nie ausführen, Limits, unprivilegiert, offline, Belege nur als Text |
| Missbrauch als Malware-Ablage | Schadsoftware sofort löschen, Login für Uploads, Kontingent, Rate-Limits, Dateien nie öffentlich ausliefern |
| Gespeicherter Code der Entwickler wird Angriffsziel | Verschlüsselung pro Projekt, Eigentümer-Prüfung in jeder Abfrage (Tests), Admin-Zugriff protokolliert, 2FA empfohlen |
| Geteilter Server zu klein | eine Prüfung gleichzeitig, Kapazitätsbericht, eigener vServer als Trigger |
| Werkzeuge ändern Lizenz oder Format | Adapter pro Werkzeug, Versionen pinnen, eigene Regeln als Kern |
| Solo-Betrieb | Scope kürzen statt Termin schieben, offene Regeln für Mitwirkende |

---

## 13. Entscheidungen

- [x] luibui = Prüfstelle zuerst, Register danach
- [x] AGPL-3.0 für die Plattform
- [ ] Vorschlag: MIT für `rules/` und die `luibui-scan`-Engine, damit Regeln und Engine auch in andere Tools und CI-Pipelines einfließen können
- [x] Zwei Achsen: Sicherheit und DSGVO, Gesamt = schlechtere
- [x] Eigener Entwicklerbereich auf app.luibui.com mit Projekten, Dateien und Auswertungen
- [x] Dateien verschlüsselt gespeichert, nur für den Eigentümer; Option „nach Prüfung löschen“; Schnellscan ohne Speicherung
- [ ] Kontingent 500 MB / 10 Versionen pro Projekt (Vorschlag)
- [x] luibui.com ist die Marketingseite mit Anmelden/Registrieren; der Entwicklerbereich liegt auf app.luibui.com
- [x] Im Entwicklerbereich lassen sich auch einzelne Dateien, Dateiauswahlen, Ordner und eingefügter Text prüfen, nicht nur ZIP
- [x] Schnellscan ohne Anmeldung auf luibui.com, eingeschränkter Umfang, ausdrücklich ohne Gewähr; Intensivscan im Entwicklerbereich
- [x] Beide Scan-Arten liefern den Bericht als PDF und CSV zum Download
- [ ] Eigener vServer für den Worker: Entscheidung nach Kapazitätsbericht Sprint 1 (bis 16.10.)
- [ ] Anwalt benennen (bis 09.10.)
- [ ] AI-Hosting-Tarif für LLM-Prüfer (bis 30.10.)
