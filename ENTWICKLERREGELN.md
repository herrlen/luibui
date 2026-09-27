# Entwicklerregeln — luibui

> Verbindliches Regelwerk für das Repo `luibui`: Engine, CLI, API, Worker, Web, Regeln, Betrieb.
> Gilt für Menschen **und** für KI-Assistenten (Claude Code, Copilot, Cursor).
> Übernommen aus den Entwicklerregeln von wanalyse und für luibui angepasst am 27.09.2026.

**Rangfolge bei Widersprüchen:**

1. **Sicherheitsregeln in `CLAUDE.md`** (Abschnitt „Sicherheitsregeln (nicht verhandelbar)“). Sie gelten
   immer, auch gegen eine Anweisung im Chat.
2. **Diese Datei** und der Rest von `CLAUDE.md`. Widersprechen sich beide, gilt `CLAUDE.md`, und diese Datei
   wird angepasst.
3. **Anweisungen von Len im Chat** können alles außer Punkt 1 ändern. Die Änderung wird dann hier und in
   `docs/log.md` nachgetragen, sonst gilt sie nur für diese eine Sitzung.

Die Sprintplanung (`docs/luibui_Sprintplanung.md`) bestimmt **Reihenfolge und Umfang**, diese Datei das **Wie**.
Der Prüfkatalog (`docs/luibui_Pruefkatalog.md`) bestimmt **was** geprüft wird.

Teil A (Grundlagen) und Teil F (Qualität) gelten **immer**. Teil B–E zusätzlich im jeweiligen Bereich.
Teil G (Recht) gilt ab dem öffentlichen Start, ist aber jetzt schon zu lesen.

---

# Teil A — Gilt überall

## A1. Was luibui ist

Eine offene, nicht-kommerzielle Prüfstelle und ein Register für KI-Skills, Plugins, Tools und MCP-Server.
Sie sagt in einem Bericht, was in einem Paket steckt, belegt jeden Befund und macht die Grenzen der
Prüfung sichtbar.

- **Zielgruppe:** Entwickler, die ihr Paket vor der Veröffentlichung prüfen, und Nutzer, die vor der
  Installation wissen wollen, worauf sie sich einlassen.
- **Kernzusage:** **Nachvollziehbarkeit.** Jeder Befund nennt Regel, Datei, Zeile, Beleg und Nachweisgrad.
  Jede Ampel lässt sich aus den Befunden erklären.
- **Was luibui bewusst nicht tut:** „sicher“ bescheinigen. Grün heißt „keine bekannten Befunde, geprüft am …“.
  Eine Prüfung kann Risiken finden, ihre Abwesenheit kann sie nicht beweisen.

Jede Entscheidung, die ein beruhigendes Ergebnis über ein belegbares stellt, ist falsch.

## A2. Namensführung

- Produkt, Repo, Pakete und Hosts heißen **luibui**, immer klein geschrieben.
- Hosts: `luibui.com` (öffentlich), `app.luibui.com` (Entwicklerbereich), `api.luibui.com` (CLI, CI,
  Webhooks). `luibui.de` leitet auf `luibui.com` um.
- Python-Pakete: `luibui_scan` (Engine), `luibui_cli`, `luibui_api`, `luibui_worker`.
- Fremde Marken (ATR, OSV, gitleaks, Anthropic, …) nur sachlich nennen, nie als Gütesiegel.

## A3. Sprache und Begriffe

- Oberfläche, Befundtexte, Doku und Rechtstexte **Deutsch**, klar, sachlich, ohne Alarmismus. Code,
  Bezeichner, Kommentare und Commit-Nachrichten **Englisch**.
- Buttons benennen die Handlung: „Paket prüfen“, nicht „Absenden“.
- **Ein Wort behält seine Bedeutung durch den ganzen Ablauf.**
- Keine Entschuldigungen in Fehlermeldungen, keine Ausrufezeichen, keine Emojis in der Oberfläche.
- Leere Zustände fordern zum Handeln auf und sind keine Sackgasse.

