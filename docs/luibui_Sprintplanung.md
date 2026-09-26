# luibui – Sprintplanung v2: Prüfstelle zuerst, Register danach

> Stand: 26.09.2026 · Owner: Len · Domain: **luibui.com** · Lizenz: **AGPL-3.0**
> Grundlage: `luibui_Konzept.md` (v2), `luibui_Pruefkatalog.md` · Prompts: `luibui_ClaudeCode_Prompts.md`
> **Öffentliche Beta der Prüfstelle: 20.11.2026** · Register: Dezember · Sandbox: Januar 2027

---

## 0. Infrastruktur – Ist-Stand

| Element | Wert |
|---|---|
| mittwald-Projekt | `luibui` · `p-yw5cv5` · ID `b8d0a6a8-83ef-4aba-b785-0b450c0ac551` |
| Server | „All“ · `s-r0ud3w` · 2 vCPU (shared), 8 GiB RAM, 150 GiB, geteilt mit 7 Projekten |
| Domains | `luibui.com`, `luibui.de` |
| Zugriff | mittwald-API-Token + MCP → Claude richtet ein und deployt |

### Hostnamen

| Hostname | Zweck | ab Sprint |
|---|---|---|
| `luibui.com` | **Marketingseite** mit Anmelden/Registrieren, „So prüfen wir“, Doku, Spenden; Schnellscan ohne Anmeldung; später Register und öffentliche Berichte | 0 |
| `app.luibui.com` | **Entwicklerbereich:** Projekte, Dateien, Prüfungen, Verlauf, Konto | 0 (Inhalt ab Sprint 2) |
| `api.luibui.com` | API: Projekte, Scans, Berichte, Pakete | 0 |
| `luibui.de` | 301 → `luibui.com` | 0 |
| `mcp.luibui.com` | Hosted MCP | 7 |
| `chat.luibui.com` | Playground mit Angriffs-Testprompts | 7 |

### Kapazität

| Phase | Limits | Summe |
|---|---|---|
| Sprint 0–2 | web 384m · api 512m · postgres 768m · worker 1536m | ≈ 3,2 GB |
| ab Sprint 4 mit ClamAV | worker 2560m | ≈ 4,2 GB |

⚠ Auf dem geteilten Server wird das eng. **Entscheidung eigener vServer (M) für den Worker bis 16.10.** anhand des Kapazitätsberichts. Web, API und Postgres können auf dem geteilten Server bleiben.

---

## 1. Rahmen

| Parameter | Wert |
|---|---|
| Team | Len (Produkt, Regeln prüfen, Recht, Community, Freigaben) + Claude Code in VS Code (Code, Tests, Deployment) |
| Kapazität Len | ca. 25 h/Woche, davon 10 h Puffer pro Sprint |
| Sprintlänge | 2 Wochen (Sprint 0: 1 Woche) · Pause 21.12.2026 – 01.01.2027 |
| Stack | Next.js 15 · FastAPI · PostgreSQL 17 · Python 3.12 Engine `luibui-scan` · CLI `luibui` |
| Deployment | Docker Compose über mittwald (MCP oder `mw` CLI), GitHub Actions |
| Repo | öffentlich, AGPL-3.0; `rules/` und `packages/engine` Vorschlag MIT |

### Rituale
- **Montag (30 min):** Sprint-Prompt in Claude Code einfügen, Tasks in GitHub Projects
- **Täglich (5 min):** `docs/log.md` – gestern / heute / blockiert
- **Freitag (60 min):** Demo gegen Definition of Done, Korpus-Ergebnis ansehen, Deploy

---

## 2. Übersicht

