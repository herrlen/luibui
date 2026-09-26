# luibui – Claude-Code-Prompts für VS Code

> So nutzt du die Datei:
> 1. Neuen Ordner `luibui` anlegen, in VS Code öffnen, Claude Code starten.
> 2. `CLAUDE.md` ins Wurzelverzeichnis legen. `luibui_Konzept.md`, `luibui_Sprintplanung.md` und `luibui_Pruefkatalog.md` nach `docs/`.
> 3. Den mittwald-MCP-Server in Claude Code einbinden (oder `mw` CLI mit API-Token installieren).
> 4. Zu Sprintbeginn den passenden Prompt unten kopieren und einfügen. Claude Code liest `CLAUDE.md` automatisch.
> 5. Freitags: „Prüfe die Definition of Done von Sprint X und schreibe das Ergebnis in docs/log.md.“

---

## Start-Prompt (einmalig, vor Sprint 0)

```
Lies CLAUDE.md und die drei Dokumente in docs/ vollständig. Fasse danach in max. 15 Zeilen zusammen:
was luibui ist, wie die Scan-Pipeline aufgebaut ist, wie bewertet wird und welche Sicherheitsregeln
für dich gelten. Nenne Widersprüche oder Lücken zwischen den Dokumenten und stelle mir bis zu
5 Fragen, die du vor Sprint 0 geklärt haben willst. Schreibe noch keinen Code.
```

---

## Sprint 0 – Fundament (28.09. – 02.10.)

```
Setze Sprint 0 aus docs/luibui_Sprintplanung.md um: S0-1, S0-3, S0-4, S0-5, S0-7 bis S0-12.
S0-2, S0-6 und S0-13 macht Len.

1. S0-1: Monorepo laut CLAUDE.md anlegen. LICENSE AGPL-3.0 im Root. In rules/ und packages/engine
   vorerst ebenfalls AGPL mit TODO-Hinweis "MIT nach Freigabe". CONTRIBUTING.md, SECURITY.md
   (Meldeweg für Sicherheitslücken in luibui selbst), README.md auf Deutsch.
2. S0-3: spec/luibui.schema.json, spec/finding.schema.json, spec/report.schema.json nach Konzept §5
   und §7. Beispiel-Dateien unter spec/examples/ und Tests, die sie validieren.
3. S0-4: docs/scanner-tools.md. Recherchiere für jedes Werkzeug aus Konzept §9 die aktuelle Version,
   Lizenz, ob es vollständig offline läuft, RAM-Bedarf, Aufruf und Ausgabeformat. Prüfe ausdrücklich
   die Lizenz der Semgrep-Registry-Regeln für den Einsatz in einem Online-Dienst und die Offline-Fähigkeit
   von Cisco skill-scanner und mcp-scanner. Mit Quellen-Links und Datum.
4. S0-5: docs/threat-model.md für die Prüfstelle selbst (STRIDE): feindliche ZIPs, feindliche Git-Repos,
   Berichtsdarstellung (XSS über Belege), DoS über große Pakete, Missbrauch als Malware-Ablage,
   Prompt-Injection gegen den LLM-Prüfer. Pro Bedrohung die Gegenmaßnahme und den Task, der sie umsetzt.
5. S0-7: infra/docker-compose.yml mit web, api, worker, postgres (PostgreSQL 17). Limits: web 384m,
   api 512m, worker 1536m, postgres 768m. Volumes luibui-pgdata, luibui-scratch (/scratch),
   luibui-rules (/rules), luibui-projects (/projects, nur api). Worker läuft als unprivilegierter Nutzer.
   Der web-Container bedient luibui.com und app.luibui.com (Host-Routing kommt in Sprint 2).
6. S0-8: FastAPI-Skeleton mit /health, pydantic-settings, Alembic-Migrationen für users, tokens,
   projects, project_versions, stored_files, scans, findings, finding_status, jobs, packages,
   versions, audit_log. Alle IDs als UUID. Jede Tabelle mit Nutzerdaten hat owner_id.
7. S0-9: Worker-Job-Loop mit SELECT … FOR UPDATE SKIP LOCKED, ein Job gleichzeitig, Timeout 5 min,
   Scratch /scratch/<job-id> mit Aufräumen im finally. Test: Job, der absichtlich abstürzt, hinterlässt
   kein Scratch-Verzeichnis.
8. S0-10: packages/engine (Paketname luibui-scan): ScanContext, Finding (aus dem Schema), Analyzer-Protokoll,
   Analyzer-Registry, Pipeline-Runner, leere scoring.py mit Signaturen. pip-installierbar.
9. S0-11: .github/workflows/ci.yml mit ruff, mypy, eslint, pytest, Image-Build.
10. S0-12: mittwald über MCP oder mw CLI: Volumes anlegen, Virtual Hosts luibui.com, app.luibui.com und
    api.luibui.com mit Zertifikaten, luibui.de per 301 auf luibui.com, Stack deployen. Danach Health prüfen und
    docs/infra-kapazitaet.md mit dem gemessenen RAM-Verbrauch schreiben.

Pro Task ein Commit mit Task-ID. Nichts Kostenpflichtiges buchen, keine anderen Projekte auf dem Server
anfassen. Vor Architekturänderungen fragen. Am Ende die Definition of Done von Sprint 0 prüfen.
```