| Begriff | Bedeutung | Nicht verwenden |
|---|---|---|
| **Befund** | ein Treffer einer Prüfung, mit Regel-ID und Beleg | „Fehler“, „Warnung“, „Problem“ |
| **Prüfung** / **Scan** | ein Durchlauf über ein Paket | „Test“, „Audit“ |
| **Schnellscan** | ohne Konto, eingeschränkt, **ohne Gewähr** | „Gratis-Scan“ |
| **Intensivscan** | im Entwicklerbereich, alle Prüfungen | „Vollprüfung“ |
| **Grün / Gelb / Rot / Gesperrt** | die Ampel nach Konzept §5 | „sicher“, „unsicher“, „gefährlich“ |
| **Freigabe** | freigegeben / Prüfung nötig / blockiert | „zertifiziert“, „verifiziert“ |
| **Prüfumfang** | Paket, Dateiauswahl ohne Manifest, Einzeldatei | „Scope“ |
| **Nachweisgrad** | statisch erkannt, per LLM bewertet, … | „Konfidenz“ |
| **Sperrliste** | Prüfungen, deren K-Befunde sperren | „Blacklist“ |
| **Paket** | was geprüft wird | „Plugin“ als Oberbegriff |
| **Projekt** / **Version** | Ablage im Entwicklerbereich | „Repo“ |

## A4. Produktregeln — nicht verhandelbar

Diese Liste ist **kein vergessenes Backlog**. Assistenten ergänzen sie nicht und weichen sie nicht auf.

- ❌ **Nie „sicher“.** Grün heißt „Keine bekannten Befunde, geprüft am …“, in jeder Ausgabe (Web, PDF, CLI,
  API, Badge).
- ❌ **Kein Grün bei unvollständiger Prüfung.** Ist ein Analyzer fehlgeschlagen, keiner gelaufen oder eine
  vorgesehene Prüfung noch nicht eingebaut (`scan.ERWARTET`), ist das Ergebnis höchstens Gelb.
- ❌ **Kein Befund ohne Herkunft.** Jeder Befund trägt `rule_id`, `nachweisgrad` und, wo es eine Stelle gibt,
  `datei`, `zeile` und `beleg`.
- ❌ **Ein Sprachmodell allein führt nie zu Grün und sperrt nie.** Es kann nur Befunde hinzufügen (B18, B19).
- ❌ **Fremde Regeln allein sperren nie.** ATR-Treffer werden höchstens H; sperren dürfen nur eigene, kuratierte
  Regeln und die ausdrücklich gelisteten externen Quellen (`gitleaks:`, `osv:MAL-`).
- ❌ **Schnellscan immer mit „ohne Gewähr“**, in Web, PDF und CSV (Spalte `scan_art`).
- ❌ **Die Ampel kommt nie aus Paketdaten.** Kein Manifest, keine Datei im Paket kann die Bewertung setzen.
  Bewertung steht ausschließlich in `packages/engine/luibui_scan/scoring.py`.
- ❌ **Keine erfundenen Befunde, Zahlen oder Beispiele in Produktionscode.** Testpakete leben in `corpus/`
  und nur entschärft (CLAUDE.md Regel 8).
- ❌ **Keine US-Dienste** für Nutzerdaten: kein VirusTotal, keine Google Fonts, kein Analytics, keine
  externen CDNs. Ausnahme mit Freigabe: der Download öffentlicher Datenbanken (OSV, freigegeben 27.09.2026).

Weiß luibui etwas nicht, steht das im Bericht (`nicht_geprueft`, `hinweise`). Kein stilles Weglassen.

## A5. Design-Tokens

Farben stehen **nie** als Literal im Komponentencode, nur über Tokens im Tailwind-Theme
(`apps/web/app/globals.css`). Die Werte stammen aus den Design-Referenzen in `docs/design/`.

| Token | Hex | Verwendung |
|---|---|---|
| `--color-ink` | `#15171C` | Fließtext, Überschriften |
| `--color-ink-2` | `#3F434C` | Zweittext |
| `--color-muted` | `#5A5F6A` | Hinweise, Metadaten |
| `--color-grund` | `#F5F3EC` | Seitenhintergrund |
| `--color-surface` | `#FFFFFF` | Karten, Tabellen |
| `--color-linie` | `#E2DED3` | Trennlinien, Rahmen |
| `--color-petrol` | `#0E5E5B` | Primärfarbe, Buttons, Links |
| `--color-gruen` / `-bg` | `#17613C` / `#E3F1E8` | Ampel Grün |
| `--color-gelb` / `-bg` | `#7A5200` / `#FBF0D5` | Ampel Gelb |
| `--color-rot` / `-bg` | `#A3261B` / `#FBE4E1` | Ampel Rot |
| `--color-gesperrt` | `#5C1A13` | Ampel Gesperrt (weiße Schrift) |