| Sprint | Zeitraum | Ziel | Meilenstein |
|---|---|---|---|
| 0 – Fundament | 28.09. – 02.10. | Repo, Infra, Schemas, Werkzeugwahl, Bedrohungsmodell | `api.luibui.com/health` = 200, Schemas + `docs/scanner-tools.md` |
| 1 – Scan-Kern | 05.10. – 16.10. | Sichere Annahme, Warteschlange, Ebenen A, B, D, Secrets, Bewertung | `luibui scan ./paket` liefert JSON mit Ampel |
| 2 – Code, MCP, Entwicklerbereich | 19.10. – 30.10. | Ebenen C, E, DSGVO, Korrelation, app.luibui.com mit Projekten, Dateiablage und Bericht | Entwickler legt Projekt an → Upload → Bericht mit zwei Ampeln |
| 3 – Qualität & Start | 02.11. – 13.11. | LLM-Prüfer, Testkorpus, Befund-Status, Verlauf, Recht, Landingpage | Erkennungs- und Fehlalarm-Quote erreicht |
| **Beta-Start** | 16.11. – 20.11. | Öffentliche Prüfstelle | **luibui.com live am 20.11.** |
| 4 – Register | 23.11. – 04.12. | Veröffentlichen, Paketseite, Installieren (Claude, MCP), Diff-Prüfung, Dateiansicht mit Befunden, ClamAV | erstes geprüftes Paket installierbar |
| 5 – Überall | 07.12. – 18.12. | weitere Adapter, Git-Anbindung, Neuprüfung, Benachrichtigungen, Badge, CI-Action, websecureaudit | Push ins Repo → automatische Prüfung im Entwicklerbereich |
| *Pause* | 21.12. – 01.01. | – | – |
| 6 – Sandbox | 04.01. – 15.01.2027 | Verhaltensprüfung auf eigenem Server | Köder-Zugangsdaten erkennen Diebstahl |
| 7 – Hosted MCP & Playground | 18.01. – 29.01.2027 | MCP-Hosting, Prompt-Angriffstests | Paket gehostet + Angriffstest im Bericht |

---

## 3. Sprints im Detail

### Sprint 0 – Fundament · 28.09. – 02.10.2026

| ID | Task | Wer | h |
|---|---|---|---|
| S0-1 | Öffentliches Repo, Monorepo-Struktur laut Konzept, LICENSE (AGPL-3.0; MIT für `rules/`, `packages/engine` nach Freigabe), `CLAUDE.md`, CONTRIBUTING, SECURITY.md | Claude | 2 |
| S0-2 | `docs/` befüllen: Konzept, Sprintplanung, Prüfkatalog | Len | 0,5 |
| S0-3 | `spec/luibui.schema.json` (Manifest), `spec/finding.schema.json`, `spec/report.schema.json` (Felder laut Konzept §5) | Claude | 4 |
| S0-4 | `docs/scanner-tools.md`: jedes Werkzeug aus Konzept §9 mit Version, Lizenz, Offline-Fähigkeit, RAM-Bedarf, Aufruf, Ausgabeformat; Lizenzfrage Semgrep-Regeln klären | Claude | 4 |
| S0-5 | `docs/threat-model.md`: Bedrohungsmodell der Prüfstelle selbst (feindliche Uploads, Git, Berichtsdarstellung, DoS) | Claude | 3 |
| S0-6 | Review S0-3 bis S0-5, Freigabe | Len | 2 |
| S0-7 | `infra/docker-compose.yml`: web, api, worker, postgres mit Limits; Volumes `luibui-pgdata`, `luibui-scratch`, `luibui-rules`, `luibui-projects` | Claude | 2 |
| S0-8 | API-Skeleton: Health, Settings, Alembic für users, tokens, projects, project_versions, stored_files, scans, findings, finding_status, jobs, packages, versions, audit_log | Claude | 4 |
| S0-9 | Worker-Skeleton: Job-Loop mit `SELECT … FOR UPDATE SKIP LOCKED`, Timeout, Scratch-Verzeichnis pro Job mit garantiertem Aufräumen | Claude | 3 |
| S0-10 | Engine-Skeleton `packages/engine`: Pipeline mit Analyzer-Interface (`analyze(ctx) -> list[Finding]`), Registry der Analyzer | Claude | 3 |
| S0-11 | CI: ruff, mypy, eslint, pytest, Image-Build | Claude | 2 |
| S0-12 | mittwald: Volumes, Virtual Hosts `luibui.com`, `app.luibui.com`, `api.luibui.com` mit TLS, `luibui.de` → 301, Stack-Deploy, `docs/infra-kapazitaet.md` | Claude | 2 |
| S0-13 | AVV mit mittwald im AV Manager | Len | 0,5 |

**Definition of Done**
- [ ] `docker compose up` startet alle vier Container lokal
- [ ] `https://api.luibui.com/health` = 200
- [ ] Schemas validieren Beispiel-Befunde (Tests)
- [ ] `scanner-tools.md` und `threat-model.md` freigegeben
- [ ] Worker räumt Scratch auch nach absichtlichem Absturz auf (Test)