---

## Sprint 1 – Scan-Kern (05.10. – 16.10.)

```
Setze Sprint 1 aus docs/luibui_Sprintplanung.md um (S1-1 bis S1-12). Halte dich strikt an die
Sicherheitsregeln in CLAUDE.md, besonders 1 bis 5.

Reihenfolge:
- Zuerst intake/: safe_extract.py (S1-2) und safe_git.py (S1-3) mit Tests gegen präparierte Archive:
  Zip-Bombe (hohe Kompressionsrate), Zip-Slip (../), absoluter Pfad, Symlink, verschlüsselter Eintrag,
  zu viele Dateien. Jede Erkennung erzeugt einen Befund (Prüfkatalog A2/A3) und bricht sicher ab.
- Alle Eingabearten laufen durch denselben sicheren Weg in intake/: einzelne Datei (10 MB), mehrere
  Dateien/Ordner mit relativen Pfaden (1.000 Dateien, 50 MB; Pfade exakt wie ZIP-Einträge prüfen),
  eingefügter Text (200 KB, wird als Datei gespeichert, Name vom Nutzer oder "eingabe.md"), ZIP, Git.
  Ergebnis ist immer ein Scratch-Verzeichnis + Inventar mit dem Prüfumfang (paket | auswahl | einzeldatei).
- Dann Annahme-API (S1-1): POST /api/projects/{id}/scans (alle Eingabearten, vorerst ohne Auth
  hinter einem Dev-Flag) und POST /api/quickscans (öffentliche Git-URL, nichts wird gespeichert),
  dann Inventar (S1-4).
- Dann die Analyzer: A-Dateien (S1-5, Prüfkatalog A2–A12), B-Inhalte (S1-6, B1–B7),
  B-Muster (S1-7, B8–B17: ATR-Regeln einbinden, Lizenz MIT beachten, plus eigene Regeln in rules/),
  Secrets mit gitleaks (S1-8, Werte maskieren), Abhängigkeiten mit OSV-Scanner offline (S1-9, dazu
  Cronjob-Definition für die OSV-DB, Typosquatting per Levenshtein gegen eine Top-Liste, Lockfile-Prüfung).
- Dann scoring.py (S1-10) genau nach Konzept §5 inkl. Sperrliste, Note und Prüfumfang: ohne Manifest
  ist die DSGVO-Achse "nicht bewertet" (außer Drittland-Endpunkte gefunden), Analyzer, die ein Paket
  brauchen, melden sich im Bericht als "nicht geprüft (Einzeldatei)". Tests für jede Ampelstufe und
  jeden Umfang.
- Dann CLI luibui scan <pfad> [--json] (S1-11) für Ordner, ZIP und einzelne Dateien.
- Zum Schluss S1-12: Scans für ein kleines, mittleres und großes Paket messen (RAM, CPU, Dauer),
  Ergebnis in docs/infra-kapazitaet.md mit klarer Empfehlung, ob der Worker einen eigenen vServer braucht.

Für Testfälle in corpus/ und rules/: nur entschärfte Nachbildungen laut CLAUDE.md Regel 8.
Pro Task ein Commit mit Task-ID. Am Ende auf p-yw5cv5 deployen und die Definition of Done prüfen.
```