**Gerechnete Kontraste (WCAG 2.1):**

| Kombination | Ratio | Bewertung |
|---|---|---|
| `ink` auf `grund` / `surface` | 16,1 / 17,9 : 1 | AAA |
| `muted` auf `grund` | 5,8 : 1 | AA |
| `petrol` auf `grund` / Weiß auf `petrol` | 6,8 / 7,6 : 1 | AA / AAA |
| `gruen` auf `gruen-bg`, `gelb` auf `gelb-bg`, `rot` auf `rot-bg` | 6,4 / 6,1 / 6,1 : 1 | AA |
| Weiß auf `gesperrt` | 13,0 : 1 | AAA |
| **`#9EA3AD` auf `grund`** | **2,3 : 1** | **unter AA, nie als Textfarbe** |
| `linie` auf `grund` | 1,2 : 1 | nur Linien, nie Text |

**Regeln daraus:**
1. Die Ampel wird **nie allein über Farbe** getragen: immer mit Wort („Gelb, Prüfung nötig“) und Symbol.
   Test mit Graustufen-Snapshot ab Sprint 2.
2. Ändert sich ein Hintergrund-Token, sind die Werte oben ungültig, bis sie neu gerechnet sind.
3. Prüfung per Skript in der CI, sobald die Oberfläche Tokens nutzt (Sprint 2).

## A6. Typografie

- **Display: Bricolage Grotesque**, nur Seitentitel und große Zahlen (Note).
- **UI/Text: IBM Plex Sans**, **Daten/Code: IBM Plex Mono** (Regel-IDs, Pfade, Belege, Hashes).
- Alle Schriften **selbst gehostet** als WOFF2 (`next/font/local`), `font-display: swap`, nur genutzte
  Schnitte, `latin` + `latin-ext`. Keine Google Fonts, auch nicht über CDN.

## A7. Layout und Darstellung von Paketinhalten

- Responsive bis 375 px. Tabellen scrollen in ihrem Container, nie das Dokument.
- Touch-Ziele mindestens 44 × 44 px. `prefers-reduced-motion` schaltet Animationen ab.
- **Paketinhalt ist feindlich** (CLAUDE.md Regel 6): Belege, Dateinamen, Titel und Beschreibungen aus
  Paketen werden **immer als escaped Text** ausgegeben. Nie `dangerouslySetInnerHTML`, nie Markdown-Rendering,
  nie automatische Verlinkung. Unsichtbare Zeichen werden sichtbar gemacht (`<U+202E>`).
- Im Terminal gilt dasselbe: `terminal_safe()` für alles aus dem Paket.

## A8. Befunde und Bewertung — die Kernregel

Jeder Befund hat die Felder aus `spec/finding.schema.json`; das Schema ist die Wahrheit, `models.py`
spiegelt es, ein Test hält beide gleich.

- **Regel-IDs:** eigene `LB-<Prüfkatalog-ID>-<kurzname>` (z. B. `LB-B01-unicode-tags`), externe mit Präfix
  (`ATR-…`, `gitleaks:…`, `osv:…`). Prüfkatalog-IDs zweistellig: `A01`–`H04`.
- **Jede eigene Regel hat mindestens einen positiven und einen negativen Testfall** (Regeln in `rules/`:
  mindestens zwei je Richtung, in der Regeldatei selbst).
- **Zitierte Beispiele** (Code, Anführungszeichen) werden herabgestuft, nicht verschwiegen.
- **Ein Befund je Datei und Regel**, mit Anzahl. Keine Flut aus Einzeltreffern.
- **Belege:** höchstens 5 Zeilen, Secrets maskiert (bei gitleaks vollständig geschwärzt).
- **Bericht** nach `spec/report.schema.json`; jeder erzeugte Bericht wird im Test gegen das Schema geprüft.

## A9. Eingänge — genau ein Weg

- **Paketinhalt kommt nur über `packages/engine/luibui_scan/intake/`** (CLAUDE.md Regel 2): Einzeldatei,
  Auswahl, Ordner, Text, ZIP (`safe_extract`), Git (`safe_git`). Kein Analyzer, keine Route liest an der
  Annahme vorbei.