---

### Sprint 1 – Scan-Kern · 05.10. – 16.10.2026

**Ziel:** Ein Paket lässt sich sicher annehmen und auf Datei-, Inhalts-, Secret- und Abhängigkeitsebene prüfen. Das Ergebnis ist ein bewerteter JSON-Bericht.

| ID | Task | h |
|---|---|---|
| S1-1 | Annahme: `POST /api/projects/{id}/scans` (Einzeldatei, mehrere Dateien mit relativen Pfaden, Text, ZIP oder Git-Commit) und `POST /api/quickscans` (öffentliche Git-URL, ohne Speicherung), Status `GET /api/scans/{id}`, Rate-Limit pro IP | 4 |
| S1-2 | Sichere Annahme aller Eingabearten über einen gemeinsamen Weg: ZIP entpacken mit Limits (50/200 MB, 10.000 Dateien, Tiefe 20, Kompressionsrate > 100 = Bombe), Einzeldateien (10 MB), Dateiauswahl/Ordner (1.000 Dateien, 50 MB, relative Pfade wie ZIP-Einträge prüfen), Text (200 KB); `../`, absolute Pfade, Symlinks, verschlüsselte Einträge → Befund + Abbruch | 6 |
| S1-3 | Sicherer Git-Clone: HTTPS-Allowlist (github.com, codeberg.org, gitlab.com), `--depth 1`, ohne Submodule, Hooks aus, Größenlimit | 3 |
| S1-4 | Inventar: Magic Bytes, SHA-256, Sprachen, Pakettyp-Erkennung (Skill, MCP-Server, Plugin, gemischt) | 3 |
| S1-5 | Analyzer **A – Dateien** (Prüfkatalog A2–A12): Autostart-Dateien, Install-Skripte, Binaries, Endung ≠ Typ, versteckte Dateien, Paketquellen | 6 |
| S1-6 | Analyzer **B – Inhalte** (B1–B7): Unicode-Tags, Zero-Width, Bidi, Homoglyphen, versteckter Text in HTML/SVG/CSS/Markdown, kodierte Blöcke | 6 |
| S1-7 | Analyzer **B – Muster** (B8–B17): ATR-Regeln einbinden + eigene Regeln in `rules/`, jede Regel mit positivem und negativem Testfall | 5 |
| S1-8 | Analyzer **Secrets**: gitleaks, Werte im Befund maskieren | 2 |
| S1-9 | Analyzer **D – Abhängigkeiten**: OSV-Scanner offline, Typosquatting-Abstand zu Top-Paketen, Lockfile-Prüfung; Cronjob für OSV-DB | 4 |
| S1-10 | Bewertung: Ampeln, Sperrliste, Note, Freigabe-Stufe und **Prüfumfang** (Paket / Dateiauswahl / Einzeldatei; DSGVO „nicht bewertet“ ohne Manifest) laut Konzept §5 | 3 |
| S1-11 | CLI `luibui scan <pfad>` lokal für Ordner, ZIP **und einzelne Dateien**, Ausgabe als Text und `--json` | 3 |
| S1-12 | Kapazitätsmessung: RAM/CPU/Dauer pro Scan bei 3 Paketgrößen → `docs/infra-kapazitaet.md` + Empfehlung vServer | 1 |

**Definition of Done**
- [ ] Präparierte Archive (Bombe, `../`, Symlink, verschlüsselt) und Dateiauswahlen mit manipulierten Pfaden werden erkannt und verworfen (Tests)
- [ ] Eine einzelne `SKILL.md` mit versteckten Unicode-Anweisungen wird als Einzeldatei geprüft und korrekt gesperrt (Test)
- [ ] Jede Regel in `rules/` hat mindestens einen positiven und einen negativen Testfall
- [ ] `luibui scan corpus/benign/*` liefert keine K/H-Befunde
- [ ] Scratch ist nach jedem Scan leer (Test)
- [ ] Entscheidung vServer getroffen

---

### Sprint 2 – Code, MCP, Entwicklerbereich · 19.10. – 30.10.2026

**Ziel:** Vollständige statische Prüfung plus der eigene Bereich für Entwickler auf app.luibui.com: anmelden, Projekt anlegen, Dateien hochladen, Bericht sehen.