---

## Sprint 2 – Code, MCP, Entwicklerbereich (19.10. – 30.10.)

```
Setze Sprint 2 aus docs/luibui_Sprintplanung.md um (S2-1 bis S2-13). Konzept §3 beschreibt den
Entwicklerbereich app.luibui.com. Wenn die Zeit knapp wird, S2-3 nach Sprint 3 verschieben und mir
Bescheid geben.

Engine:
- S2-1: Analyzer C mit Opengrep und ausschließlich eigenen Regeln in rules/opengrep/ (Prüfkatalog
  C1–C13, Python und JavaScript/TypeScript), dazu Bandit. Jede Regel mit Testfällen.
- S2-2 und S2-3: Cisco skill-scanner und mcp-scanner nur mit ihren Offline-Analyzern (kein Cloud-Aufruf,
  kein VirusTotal). Befunde auf spec/finding.schema.json mappen, Duplikate zusammenführen
  (gleiche Datei + Zeile + Kategorie).
- S2-4: Analyzer G: Endpunkte und Rechte (Shell, Dateisystem, Netzwerk, Env-Zugriff) aus dem Code
  extrahieren, gegen luibui.json abgleichen. Länderzuordnung über gepflegte Liste in rules/data/ plus
  Länder mit EU-Angemessenheitsbeschluss. Unbekannt = Gelb.
- S2-5: Korrelation: Verweise in SKILL.md und Tool-Beschreibungen auf Dateien auflösen; Befund ≥ M in
  der referenzierten Datei eine Stufe hochstufen und verlinken.

Plattform:
- S2-6: Auth mit Argon2 und TOTP. Session-Cookie host-only für app.luibui.com (Secure, HttpOnly,
  SameSite=Lax), kein Domain-Attribut. Die Oberfläche ruft die API über app.luibui.com/api/* auf
  (Next.js-Weiterleitung an den api-Container). api.luibui.com akzeptiert nur Bearer-Tokens, keine
  Cookies. API-Tokens gehasht, mit Ablaufdatum und Scope.
- S2-7: Verschlüsselte Dateiablage in apps/api/storage/: Envelope-Verschlüsselung (AES-256-GCM,
  pro Projekt ein Datenschlüssel, verschlüsselt mit MASTER_KEY aus ENV). Kontingent 500 MB pro Konto,
  die letzten 10 Versionen pro Projekt. Projekt-Option "Dateien nach Prüfung löschen". Wenn die
  Prüfung bekannte Schadsoftware (Sperrliste Ebene A) findet: nichts ablegen, nur Hash speichern.
- Zentrale Zugriffsprüfung: eine Dependency in FastAPI, die jede Ressource gegen owner_id prüft.
  Kein Endpunkt ohne sie. Schreibe einen Test, der für JEDE Route prüft, dass Nutzer B nicht an
  Daten von Nutzer A kommt (404, nicht 403).
- S2-8: app.luibui.com in apps/web per Next.js-Middleware nach Host trennen. Übersicht aller
  Projekte (Gesamtampel, Note, letzte Prüfung, offene K/H oben), Projekt anlegen (Name, Typ, Quelle),
  neue Version hochladen, Prüfungsliste pro Projekt. Ein Upload-Feld für alles: einzelne Datei,
  mehrere Dateien, ganzer Ordner per Drag & Drop (webkitdirectory, relative Pfade mitsenden), ZIP und
  ein Tab "Text einfügen". Dazu "Schnell eine Datei prüfen" als Drop-Zone auf der Übersicht, die ohne
  Projektanlage in das automatische Projekt "Einzelprüfungen" prüft. Limits vor dem Upload im Browser
  anzeigen und serverseitig erzwingen.
- S2-9: Bericht in app.luibui.com: zwei Ampeln, Note, Freigabe, Befunde nach Schwere gruppiert,
  Belege escaped und maskiert, Fix und Fix-Prompt mit Kopieren-Button, Fortschritt per Polling.
- S2-10: Konto: Profil, 2FA, API-Tokens, Speicherverbrauch, Datenexport (ZIP mit JSON + eigenen
  Dateien), Konto löschen (inkl. Dateien und Schlüssel).
- S2-11: luibui.com als Marketingseite (Grundgerüst): Startseite mit "Anmelden" und "Kostenlos
  registrieren". Die Formulare liegen auf app.luibui.com/anmelden und /registrieren im selben Design,
  damit das Session-Cookie host-only bleibt. Nach dem Login landet man auf der Übersicht in
  app.luibui.com.
- S2-12: Downloads im Bericht: CSV (eine Zeile pro Befund, Spalten laut Konzept §2 "Bericht als
  Download", UTF-8 mit BOM, Semikolon), JSON und SARIF 2.1.0 (validieren). CSV-Injection verhindern:
  jede Zelle, die mit =, +, -, @, Tab oder CR beginnt, bekommt ein vorangestelltes Apostroph; Test dazu.
  Teilen per Link mit Zufalls-Token.
- S2-13: Schnellscan auf luibui.com: öffentliche Git-URL oder eine Datei bis 2 MB ohne Anmeldung.
  Eigenes Pipeline-Profil "schnell" in der Engine (nur A, B-Regeln ohne LLM, Secrets, D bei Git),
  Ziel unter 30 s. Bericht mit deutlichem Hinweis "Schnellscan – eingeschränkter Umfang, ohne Gewähr",
  Liste der NICHT durchgeführten Prüfungen, Button "Kostenlos registrieren für den Intensivscan".
  Nichts speichern, Bericht 7 Tage per Link, Rate-Limit 3 pro Tag und IP, CSV-Download.

Design für beide Oberflächen: warmer heller Grund #F5F3EC, Petrol #0E5E5B, Schriften Bricolage
Grotesque, IBM Plex Sans, IBM Plex Mono – alle lokal ausgeliefert. Ampelstatus immer auch als Text.
app.luibui.com mit linker Navigation: Übersicht, Projekte, Konto.

Pflicht-Tests: Beleg mit <script>, <img onerror> und Markdown-Bild-Link wird als Text angezeigt;
Rohdatei auf dem Volume enthält keinen Klartext; Session-Cookie wird an luibui.com nicht gesendet.
CSP-Header setzen. Pro Task ein Commit, am Ende deployen und DoD prüfen.
```