- **Externe Werkzeuge nur über einen Adapter** in `luibui_scan/tools/`: feste argv, leere Umgebung, Timeout,
  JSON parsen, eigene Konfiguration statt der aus dem Paket. Nie direkt aus der Pipeline.
- **Projekt-Dateien nur über `apps/api/luibui_api/storage/`** (AES-256-GCM).

## A10. Datenmodell

- **PostgreSQL** ist die einzige Datenbank. Schema in `apps/api/luibui_api/models.py`, Migrationen mit Alembic,
  jede reversibel (Test: upgrade → check → downgrade → upgrade).
- **Jede Tabelle mit Nutzerdaten hat `owner_id`**; IDs sind UUIDs.
- Tokens und Sessions nur als Hash (Passwörter Argon2id, Tokens SHA-256), Projekt-Dateien nur verschlüsselt,
  TOTP-Geheimnisse mit `MASTER_KEY` verschlüsselt.
- Berichte sind reproduzierbar: Ein Bericht trägt `engine_version` und später `regeln_version`; ein alter
  Bericht wird nie mit neuen Regeln umgeschrieben, eine neue Prüfung ist ein neuer Bericht.

## A11. Datenschutz (Kurzfassung, Details in Teil G)

- Datensparsamkeit: kein Feld ohne Nutzungsszenario.
- **Keine personenbezogenen Daten und keine Paketinhalte in Logs.** Ausnahmen protokollieren nur Typ und
  Ort, nie die Nachricht (sie kann Paketinhalt enthalten). Das Audit-Log speichert nur Metadaten.
- Jeder Drittdienst steht in `docs/drittdienste.md` (Anbieter, Zweck, Daten, Standort, AV-Vertrag).
  **Kein Eintrag → keine Einbindung.**
- Keine Session-Recorder, kein Tracking.

> Operative Checkliste, keine Rechtsberatung.

## A12. Sicherheit

Die nicht verhandelbaren Regeln stehen in `CLAUDE.md`. Ergänzend:

- Keine Secrets im Repo. `.env` ignoriert, `.env.example` gepflegt, Secret-Scan der Historie in der CI.
- **Zugriff nur über `get_owned()`**: fremde und unbekannte IDs geben 404. Jede neue Route hat einen Test,
  dass Nutzer B nicht an Daten von Nutzer A kommt.
- **Schreibende Anfragen mit Cookie** brauchen die passende Herkunft (CSRF). `api.luibui.com` nimmt nur Tokens.
- **Jede URL von Nutzern** wird streng geprüft und aus Teilen neu gebaut (`canonical_url`), nie durchgereicht.
- **Rate-Limits** serverseitig; Client-IP nur aus vertrauenswürdigen Proxy-Headern.
- **Der prüfende Prozess hat kein Netz** (`LUIBUI_NETZ_ISOLIEREN=1`), scheitert geschlossen.
- **Fremde Regex** (ATR) laufen mit Timeout; ein Timeout macht die Prüfung unvollständig, nie „kein Treffer“.
- Neue Werkzeuge: gepinnte Version, Prüfsumme aus dem offiziellen Release.

## A13. Arbeitsweise für KI-Assistenten

1. **Prüfen, nicht annehmen.** Vor Änderungen den Ist-Zustand lesen. Werkzeugoptionen mit `--help` oder im
   Quellcode belegen (Beispiel: der Pfad der OSV-Datenbank stand anders in der Doku als im Code).
2. **Praxistest an echten Paketen**, bevor ein Analyzer als fertig gilt: mindestens die Vergleichs-Repos
   (`anthropics/skills`, `modelcontextprotocol/servers`, `modelcontextprotocol/python-sdk`). Jeder Fehlalarm wird
   behoben und als Negativtest aufgenommen.
3. **Kleine Schritte.** Eine Task-ID = ein Commit.
4. **Keine ungefragten Zusatzfunktionen**, nichts gegen A4.
5. **Neue Abhängigkeiten nur mit klarer Lizenz** (MIT, Apache-2.0, BSD); unklare Lizenz → fragen. Jede neue
   Abhängigkeit mit Begründung in `docs/log.md`.