> Dichtester Sprint. Bei Verzug rutscht S2-3 (MCP-Analyzer) in Sprint 3.

| ID | Task | h |
|---|---|---|
| S2-1 | Analyzer **C – Code**: Opengrep mit eigenen Regeln (C1–C13), Bandit | 6 |
| S2-2 | Cisco skill-scanner einbinden (nur Offline-Analyzer), Befunde auf luibui-Schema mappen, Duplikate zusammenführen | 4 |
| S2-3 | Analyzer **E – MCP**: Cisco mcp-scanner offline, Tool-Beschreibungen, Auth/Transport-Konfiguration | 4 |
| S2-4 | Analyzer **G – DSGVO und Rechte**: Endpunkte und Rechte aus Code extrahieren, gegen Manifest, Länderzuordnung (gepflegte Liste + Angemessenheitsbeschlüsse) | 5 |
| S2-5 | **Korrelation**: Verweise aus Markdown auf Dateien auflösen, Befunde hochstufen | 3 |
| S2-6 | Auth: E-Mail + Passwort (Argon2), TOTP, Session-Cookie host-only für `app.luibui.com`, API-Tokens | 5 |
| S2-7 | **Verschlüsselte Dateiablage:** Projekt-Dateien auf `luibui-projects`, pro Projekt ein Datenschlüssel (mit Hauptschlüssel aus ENV verschlüsselt), Kontingent 500 MB / 10 Versionen, Option „nach Prüfung löschen“, Schadsoftware nie ablegen | 5 |
| S2-8 | **app.luibui.com – Übersicht und Projekte:** Host-Routing in Next.js, Übersicht aller Projekte (Ampel, Note, letzte Prüfung, offene K/H oben), Projekt anlegen (Name, Typ, Quelle), **Upload-Feld für einzelne Dateien, mehrere Dateien, ganze Ordner (Drag & Drop), ZIP und eingefügten Text**, „Schnell eine Datei prüfen“ direkt auf der Übersicht, neue Version hochladen, Prüfungsliste pro Projekt | 7 |
| S2-9 | **app.luibui.com – Bericht:** zwei Ampeln, Note, Freigabe, Befunde nach Schwere, Belege escaped und maskiert, Fix + Fix-Prompt kopierbar, Fortschritt während der Prüfung | 6 |
| S2-10 | **app.luibui.com – Konto:** Profil, 2FA, API-Tokens, Speicherverbrauch, Datenexport, Konto löschen | 3 |
| S2-11 | **luibui.com – Grundgerüst Marketingseite:** Startseite mit „Anmelden“ und „Kostenlos registrieren“ (führen zu app.luibui.com/anmelden bzw. /registrieren, im gleichen Design) | 2 |
| S2-13 | **Schnellscan** auf luibui.com: öffentliche Git-URL oder eine Datei bis 2 MB, ohne Anmeldung, reduzierte Pipeline (A, B-Regeln, Secrets, D), unter 30 s, Hinweis „eingeschränkter Umfang, ohne Gewähr“, nichts gespeichert, Bericht 7 Tage, Rate-Limit, Button zum Intensivscan | 3 |
| S2-12 | Download **CSV** (eine Zeile pro Befund, UTF-8 mit BOM, Semikolon, **gegen CSV-Injection abgesichert**), JSON und SARIF 2.1.0; Teilen eines Berichts per Link mit Zufalls-Token | 3 |

**Definition of Done**
- [ ] luibui.com → Registrieren → Projekt anlegen → Ordner oder ZIP hochladen → Bericht in unter 2 Minuten für ein typisches Skill-Paket
- [ ] Eine einzelne Datei per Drag & Drop auf der Übersicht → Bericht mit Hinweis „Einzeldatei-Prüfung“
- [ ] **Nutzer A kommt über keine Route an Projekte, Dateien, Berichte oder Tokens von Nutzer B** (automatisierter Test für jede Route)
- [ ] Dateien liegen verschlüsselt auf dem Volume (Test liest Rohdatei und findet keinen Klartext)
- [ ] SARIF lässt sich in GitHub Code Scanning importieren
- [ ] CSV öffnet sich korrekt in Excel und LibreOffice; ein Beleg, der mit `=`, `+`, `-` oder `@` beginnt, wird nicht als Formel ausgeführt (Test)
- [ ] Schnellscan eines Beispiel-Repos in unter 30 Sekunden, Bericht trägt den Hinweis „ohne Gewähr“
- [ ] Ein Beleg mit `<script>`, `<img onerror>` oder Markdown-Bild-Link wird als Text angezeigt (Test)
- [ ] Session-Cookie wird auf `luibui.com` nicht mitgesendet
- [ ] Keine externen Ressourcen im Frontend