---

## Sprint 3 – Qualität & Start (02.11. – 13.11.)

```
Setze Sprint 3 um (S3-1 bis S3-3, S3-5 bis S3-11; S3-4 macht Len).

- S3-1: Testkorpus. corpus/benign/: 60 echte offene Skills und MCP-Server mit kompatibler Lizenz
  (Quelle und Lizenz in corpus/benign/SOURCES.md). corpus/malicious/: 60 entschärfte Nachbildungen,
  mindestens zwei pro Kategorie des Prüfkatalogs (A, B, C, D, E, G), streng nach CLAUDE.md Regel 8.
  Jede Nachbildung hat expected.json mit den erwarteten Regel-IDs.
- S3-2: Benchmark-Skript, Erkennungsrate und Fehlalarm-Quote pro Kategorie, Ausgabe docs/benchmark.md,
  läuft in CI und schlägt fehl, wenn die Abnahmewerte unterschritten werden.
- S3-3: LLM-Prüfer über LLM_BASE_URL (mittwald AI Hosting). Prüft Anweisungen und Tool-Beschreibungen
  auf B8–B19 und "Beschreibung ≠ Verhalten". Paketinhalt in markierten Datenblöcken, strukturierte
  JSON-Ausgabe mit Schema-Validierung, Nachweisgrad "per LLM bewertet". Das LLM darf nur Befunde
  hinzufügen, nie entfernen oder Grün erzeugen. Test mit einem Paket, das den Prüfer per Injection
  zu "keine Befunde" überreden will.
- S3-5: app.luibui.com – Verlauf pro Projekt: Note und Befundzahl über die Zeit (einfaches
  Liniendiagramm, lokal gerendert), Vergleich zweier Prüfungen mit neu / behoben / unverändert.
  Befunde über Prüfungen hinweg per Fingerprint (rule_id + Datei + normalisierter Beleg) zuordnen.
- S3-6: Regeln kalibrieren, bis Erkennung ≥ 90 % (Code-Ebene ≥ 95 %) und Fehlalarme ≤ 5 %. Regeln,
  die zu viele Fehlalarme erzeugen, auf Schwere N/I zurückstufen und in docs/benchmark.md begründen.
- S3-7: Befund-Status im Entwicklerbereich: offen, behoben (automatisch, wenn der Fingerprint in der
  neuen Version fehlt), akzeptiert (Pflicht-Begründung, zählt weiter in die Ampel, wird aber markiert),
  bestritten (Einspruch an Moderation). Moderationsansicht für Admins.
- S3-8: Rechtstexte aus docs/recht/ einbauen, Haftungsausschluss an jedem Bericht, DSA-Meldeformular,
  Disclosure-Richtlinie als Seite, AVV-Text für Entwickler im Konto.
- S3-9: luibui.com fertigstellen: Marketingseite (Nutzen, Ablauf in 3 Schritten, Ampel erklärt,
  Beispielbericht, "Kostenlos registrieren"), "So prüfen wir" (Ebenen, Bewertung, Grenzen),
  Prüfkatalog, Doku-Einstieg, Spenden- und Transparenzseite, SEO-Grundlagen (Titel, Meta, Sitemap,
  strukturierte Daten), keine externen Skripte.
- S3-10: Produktions-Limits, Backup-Schedule (Postgres UND Volume luibui-projects; MASTER_KEY getrennt
  sichern und dokumentieren, wie Len ihn aufbewahrt), verschlüsselter pg_dump, dokumentierter
  Restore-Test, Health-Cronjob mit Mail-Alarm.

- S3-11: PDF-Bericht für beide Scan-Arten, serverseitig erzeugt (z. B. WeasyPrint oder ReportLab,
  Wahl mit Lizenz in docs/scanner-tools.md begründen). Externe Ressourcen beim Rendern komplett
  abschalten (kein URL-Fetcher, Fonts lokal). Belege nur als escaped Text. Deckblatt mit Ampeln,
  Note, Prüfumfang, Scan-Art und Datum; Haftungsausschluss auf jeder Seite; beim Schnellscan
  "ohne Gewähr" im Seitenkopf. Test: Beleg mit <script> und <img src=http://…> erscheint als Text
  und löst keinen Netzwerkzugriff aus.

Pro Task ein Commit. Am Ende deployen, Benchmark ausführen, DoD prüfen.
```