6. **Keine erfundenen Werte**, auch nicht als Platzhalter.
7. **Unsicherheit benennen** statt raten. Offene Punkte in `docs/log.md` unter „Offen“.
8. Nichts löschen und nichts umformatieren, was nicht Teil der Aufgabe ist. **Löschen, Force-Push, Ausrollen
   und Änderungen an Konten nur auf Lens Wort.**
9. **Commits nennen ihre Dateien ausdrücklich**, kein `git add -A` (eine fremde Datei ist so schon einmal ins
   Repo geraten).
10. **Vor jedem Commit alle Prüfungen**, nicht nur die Tests (ruff check, ruff format, mypy, pytest).
11. **Nach jeder Arbeitseinheit:** `docs/log.md` (was, warum, offen) und das Protokoll nach
    `~/Desktop/Len/PROTOKOLL-REGELN.md`.

## A14. Git und Definition of Done

- Standardzweig `main`, immer ausrollbar. Commit-Nachricht: Task-ID vorn, Englisch, Imperativ:
  `S1-5: add file-layer analyzer`. Ohne Task-ID: `chore:`, `docs:`, `fix:`.
- Architekturentscheidungen bekommen einen ADR in `docs/adr/` (nummeriert, Datum, Alternativen).
- **Definition of Done:** die Checkliste in **F9**, dazu die DoD des Sprints aus der Sprintplanung.

---

# Teil B — Web (Next.js App Router, TypeScript, Tailwind) — ab Sprint 2

- TypeScript **strict**, kein `any`, kein `@ts-ignore` ohne `@ts-expect-error` mit Begründung.
- **Server Components sind Standard**, `"use client"` nur wo Interaktion es erzwingt.
- Host-Trennung per Middleware: `luibui.com` (öffentlich) und `app.luibui.com` (Entwicklerbereich). Die App
  spricht die API nur über `app.luibui.com/api/*`.
- Formatierung (Zahlen, Daten, Größen) nur über einen Helfer mit deutscher Locale (`Intl`).
- Geteilte Bausteine gibt es **genau einmal**: `Ampel` · `NoteBadge` · `BefundKarte` · `Beleg` (escaped,
  Monospace) · `FixPrompt` (kopierbar) · `Upload` · `EmptyState` · `Skeleton`.
- Jede Liste hat vier Zustände: laden, leer, teilweise, Fehler. Während einer Prüfung ist der Fortschritt sichtbar.
- Keine externen Ressourcen (Fonts, Skripte, Bilder) im Frontend.

---

# Teil C — Backend, API und Worker

- **Pfade:** heute `/api/…`. **Vor der ersten öffentlichen Nutzung durch CLI und CI** wird auf `/api/v1/…`
  umgestellt; danach Breaking Changes nur mit `v2`.
- JSON, Zeitangaben ISO 8601 UTC. Die Oberfläche rechnet in `Europe/Berlin` um, die API nie.
- **Fehlerformat:** `{"detail": {"code": "…", "text": "…"}}`. `code` ist maschinenlesbar und stabil, `text`
  deutsch und darf sich ändern. Clients werten nie `text` aus.
- Eingaben am Rand mit Pydantic validiert, auch Umgebungsvariablen beim Start und **jede Ausgabe eines
  Kindprozesses oder Werkzeugs**, bevor sie in die Datenbank geht.
- **Kontingente vor der teuren Operation prüfen** (500 MB, 10 Versionen, Upload-Größe vor dem Lesen).
- Langlaufendes (Prüfung, Klon, PDF) als Job mit Statusabfrage. Jobs sind idempotent; Scan-Jobs laufen
  einmal (`max_attempts = 1`).
- **Worker:** Elternprozess (Datenbank, OSV-Download) und Kindprozess (Paketinhalt, ohne Netz, ohne
  Zugangsdaten) bleiben getrennt. Scratch wird im `finally` gelöscht.

---

# Teil D — Engine, Analyzer und Regeln

- Jeder Analyzer implementiert `analyze(ctx) -> list[Finding]`, ist in der Registry eingetragen und hat
  `scopes`/`scan_arts`, die dem Prüfkatalog entsprechen.
- **Ein Analyzer, der nicht laufen kann** (Werkzeug fehlt, Datenbank fehlt, Timeout), **wirft eine Ausnahme**.
  Die Pipeline meldet ihn als fehlgeschlagen; das Ergebnis wird nie grün.