---

### Sprint 3 – Qualität & Start · 02.11. – 13.11.2026

**Ziel:** Die Prüfstelle ist genau genug, rechtlich sauber und öffentlich nutzbar.

| ID | Task | Wer | h |
|---|---|---|---|
| S3-1 | Testkorpus: 60 gutartige Pakete (echte offene Skills/MCP-Server mit Lizenz) + 60 **entschärfte** bösartige Nachbildungen (alle Kategorien des Prüfkatalogs, Endpunkte `.invalid`, keine echten Payloads) | Claude | 8 |
| S3-2 | Benchmark-Skript: Erkennungsrate und Fehlalarm-Quote pro Kategorie → `docs/benchmark.md`, läuft in CI | Claude | 3 |
| S3-3 | LLM-Prüfer über mittwald AI Hosting: Anweisungen, Tool-Beschreibungen, „Beschreibung ≠ Verhalten“; strukturierte Ausgabe; Prompt gegen Injection gehärtet (Paketinhalt als Daten markiert) | Claude | 6 |
| S3-4 | AI-Hosting-Key im mStudio, als Secret hinterlegen | Len | 0,5 |
| S3-5 | **app.luibui.com – Verlauf:** Note und Befundzahl über die Zeit, Vergleich zweier Prüfungen (neu, behoben, unverändert) | Claude | 4 |
| S3-6 | Regeln kalibrieren bis Abnahmewerte erreicht | Claude + Len | 6 |
| S3-7 | **Befund-Status** im Entwicklerbereich: offen, behoben (automatisch, wenn in neuer Version weg), akzeptiert (mit Begründung), bestritten (Einspruch); Moderationsansicht für Einsprüche | Claude | 5 |
| S3-8 | Rechtstexte einbauen: Impressum, Datenschutz, Nutzungsbedingungen mit Haftungsausschluss, Disclosure-Richtlinie; DSA-Meldeformular | Claude (Texte: Anwalt) | 3 |
| S3-9 | luibui.com fertigstellen: Marketingseite (Nutzen, Ablauf, Ampel erklärt, Beispielbericht, „Kostenlos registrieren“), „So prüfen wir“, Prüfkatalog, Doku-Einstieg, Transparenz- und Spendenseite, SEO-Grundlagen | Claude | 5 |
| S3-11 | **PDF-Bericht** für Schnell- und Intensivscan: Deckblatt (Ampeln, Note, Umfang, Scan-Art, Datum), Befunde mit Beleg und Fix, Haftungsausschluss auf jeder Seite, beim Schnellscan „ohne Gewähr“ im Kopf; serverseitig erzeugt ohne Nachladen externer Ressourcen | Claude | 4 |
| S3-10 | Produktion: Limits, Backups, verschlüsselter pg_dump, Restore-Test, Health-Cronjob mit Mail-Alarm | Claude | 4 |

**Definition of Done**
- [ ] **Erkennung ≥ 90 %** der entschärften bösartigen Pakete (Code-Ebene ≥ 95 %)
- [ ] **Fehlalarme ≤ 5 %** der gutartigen Pakete mit K/H-Befund
- [ ] Rechtstexte vom Anwalt freigegeben
- [ ] Restore-Test dokumentiert
- [ ] PDF und CSV für Schnell- und Intensivscan herunterladbar, Belege mit `<script>` erscheinen im PDF als Text

---

### Beta-Start · 16.11. – 20.11.2026

| Aufgabe | Wer |
|---|---|
| luibui als neuntes Projekt auf lensuh.de | Len |
| Ankündigung: Heise-Forum, Reddit (r/de_EDV, r/ClaudeAI, r/mcp), Mastodon, LinkedIn, Discords der KI-Tools | Len |
| 20 bekannte offene Skills/MCP-Server prüfen, Autoren mit Befunden privat informieren (Disclosure) | Len + Claude |
| Bugfixes, Regelanpassungen aus Einsprüchen | Claude |