---

## Sprint 4 – Register (23.11. – 04.12.)

```
Setze Sprint 4 um (S4-1 bis S4-8, S4-10).
- S4-2: Veröffentlichen aus einem Projekt in app.luibui.com, nur bei Freigabe "freigegeben" oder
  "Prüfung nötig", nie bei "blockiert". Versionen unveränderlich und signiert.
- S4-3/S4-4: Paketseite auf luibui.com mit zwei Ampeln, Note, Rechte-Label (Netzwerk, Dateien, Shell,
  Zugangsdaten, Drittland), Befundliste, README (sanitized), Versionen; Suche mit Filtern.
- S4-5: luibui install mit Adaptern Claude (Skill-Ordner, MCP-Konfiguration) und MCP generisch.
- S4-6: Diff-Prüfung zwischen Versionen, neue Rechte und Endpunkte prominent.
- S4-7: Disclosure-Workflow: neuer K/H-Befund → Autor sofort per Mail, öffentlich 14 Tage nur
  "Sicherheitsbefund offen".
- S4-8: app.luibui.com – Dateien: Dateibaum der geprüften Version, Dateiansicht als escaped Text mit
  Zeilennummern und Befund-Markierung an der Zeile (Klick öffnet den Befund), Download nur als
  application/octet-stream mit Content-Disposition: attachment. Git-Projekte holen den Commit bei
  Bedarf über safe_git.py. Keine Syntax-Hervorhebung, die HTML aus dem Inhalt erzeugt.
- S4-10: ClamAV mit Signatur-Cronjob, je nach Entscheidung auf dem Worker-vServer.
Pro Task ein Commit, deployen, DoD prüfen.
```

---

## Sprint 5 – Überall (07.12. – 18.12.)