- **Regeln als Daten** (`rules/b-muster/*.yaml`, `rules/data/*.txt`), nicht als `if`-Kaskaden. Eine neue Regel
  ist eine Datei mit Testfällen, kein Code-Risiko.
- **Fremde Regeln übernehmen** nur per Skript (`scripts/vendor_atr.py`): fester Stand, eigene Testfälle bestanden,
  **kein Treffer im gutartigen Vergleichsbestand**, Ausschlüsse mit Grund in `QUELLE.md`.
- Nur Anweisungstexte (Markdown, Text, YAML, JSON, TOML) laufen durch die Anweisungsmuster; Code ist Ebene C,
  Lockfiles sind Ebene D.
- Jede Regeldatei beginnt mit `# LUIBUI-Regel`, jede Testfixture im Korpus mit
  `LUIBUI-TESTFIXTURE: entschärft, nicht ausführen`.

---

# Teil E — Ehrlichkeit der Bewertung

**E1. Keine vorgetäuschte Prüftiefe**
- Der Bericht nennt, was nicht geprüft wurde und warum. Ein Analyzer, der nicht läuft, erscheint dort.
- Keine erfundenen Zähler („1.000 Pakete geprüft“), keine Beispielberichte ohne Kennzeichnung.

**E2. Kalibrierung**
- Jede Änderung an Regeln oder Schweregraden läuft gegen `corpus/` und die Vergleichs-Repos. Erkennungs- und
  Fehlalarmrate stehen ab Sprint 3 in `docs/benchmark.md`; eine Verschlechterung wird im Log benannt.
- Regeln mit zu vielen Fehlalarmen werden herabgestuft oder entfernt, mit Begründung.

**E3. Darstellung**
- Die Ampel entscheidet, die Note zeigt Fortschritt. Keine Note ohne Ampel.
- Unsichere Befunde (LLM, zitierte Beispiele, Beispielpfade) sind als solche erkennbar, am Befund, nicht in
  einer Fußnote.
- Eine Schwelle wird nicht gesenkt, „weil Rot schlecht aussieht“. Das ist der schwerste Verstoß in dieser Datei.

---

# Teil F — Qualität und Gates

> Regeln, die nicht automatisiert geprüft werden, werden nicht eingehalten.

## F1. Leistung

| Kennwert | Budget |
|---|---|
| Schnellscan eines typischen Repos | < 30 s |
| Intensivscan eines typischen Skill-Pakets | < 2 min |
| Worker-Job | Zeitlimit 5 min, Schnellscan 60 s |
| RAM Worker bei Prüfung | im Limit von 1,5 GB, gemessen in `docs/infra-kapazitaet.md` |
| Web ab Sprint 2 | Lighthouse Performance ≥ 90, Accessibility ≥ 95, CLS < 0,1 |

## F2. Fehlerbehandlung

- Jeder Fehlerpfad hat eine sichtbare Rückmeldung. **Keine leeren `except`/`catch`.**
- Fehlermeldungen enthalten nie Paketinhalt; geloggt wird der Typ.
- Teil-Verfügbarkeit ist normal: Fällt ein Analyzer aus, zeigt der Bericht die übrigen Befunde und den Ausfall.

## F3. Texte an einer Stelle

- Befundtexte stehen bei der Regel (YAML) oder im Analyzer, Oberflächentexte ab Sprint 2 in einer
  Locale-Datei. Begriffe nach A3.

## F4. Größe und Zuständigkeit

| Artefakt | Richtwert | Danach |
|---|---|---|
| Python-Modul | 400 Zeilen | in Teilmodule zerlegen |
| Funktion | 60 Zeilen | Schritte auslagern |
| Route-Handler | 80 Zeilen | Logik in ein Modul (`uploads.py`, `auth.py`) |
| React-Komponente | 200 Zeilen | Teilkomponenten |

Grenzwerte als benannte Konstanten (`MAX_PER_RULE`, `REGEX_TIMEOUT_SECONDS`), nicht verstreut.

## F5. Vorhandenes zuerst prüfen

Diese Bausteine gibt es **genau einmal**: Annahme (`intake`), Inventar, `finding()`, `visible()`,
`terminal_safe()`, `rules_dir()`, `get_owned()`, `bewerte()`, `build_report()`, Blob-Speicher.