---

### Sprint 4 – Register · 23.11. – 04.12.2026

| ID | Task | h |
|---|---|---|
| S4-1 | Organisationen/Namespaces, Namensverwechslungs-Prüfung (H4) | 3 |
| S4-2 | **app.luibui.com – Veröffentlichen:** Paket aus einem Projekt/Bericht ins Register (nicht bei gesperrt), Versionen unveränderlich und signiert, Versionsverwaltung | 5 |
| S4-3 | Paketseite: zwei Ampeln, Note, **Rechte-Label**, Befunde, README (sanitized), Versionen | 6 |
| S4-4 | Suche mit Filtern (Ziel, Ampel, Typ, Rechte) | 4 |
| S4-5 | `luibui install` mit Adaptern **Claude** und **MCP**, Lockfile | 5 |
| S4-6 | **Diff-Prüfung** (H1): neue Rechte/Endpunkte gegenüber Vorversion hervorheben | 4 |
| S4-7 | Disclosure-Workflow: neuer K/H-Befund → Autor sofort, öffentlich „Befund offen“ für 14 Tage | 3 |
| S4-8 | **app.luibui.com – Dateien:** Dateibaum der geprüften Version, Dateiansicht als escaped Text mit Befunden an der Zeile, Download als Anhang | 5 |
| S4-10 | ClamAV im Worker oder auf dem Worker-vServer inkl. Cronjob für Signaturen | 2 |

**DoD:** Ein geprüftes Paket ist aus dem Entwicklerbereich veröffentlicht und per `luibui install --target claude` nutzbar; ein Update mit neuem Endpunkt zeigt den Diff; die Dateiansicht markiert Befunde an der richtigen Zeile.

---

### Sprint 5 – Überall · 07.12. – 18.12.2026

| ID | Task | h |
|---|---|---|
| S5-1 | Adapter ChatGPT, Gemini, Mistral, Open WebUI (Formate vorher aktuell recherchieren) | 6 |
| S5-2 | Nächtliche Neuprüfung aller veröffentlichten Pakete, Benachrichtigung bei Verschlechterung | 4 |
| S5-3 | `luibui audit` für installierte Pakete | 2 |
| S5-4 | Badge-SVG und Einbettungs-Snippet | 2 |
| S5-5 | GitHub-Action + Codeberg/Forgejo-Action + pre-commit-Hook (`luibui scan` lokal, SARIF-Upload) | 5 |
| S5-6 | websecureaudit-Anbindung für Remote-MCP-URLs (interne API, Befunde als Ebene E7) | 4 |
| S5-7 | Herkunft (H3): Paket gegen Git-Tag abgleichen | 3 |
| S5-8 | **app.luibui.com – Automatisierung:** Git-Repository verbinden (GitHub, Codeberg, GitLab), Webhook mit Signaturprüfung, Prüfung bei Push/Tag, CI-Snippet und Projekt-Token | 5 |
| S5-9 | **Benachrichtigungen:** Mail bei neuen Befunden (Neuprüfung, Push), Einspruchs-Entscheidung, Meldungen; Einstellungen im Konto | 3 |

**DoD:** Ein Paket in allen sechs Zielen installierbar; ein Push in ein verbundenes Repo erzeugt automatisch eine Prüfung im Entwicklerbereich; die Action meldet Befunde als SARIF.

---

### Sprint 6 – Sandbox · 04.01. – 15.01.2027

Läuft auf einem **eigenen vServer** (gVisor oder nsjail nötig).

| ID | Task | h |
|---|---|---|
| S6-1 | Sandbox-Host einrichten, Isolation (gVisor/nsjail), kein Netz, Ressourcen- und Zeitlimits | 6 |
| S6-2 | Ausführung von Install-Skripten und MCP-Servern (Start + Tool-Aufrufe mit Testdaten) | 6 |
| S6-3 | Syscall- und Datei-Protokoll (strace), DNS-/Verbindungsversuche | 4 |
| S6-4 | **Köder-Zugangsdaten** (Canary-Tokens) in `~/.aws`, `~/.ssh`, `.env` | 3 |
| S6-5 | Zeitbomben: faketime, wiederholte Aufrufe | 2 |
| S6-6 | Befunde mit Nachweisgrad „in Sandbox beobachtet“ in den Bericht | 2 |