```
Setze Sprint 5 um (S5-1 bis S5-9). Recherchiere vor S5-1 die aktuellen Import-Formate von ChatGPT,
Gemini, Mistral Le Chat und Open WebUI und dokumentiere sie mit Quellen in docs/adapter-ziele.md.
Nächtliche Neuprüfung als Cronjob. luibui audit. Badge-SVG. GitHub-Action und Forgejo/Codeberg-Action
plus pre-commit-Hook, die luibui scan lokal ausführen und SARIF hochladen. websecureaudit-Anbindung
für Remote-MCP-URLs über eine interne API (Schnittstelle zuerst als ADR vorschlagen und mit mir
abstimmen). Herkunftsabgleich Paket gegen Git-Tag.
- S5-8: app.luibui.com – Automatisierung pro Projekt: Git-Repository verbinden (GitHub, Codeberg,
  GitLab), Webhook-Secret pro Projekt, Signatur jedes Webhooks prüfen, Prüfung bei Push/Tag,
  CI-Snippet zum Kopieren und projektgebundenes API-Token.
- S5-9: Benachrichtigungen per Mail (über mittwald-Mail, kein US-Dienst): neue Befunde durch Push
  oder nächtliche Neuprüfung, Einspruchs-Entscheidung, Meldungen; Einstellungen im Konto.
Pro Task ein Commit, deployen, DoD prüfen.
```

---

## Sprint 6 – Sandbox (04.01. – 15.01.2027)

```
Setze Sprint 6 um (S6-1 bis S6-6) auf dem separaten Sandbox-vServer, den Len gebucht hat.
Schlage zuerst in einem ADR vor: gVisor oder nsjail, Netzwerk-Isolation, Ressourcenlimits, wie
Ergebnisse zurück zum Worker kommen, ohne dass der Sandbox-Host Zugangsdaten zur Hauptplattform hat.
Erst nach meiner Freigabe umsetzen. Köder-Zugangsdaten mit eindeutigen Markern pro Lauf, Erkennung
über Datei-Zugriffsprotokoll und Netzwerkversuche. Nur Pakete aus corpus/ und Pakete mit Einwilligung
des Autors ausführen. Pro Task ein Commit, DoD prüfen.
```

---

## Sprint 7 – Hosted MCP & Playground (18.01. – 29.01.2027)

```
Setze Sprint 7 um (S7-1 bis S7-3). Hosted MCP nur für Pakete mit Gesamt Grün oder Gelb, ausgehender
Netzverkehr nur zu im Manifest deklarierten Endpunkten, Ressourcenlimits und Ruhemodus. Playground
über LLM_BASE_URL, keine Speicherung von Chatinhalten. Automatisierte Prompt-Angriffstests (F6):
eine Liste von Testprompts, die das Paket zum Datenabfluss oder zur Anweisungs-Übernahme verleiten
sollen; Ergebnis als Befunde mit Nachweisgrad "im Test beobachtet". Pro Task ein Commit, DoD prüfen.
```

---

## Nützliche Einzel-Prompts

**Neue Regel hinzufügen**
```
Füge eine Regel für Prüfkatalog-ID <ID> hinzu: <Beschreibung>. ID nach Konvention LB-<ID>-<kurzname>,
Schwere <K/H/M/N>, mit mindestens zwei positiven und zwei negativen Testfällen (entschärft, CLAUDE.md
Regel 8), Fix-Text und Fix-Prompt. Benchmark danach ausführen und Änderung in docs/benchmark.md notieren.
```

**Fehlalarm aus Einspruch bearbeiten**
```
Einspruch zu Befund <ID> in Scan <Scan-ID>: <Begründung des Autors>. Prüfe, ob es ein Fehlalarm ist.
Wenn ja: Regel anpassen, den Fall als negativen Testfall aufnehmen, Benchmark ausführen. Wenn nein:
begründe in 3 Sätzen, warum der Befund bleibt.
```

**Wochenabschluss**
```
Prüfe die Definition of Done des aktuellen Sprints Punkt für Punkt, führe Tests und Benchmark aus,
prüfe RAM-Verbrauch auf dem Server und schreibe das Ergebnis mit offenen Punkten in docs/log.md.
```