## F6. Barrierefreiheit (ab Sprint 2)

- Kontrast nach A5, sichtbarer Fokus überall, Skip-Link, `aria-live` für Prüfstatus und Upload.
- **Die Ampel hat ein Textäquivalent** („Sicherheit: Gelb, Prüfung nötig“). Nie Farbe allein.

## F7. Automatische Gates

**Vor jedem Commit (lokal, Git-Hook):** `ruff check` · `ruff format --check` · `mypy` · betroffene Tests.

**CI bei jedem Push:**
1. ruff, mypy, pytest mit PostgreSQL — **kein übersprungener Test**
2. gitleaks und osv-scanner installiert (für die Analyzer-Tests)
3. Web: eslint, tsc, vitest, Build
4. Images bauen (worker, api, web)
5. geplant: Secret-Scan der Historie, osv-scanner über die eigenen Lockfiles, Kontrast-Check

**Nicht automatisierbar**, deshalb in der Checkliste: A4, Teil E, Tonalität nach A3.

## F8. Tests

- **Unit:** Annahme (jede Ablehnung), Inventar, Bewertung, jede Regel mit positiven und negativen Fällen.
- **Sicherheit:** Zip-Slip, Symlinks, Bomben, SSRF-URLs, CSRF, Umgehungsversuche gegen Werkzeuge
  (`.gitleaks.toml` im Paket), Netzisolation.
- **Zugriff:** Nutzer B erreicht keine Daten von Nutzer A, für jede Route.
- **Ende zu Ende:** Upload über die API → echter Worker → Bericht.
- **Praxistest:** Vergleichs-Repos ohne Fehlalarm (A13.2).

## F9. Checkliste vor dem Commit

- [ ] ruff, Format, mypy, pytest grün (mit Datenbank)
- [ ] Keine Regel aus A4 verletzt: kein „sicher“, kein Grün bei Unvollständigkeit, LLM/ATR sperren nicht allein
- [ ] Neue Befunde haben Regel-ID, Beleg, Nachweisgrad, Fix und Fix-Prompt; Belege maskiert (A8)
- [ ] Paketinhalt nur über `intake`, Werkzeuge nur über Adapter, Dateien nur über `storage` (A9)
- [ ] Neue Route: `get_owned()` und Test „B sieht A nicht“ (A12)
- [ ] Keine Paketinhalte und keine personenbezogenen Daten in Logs (A11)
- [ ] Neue Regel: mindestens zwei positive und zwei negative Testfälle, Praxistest ohne Fehlalarm (D, E2)
- [ ] Neue Abhängigkeit: Lizenz geprüft, Begründung im Log (A13.5)
- [ ] Neues Werkzeug: gepinnte Version und Prüfsumme (A12)
- [ ] Datenbankänderung: Migration reversibel, Test grün (A10)
- [ ] Dateien einzeln benannt beim Commit (A13.9)
- [ ] `docs/log.md` und Protokoll nachgetragen (A13.11)

---

# Teil G — Recht und Datenschutz

> Operative Checkliste, keine Rechtsberatung.

**G1. Rollen und Verträge**
- Für Projekt-Dateien im Entwicklerbereich ist luibui **Auftragsverarbeiter** der Entwickler. Der AV-Vertrag
  mit mittwald ist Aufgabe S0-13 (Len); ob er für luibui abgeschlossen ist, steht noch nicht im Log.
- Verzeichnis von Verarbeitungstätigkeiten (`docs/vvt.md`) und Drittdienste (`docs/drittdienste.md`) werden
  gepflegt.

**G2. Speicherung und Löschung**
- Projekt-Dateien verschlüsselt, bis der Entwickler sie löscht; 500 MB pro Konto, letzte 10 Versionen.
  „Nach Prüfung löschen“ speichert nichts.
- Schnellscan: nichts gespeichert außer dem Bericht, der nach 7 Tagen verschwindet (Löschlauf per Cron).
- Kontolöschung und Datenexport im Produkt (S2-10), nicht nur per Mail.
- Bekannte Schadsoftware wird nie abgelegt.

**G3. Veröffentlichung im Register (ab Sprint 4)**
- Veröffentlichen nur als Paket mit Manifest und nicht gesperrt. Öffentliche Berichte nennen Stand und
  Prüfumfang.