**DoD:** Alle entschärften Diebstahl-Nachbildungen im Korpus lösen die Köder aus; kein Ausbruch aus der Sandbox im Selbsttest.

---

### Sprint 7 – Hosted MCP & Playground · 18.01. – 29.01.2027

| ID | Task | h |
|---|---|---|
| S7-1 | `mcp.luibui.com`: gehostete MCP-Server nur für Pakete mit Gesamt Grün/Gelb, Netzwerk-Allowlist aus Manifest | 10 |
| S7-2 | `chat.luibui.com`: Playground mit mittwald AI Hosting, Paket per Klick testen | 6 |
| S7-3 | **Prompt-Angriffstests** (F6): automatisierte Testprompts, die den Skill zum Datenabfluss verleiten sollen; Ergebnis in den Bericht | 6 |

---

## 4. Parallel-Track (Len)

| Woche | Aufgabe | Deadline |
|---|---|---|
| KW 40 | Markenrecherche „luibui“ (DPMA/EUIPO) | 02.10. |
| KW 41 | Fachanwalt IT-Recht: Nutzungsbedingungen, Haftungsausschluss, Disclosure, Einspruch, DSA | 09.10. |
| KW 42 | Entscheidung eigener vServer für Worker | 16.10. |
| KW 42–43 | 10 Skill-/MCP-Entwickler:innen als Beta-Tester gewinnen | 23.10. |
| KW 44 | AI-Hosting-Tarif buchen; mittwald bestätigen lassen: kein Training auf Prompts | 30.10. |
| KW 45 | Rechtstexte final | 06.11. |
| KW 46 | Launch-Texte, lensuh.de-Eintrag, Liste der 20 Projekte für den Launch-Scan | 13.11. |

---

## 5. Upgrade-Trigger

| Baustein | Wann |
|---|---|
| Eigener vServer für Worker | Kapazitätsbericht > 60 % RAM auf dem geteilten Server oder ClamAV aktiv |
| Zweiter Worker | Wartezeit > 5 min zu Spitzenzeiten |
| Redis | mehrere API-Instanzen oder Rate-Limits über Prozesse |
| Sandbox-Server | Sprint 6 |
| AI Pro / Business | LLM-Kontingent erreicht |

---

## 6. Risiken pro Sprint

| Sprint | Risiko | Gegenmaßnahme |
|---|---|---|
| 0 | Werkzeug-Lizenz passt nicht zum Dienst | `scanner-tools.md` vor Einbau, eigene Regeln als Kern |
| 1 | Prüfstelle wird über Uploads angegriffen | Bedrohungsmodell, Limits, nie ausführen, Tests mit präparierten Archiven |
| 2 | Bericht wird selbst zum Angriffsvektor | Belege nur als Text, CSP, Test |
| 2 | Entwickler sieht fremde Projekte (fehlende Eigentümer-Prüfung) | zentrale Zugriffsprüfung in der API, Test für jede Route, keine fortlaufenden IDs (UUIDs) |
| 3 | Zu viele Fehlalarme zum Start | Abnahmewerte als harte Bedingung, sonst Regeln als „Hinweis“ statt Befund |
| 3 | LLM-Prüfer wird per Injection manipuliert | Inhalt als Daten markiert, strukturierte Ausgabe, LLM-Urteil nie allein für „Grün“ |
| Start | Rechtsstreit wegen roter Bewertung | nur eigene Veröffentlichungen öffentlich, Einspruch, sachliche Belege, Anwalt |
| 6 | Sandbox-Ausbruch | eigener Server, gVisor, keine Geheimnisse auf dem Host |
| alle | Solo-Betrieb | Scope kürzen statt Termin schieben |

---

## 7. Entscheidungen

- [x] Prüfstelle zuerst, Register ab Sprint 4
- [x] Zwei Achsen, Gesamt = schlechtere
- [x] Eigener Entwicklerbereich auf app.luibui.com, Dateien verschlüsselt, nur für den Eigentümer
- [ ] Kontingent 500 MB / 10 Versionen (Vorschlag)
- [x] AGPL-3.0 für die Plattform
- [ ] MIT für `rules/` und Engine (Vorschlag)
- [ ] Eigener vServer für den Worker (bis 16.10.)
- [ ] Anwalt (bis 09.10.)
- [ ] AI-Hosting-Tarif (bis 30.10.)