**G4. Fremde Daten und Lizenzen**
- Fremde Regeln und Datenbanken mit Lizenz und Quelle in `THIRD_PARTY_NOTICES.md`; OSV-Befunde nennen
  `osv.dev/<ID>` (CC-BY).

---

# Anhang — Fehler, die hier nicht passieren dürfen

| Fehler | Warum falsch |
|---|---|
| „sicher“ in einer Ausgabe | A4 |
| Grün, obwohl ein Analyzer fehlte oder fehlschlug | A4, E1 |
| Paket gesperrt nur durch LLM oder ATR | A4 |
| Timeout einer Regel als „kein Treffer“ | A12 |
| Werkzeug liest Konfiguration aus dem Paket (`.gitleaks.toml`) | A9, belegte Umgehung |
| osv-scanner mit Aufrufanalyse (führt Build-Skripte aus) | CLAUDE.md Regel 1 |
| Beleg als HTML oder Markdown gerendert | A7, CLAUDE.md Regel 6 |
| Route ohne `get_owned()` | A12, CLAUDE.md Regel 9 |
| Paketinhalt oder Ausnahmetext im Log | A11 |
| `git add -A` im Wurzelordner | A13.9 |
| Commit ohne vorheriges ruff/mypy | A13.10 |
| Fehlalarm im Vergleichsbestand „später beheben“ | E2 |
| Schwelle senken, damit ein Paket grün wird | E3 |
| Secret im Klartext in Ausgabe, Log oder Protokoll | CLAUDE.md, Protokollregeln |

---

# Umsetzungsstand (Abgleich 27.09.2026)

| Regel | Stand | Anmerkung |
|---|---|---|
| A4 kein Grün bei Unvollständigkeit, LLM/ATR sperren nicht | ✅ | `scan.ERWARTET`, Tests |
| A7/A8 Belege escaped, Terminal-Escaping | ✅ | `visible()`, `terminal_safe()` |
| A9 ein Eingang, Adapter, Storage | ✅ | |
| A10 `owner_id`, UUIDs, reversible Migrationen | ✅ | Migrationstest |
| A12 Zugriff, CSRF, URL-Prüfung, Netzisolation, Regex-Timeout | ✅ | |
| A12 Client-IP hinter dem Proxy | ❌ | `X-Forwarded-For` offen, deshalb `ANNAHME_OFFEN` aus |
| A13.2 Praxistest an echten Repos | ✅ | seit S1-6 |
| A13.9 Dateien einzeln committen | ✅ ab 27.09. | davor `git add -A`, fremde Datei im Repo |
| A13.10 alle Prüfungen vor dem Commit | ⚠️ | einmal nur pytest (S1-5 rot); kein Git-Hook |
| A14 ADRs | ❌ | `docs/adr/` leer, Entscheidungen nur in `docs/log.md` |
| A5/A6 Tokens, Schriften lokal | ⚠️ | Web noch Gerüst: `globals.css` hat ein Farbliteral und `system-ui` |
| A11 `docs/drittdienste.md`, `docs/vvt.md` | ❌ | fehlen; mittwald, GitHub, osv.dev eintragen |
| G1 AV-Vertrag mit mittwald für luibui | ❓ | S0-13 (Len), Stand nicht dokumentiert |
| A11 keine IP-Adressen im Log | ⚠️ | uvicorn-Zugriffslog schreibt Client-IPs (Proxy-IPs) |
| C Fehlerformat mit `code` | ⚠️ | teils `{"detail": "Text"}`, teils `{"grund", "text"}` — vor Sprint 2 vereinheitlichen |
| C Versionierung `/api/v1` | ❌ | vor der ersten Nutzung durch CLI/CI |
| F4 Modulgröße 400 Zeilen | ⚠️ | `a_dateien.py` 656 Zeilen, in Teilmodule zerlegen |
| F7 Git-Hook vor dem Commit | ❌ | vorschlagen: `.githooks/pre-commit` ohne neue Abhängigkeit |
| F7 Secret-Scan und OSV über das eigene Repo in der CI | ❌ | Werkzeuge sind in der CI schon installiert |
| F7 CI läuft | ❌ | GitHub-Abrechnung sperrt Jobs seit 27.09., 08:08 |
