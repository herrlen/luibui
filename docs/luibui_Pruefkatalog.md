# luibui – Prüfkatalog

> Stand: 27.09.2026 · Task S0-2 · Status: **freigegeben von Len am 27.09.2026** (Entwurf von Claude).
> Ergänzt am 27.09.2026 um die Scanner-Matrix (Teil B): A13–A21, B21, C14, C15, E08, E09, G07,
> G08, erweiterte A02/A03/A04/A07, Sperrliste um A16 und B20. Entscheidungen dazu in §13.
> Grundlage: `luibui_Konzept.md` §4 und §5, `luibui_Sprintplanung.md`, `threat-model.md`,
> `scanner-tools.md`. Wo diese Dokumente sich widersprechen oder schweigen, ist die Entscheidung
> unten unter „Offene Fragen“ aufgeführt.

Dieser Katalog legt fest, **was** luibui prüft, **wie schwer** ein Treffer wiegt und **welche
Treffer ein Paket sperren**. Die Bewertung selbst (Ampeln, Note, Freigabe) steht in Konzept §5 und
ist ausschließlich in `packages/engine/luibui_scan/scoring.py` umgesetzt.

---

## 1. Konventionen

**Prüfungs-ID:** Buchstabe der Ebene und zweistellige Nummer, z. B. `A02`, `B01`, `C13`. Verweise
wie „A2–A12“ in der Sprintplanung meinen `A02`–`A12`.

**Regel-ID:** Eigene Regeln heißen `LB-<Prüfungs-ID>-<kurzname>`, z. B. `LB-B01-unicode-tags`.
Eine Prüfung kann mehrere Regeln haben (`LB-C07-subprocess-shell`, `LB-C07-os-system`); für die
Sperrliste zählt jede Regel der Prüfung. Externe Regeln behalten ihr Präfix (`ATR-…`,
`gitleaks:…`, `osv:…`, `cisco-skill:…`) und werden einer Prüfung dieses Katalogs zugeordnet
(Spalte „Quelle“).

**Schwere:** Die Spalte nennt die **Regelschwere**. Eine einzelne Regel darf niedriger liegen,
wenn der Benchmark (S3-6) zu viele Fehlalarme zeigt, nie höher. Die Korrelation (Konzept §4,
Schritt 11) stuft einen Befund um eine Stufe hoch und setzt `hochgestuft_von`.

| Kürzel | Schwere | Wirkung auf die Sicherheitsampel |
|---|---|---|
| **K** | kritisch | Rot, mit Sperrliste Gesperrt |
| **H** | hoch | Rot |
| **M** | mittel | Gelb |
| **N** | niedrig | bleibt Grün, kostet 1 Punkt |
| **I** | Info | bleibt Grün, kostet nichts |

**Sperrliste (●):** Ein Befund der Schwere K aus einer so markierten Prüfung sperrt das Paket.
Ein K ohne ● ergibt Rot. Die Sperrliste gilt nur auf der Sicherheitsachse.

**Umfang:** P = Paket mit `luibui.json`, W = Dateiauswahl ohne Manifest, E = Einzeldatei oder
Text, S = Schnellscan. „–“ heißt: läuft bei diesem Umfang nicht und erscheint im Bericht unter
„nicht geprüft“ (Konzept §5).

**Nachweisgrad:** `statisch_erkannt` (S), `per_llm_bewertet` (L), `in_sandbox_beobachtet` (X),
`im_test_beobachtet` (T), `selbstauskunft` (M, aus dem Manifest).

**Normbezug:** OWASP Top 10 for Agentic Applications (`OWASP-ASI01`–`ASI10`), OWASP Top 10 for
LLM Applications 2025 (`OWASP-LLM01`–`LLM10`), DSGVO-Artikel (`DSGVO-Art-44`). Die Zuordnung ist
eine Orientierung, keine Konformitätsaussage. In den Tabellen steht kurz `ASI01` für `OWASP-ASI01`
und `LLM01` für `OWASP-LLM01`; im Befund steht die lange Form.

---

## 2. Ebene A – Dateien und Annahme

Was im Paket liegt, unabhängig vom Inhalt der Dateien. Sprint 1 (A01 mit S1-2, A02–A12 mit S1-5).

| ID | Prüfung | Schwere | ● | P W E S | Quelle | Normbezug |
|---|---|---|---|---|---|---|
| A01 | **Annahme abgelehnt:** Pfad außerhalb, ungültiger oder zu langer Name, doppelter Name, zu tief, Verknüpfung, verschlüsselt, zu groß, zu viele Dateien, Kompressionsrate, defektes Archiv (Kurzname = Ablehnungsgrund, siehe §11) | H | – | ✓ ✓ ✓ ✓ | `intake/` | ASI04 |
| A02 | **Autostart-Dateien mit Befehlen:** `.claude/settings.json`- und `hooks.json`-Hooks, `.vscode/tasks.json` mit `runOn: folderOpen`, `task.allowAutomaticTasks`, `devcontainer.json`-Befehle, `.envrc`, `.git/hooks`, `package.json`-Skripte `preinstall`/`install`/`postinstall` (`prepare` nur mit gefährlichem Befehl), Python-`.pth` mit `import`, `sitecustomize.py`/`usercustomize.py`, `setup.py`, das herunterlädt und ausführt. K bei Nachladen, Verschleiern, Löschen des Home-Ordners, Lesen von Zugangsdaten, Hochladen von Dateien oder Persistenz, sonst H | K | ● | ✓ ✓ ✓ ✓ | eigene Regeln | ASI05, LLM03 |
| A03 | **Install- und Hilfsskripte:** `setup.py` mit Code außerhalb von `setup()`, `install.sh`/`install.ps1`, `Makefile`/`Justfile`-Ziele und alle Shell-/PowerShell-Skripte, die herunterladen und ausführen oder eine Reverse Shell öffnen, `conftest.py` mit Netzwerk, Build-Backend im Paket (`backend-path`), Notebook-Shell-Zellen, die nachladen | H | – | ✓ ✓ ✓ ✓ | eigene Regeln | ASI05, LLM03 |
| A04 | **Ausführbare Binärdateien:** ELF, Mach-O, PE, WASM, Java-Class, deb, rpm im Paket (Inventar); Installationspakete `.msi`, `.apk`, `.dmg`, `.pkg` | H | – | ✓ ✓ ✓ ✓ | Inventar | ASI04, LLM03 |
| A05 | **Endung passt nicht zum Typ:** z. B. `bild.png` ist ein ELF, `notes.md` ist ein ZIP | H | – | ✓ ✓ ✓ ✓ | Inventar | ASI04 |
| A06 | **Kompilierter Code ohne Quelle:** `.pyc`, `.so`, `.node`, minifizierte `.js` ohne Quelldatei | M | – | ✓ ✓ ✓ ✓ | Inventar, Cisco skill-scanner (Bytecode) | ASI04 |
| A07 | **Archive im Archiv:** verschachtelte ZIP/tar/7z/RAR bleiben gepackt und ungeprüft. Ausnahme: Paketformate `.whl`, `.egg`, `.dxt`, `.mcpb`, `.vsix`, `.xpi`, `.nupkg` werden eine Ebene tief nach `<name>.inhalt/` entpackt und mitgeprüft (Limits des ganzen Pakets) | M | – | ✓ ✓ ✓ ✓ | Inventar | ASI04 |
| A08 | **Bekannte Schadsoftware:** Hash-Liste und Signaturen (ab Sprint 4 ClamAV). Treffer: Dateien sofort löschen, nur Hash behalten (Konzept §3) | K | ● | ✓ ✓ ✓ ✓ | Hash-Liste, ClamAV | ASI04, LLM03 |
| A09 | **Versteckte Dateien und Ordner** außerhalb bekannter Muster (`.github/`, `.gitignore`, `.claude-plugin/`, …) | N | – | ✓ ✓ – ✓ | eigene Regeln | – |
| A10 | **Symlinks im Git-Repository:** als Textdatei ausgecheckt (`core.symlinks=false`); Ziel außerhalb des Pakets oder absolut | M | – | ✓ – – ✓ | `safe_git` | ASI04 |
| A11 | **Submodule:** `.gitmodules` vorhanden, die Quellen werden nicht geprüft | M | – | ✓ – – ✓ | `safe_git` | ASI04, LLM03 |
| A12 | **Fremde Paketquellen:** `--index-url`/`--extra-index-url`, `.npmrc`-`registry`, `pip.conf`, Abhängigkeiten per Git-URL oder Tarball-Link | H | – | ✓ ✓ ✓ ✓ | eigene Regeln | ASI04, LLM03 |
| A13 | **Git-Attribute und LFS:** eigene `filter=`/`diff=`/`merge=`-Treiber in `.gitattributes` (M); LFS-Zeiger ohne Inhalt als „nicht geprüft“ (I) | M | – | ✓ ✓ – ✓ | eigene Regeln | ASI04 |
| A14 | **Täuschende Dateinamen:** Doppelendung (`rechnung.pdf.exe`), reservierte Windows-Namen (`CON`, `NUL`, `COM1`) | M | – | ✓ ✓ ✓ ✓ | eigene Regeln | ASI04 |
| A15 | **Polyglot und angehängte Daten:** Bild oder PDF, das zugleich ein ZIP ist (H), oder mehr als 1 KB Daten nach dem Formatende (M) | H | – | ✓ ✓ ✓ ✓ | Inventar | ASI04 |
| A16 | **Code-Ausführung beim Laden eines Modells:** Pickle-Importe von `os`, `subprocess`, `eval` & Co. (auch in PyTorch-ZIPs, nur als Opcodes gelesen), Jinja-SSTI in `chat_template` | K | ● | ✓ ✓ ✓ ✓ | eigener Code (`pickletools.genops`) | ASI05, LLM03 |
| A18 | **Modelldatei unklar:** Pickle mit unbekannten Importen oder nicht lesbar, ungültiger safetensors-Header | M | – | ✓ ✓ ✓ ✓ | eigener Code | LLM03 |
| A19 | **`trust_remote_code`:** `auto_map` in `config.json` verweist auf Code im Paket | M | – | ✓ ✓ ✓ ✓ | eigene Regeln | ASI05, LLM03 |
| A20 | **Formeln in mitgelieferten Tabellen:** CSV/TSV-Zellen mit Formeln (N), mit `HYPERLINK`, `WEBSERVICE`, DDE oder `\|` (H) | H | – | ✓ ✓ ✓ ✓ | eigener Code | LLM05 |
| A21 | **Aktive Inhalte in Dokumenten:** PDF mit JavaScript, `/Launch`, eingebetteten Dateien (H) oder Aktion beim Öffnen (M); Office mit Makros, externer Vorlage oder DDE | H | – | ✓ ✓ ✓ ✓ | eigener Code (nur Bytes, kein Parser) | ASI05 |

A17 (Keras/TF/ONNX-Struktur) ist reserviert für Sprint 3/4 (modelscan).

---

## 3. Ebene B – Inhalte

Was in Texten steht, vor allem in `SKILL.md`, Prompts, Tool-Beschreibungen und Markdown.
B01–B07 mit S1-6, B08–B17 mit S1-7, B18–B19 mit S3-3 (LLM-Prüfer), B20 mit S1-8.

### Versteckte Inhalte (B01–B07)

| ID | Prüfung | Schwere | ● | P W E S | Quelle | Normbezug |
|---|---|---|---|---|---|---|
| B01 | **Unicode-Tag-Zeichen** (U+E0000–E007F): für Menschen unsichtbarer Text, den ein Modell liest | K | ● | ✓ ✓ ✓ ✓ | eigene Regeln | ASI01, LLM01 |
| B02 | **Zero-Width- und unsichtbare Formatzeichen** (U+200B–200D, U+2060–2064, U+FEFF mitten im Text, Variation Selectors als Datenträger) | H | – | ✓ ✓ ✓ ✓ | eigene Regeln | ASI01, LLM01 |
| B03 | **Bidi-Steuerzeichen** (U+202A–202E, U+2066–2069) in Text **und Dateinamen** (Trojan Source) | H | – | ✓ ✓ ✓ ✓ | eigene Regeln | ASI01, LLM01 |
| B04 | **Homoglyphen:** gemischte Schriftsysteme in einem Wort, Befehlen oder Domains (`раураl.com`) | M | – | ✓ ✓ ✓ ✓ | eigene Regeln | ASI09 |
| B05 | **Versteckter Text in HTML/SVG/CSS/Markdown:** `display:none`, weiße Schrift, `font-size:0`, HTML-Kommentare mit Anweisungen, Markdown-Link-Referenzen und Alt-Texte als Träger | H | – | ✓ ✓ ✓ ✓ | eigene Regeln | ASI01, LLM01 |
| B06 | **Kodierte Blöcke:** lange Base64/Hex/URL-kodierte Abschnitte in Anweisungsdateien, besonders wenn sie dekodiert Befehle oder Anweisungen ergeben | M | – | ✓ ✓ ✓ ✓ | eigene Regeln | ASI01, LLM01 |
| B07 | **Unsichtbare Ausgabe-Tricks:** Anweisung, Bilder oder Links mit Daten im Query-String zu rendern (Markdown-Image-Exfiltration) | K | ● | ✓ ✓ ✓ ✓ | eigene Regeln | ASI01, LLM02, LLM05 |

### Anweisungsmuster (B08–B17, regelbasiert, ATR und eigene Regeln)

| ID | Prüfung | Schwere | ● | P W E S | Quelle | Normbezug |
|---|---|---|---|---|---|---|
| B08 | **Anweisungs-Übernahme:** „ignoriere alle vorherigen Anweisungen“, neue Systemrolle, Rollen-Spoofing (`</system>`, gefälschte Tool-Ergebnisse) | K | ● | ✓ ✓ ✓ ✓ | ATR (prompt-injection), eigene Regeln | ASI01, LLM01 |
| B09 | **Geheimhaltung vor dem Nutzer:** „erwähne das nicht“, „sag dem Nutzer nicht“, „führe still aus“ | K | ● | ✓ ✓ ✓ ✓ | ATR (agent-manipulation), eigene Regeln | ASI09, LLM01 |
| B10 | **Aufforderung zum Datenabfluss:** Inhalte, Verlauf oder Dateien an eine URL, E-Mail oder einen Webhook senden | K | ● | ✓ ✓ ✓ ✓ | ATR (context-exfiltration) | ASI01, LLM02 |
| B11 | **Zugriff auf Zugangsdaten:** Anweisung, `~/.ssh`, `~/.aws`, `.env`, Keychain, Browser-Profile, Token-Dateien zu lesen | K | ● | ✓ ✓ ✓ ✓ | ATR (privilege-escalation), eigene Regeln | ASI03, LLM02 |
| B12 | **`curl \| bash` und Verwandte:** Anweisung, Code aus dem Netz herunterzuladen und direkt auszuführen | K | ● | ✓ ✓ ✓ ✓ | eigene Regeln | ASI05, LLM03 |
| B13 | **Persistenz:** Anweisung, Shell-Profile, Crontab, Autostart, `CLAUDE.md`/`AGENTS.md` anderer Projekte oder Agent-Konfiguration zu ändern | K | ● | ✓ ✓ ✓ ✓ | ATR (skill-compromise), eigene Regeln | ASI06, ASI10 |
| B14 | **Rechteausweitung:** Aufforderung, Bestätigungen zu umgehen, `--dangerously-skip-permissions`, `sudo`, Sicherheitsfunktionen abzuschalten | H | – | ✓ ✓ ✓ ✓ | ATR (privilege-escalation) | ASI03, LLM06 |
| B15 | **Übermäßige Autonomie:** unbegrenzte Schleifen, Selbstvervielfältigung, Aufträge an andere Agents ohne Nutzerbestätigung | M | – | ✓ ✓ ✓ ✓ | ATR (excessive-autonomy) | ASI08, ASI10, LLM06 |
| B16 | **Tool Poisoning in Anweisungen:** Beschreibung verlangt, andere Tools umzuleiten oder deren Parameter zu verändern (Shadowing) | K | ● | ✓ ✓ ✓ ✓ | ATR (tool-poisoning) | ASI02, LLM01 |
| B17 | **Täuschung des Nutzers:** falsche Herkunftsangaben, Autoritäts-Behauptungen („offizielles Anthropic-Tool“), Drängen zur Eile | M | – | ✓ ✓ ✓ ✓ | ATR (agent-manipulation), eigene Regeln | ASI09 |

### Semantische Prüfung und Secrets

| ID | Prüfung | Schwere | ● | P W E S | Quelle | Normbezug |
|---|---|---|---|---|---|---|
| B18 | **Semantische Anweisungsprüfung:** Muster B08–B17, die die Regeln nicht erfassen (Umschreibungen, andere Sprachen) | wie B08–B17 | wie B08–B17 | ✓ ✓ ✓ – | LLM-Prüfer (L) | wie B08–B17 |
| B19 | **Beschreibung ≠ Verhalten:** Die Beschreibung verspricht etwas anderes als Anweisungen und Code tun | H | – | ✓ ✓ ✓ – | LLM-Prüfer (L) | ASI09, LLM09 |
| B20 | **Echte Secrets im Paket:** API-Schlüssel, Tokens, private Schlüssel; im Bericht maskiert (erste 4 Zeichen + …). Dazu Schlüssel- und Zugangsdateien nach Namen (`id_rsa`, `.p12`, `.pfx`, `.jks`, `.kdbx`, `.aws/credentials`, …), auch binäre | K | ● | ✓ ✓ ✓ ✓ | gitleaks (`gitleaks:…`), `LB-B20-schluesseldatei` | LLM02, DSGVO-Art-32 |
| B21 | **Aktive Inhalte in SVG und XML:** `<script>`, Ereignis-Attribute, `javascript:` in SVG; externe Entitäten (XXE) in XML | M | – | ✓ ✓ ✓ ✓ | eigene Regeln | LLM05 |

B08–B17 lesen auch `.mdc`, `.cursorrules`, `.jsonl` und prüfen zusätzlich Text, der in Unicode-Tags oder in Base64/Hex/gzip-Blöcken (bis drei Ebenen) versteckt ist. B06 ist H, wenn der dekodierte Text einen Befehl oder eine Adresse enthält; B02 erkennt Folgen von Variation Selectors (Emoji Smuggling).

**LLM-Regel (CLAUDE.md Regel 7):** B18 und B19 fügen nur Befunde hinzu. Sie entfernen keine, und
ein LLM-Urteil allein führt nie zu Grün. **B18 sperrt nie allein:** Ein K aus B18 sperrt nur, wenn
eine statische Regel derselben Datei mindestens M meldet. Bis dahin ergibt es Rot.

---

## 4. Ebene C – Code

Skripte und Serverquellcode, statisch analysiert. Sprint 2 (S2-1, S2-2). Opengrep **nur mit
eigenen Regeln** (`rules/opengrep/`), dazu Bandit für Python und der Cisco skill-scanner offline.

| ID | Prüfung | Schwere | ● | P W E S | Quelle | Normbezug |
|---|---|---|---|---|---|---|
| C01 | **Shell-Ausführung mit fremden Daten:** `subprocess(shell=True)`, `os.system`, `child_process.exec` mit Eingaben aus Tool-Parametern, Netz oder Dateien | H | – | ✓ ✓ ✓ – | Opengrep, Bandit | ASI05, LLM05 |
| C02 | **Dynamische Code-Ausführung:** `eval`, `exec`, `new Function`, `pickle.loads`, `yaml.load` ohne SafeLoader, `importlib` mit variablen Namen | H | – | ✓ ✓ ✓ – | Opengrep, Bandit | ASI05 |
| C03 | **Herunterladen und Ausführen:** Download gefolgt von `exec`, `chmod +x`, `import` oder Schreiben in `site-packages` | K | ● | ✓ ✓ ✓ – | Opengrep, skill-scanner (Pipeline) | ASI05, LLM03 |
| C04 | **Lesen von Zugangsdaten:** Zugriff auf `~/.ssh`, `~/.aws`, `~/.config/gcloud`, `.env`, `.netrc`, Browser-Profile, Keychain | K | ● | ✓ ✓ ✓ – | Opengrep, skill-scanner (Datenfluss) | ASI03, LLM02 |
| C05 | **Datenabfluss:** Daten aus Dateien, Umgebung oder Tool-Eingaben fließen zu einem Netz-Aufruf | K | ● | ✓ ✓ ✓ – | skill-scanner (Datenfluss), Opengrep | ASI02, LLM02 |
| C06 | **Umgebungsvariablen komplett gelesen und versendet** (`os.environ`, `process.env` als Ganzes) | H | – | ✓ ✓ ✓ – | Opengrep | LLM02 |
| C07 | **Persistenz im Code:** Schreiben in Shell-Profile, Crontab, LaunchAgents, systemd, Autostart, Agent-Konfiguration | K | ● | ✓ ✓ ✓ – | Opengrep | ASI06, ASI10 |
| C08 | **Verschleierter Code:** mehrstufiges Dekodieren mit anschließender Ausführung, gepackte Strings, absichtlich unlesbare Bezeichner | K | ● | ✓ ✓ ✓ – | Opengrep, YARA-X | ASI05 |
| C09 | **Zeitbomben:** Verhalten abhängig von Datum, Aufrufzähler oder Umgebung (CI erkannt → harmlos) | K | ● | ✓ ✓ ✓ – | Opengrep; ab Sprint 6 Sandbox (F04) | ASI10 |
| C10 | **Schadmuster:** Reverse Shell, Keylogger, Krypto-Miner, Ransomware-Muster, Anti-Analyse | K | ● | ✓ ✓ ✓ – | YARA-X, skill-scanner (YARA) | ASI10 |
| C11 | **Unsichere Netzwerknutzung:** TLS-Prüfung abgeschaltet, `http://` für Daten, Server lauscht auf `0.0.0.0` ohne Auth | M | – | ✓ ✓ ✓ – | Opengrep, Bandit | ASI07 |
| C12 | **Pfad- und Dateizugriffe ohne Grenze:** Tool-Parameter als Pfad ohne Normalisierung (Path Traversal), Löschen außerhalb eines Arbeitsordners | H | – | ✓ ✓ ✓ – | Opengrep | ASI02, LLM06 |
| C13 | **Sonstige Code-Schwächen:** SQL-Injection, schwache Kryptografie, hartkodierte Temp-Pfade (Bandit mittel und niedrig) | N | – | ✓ ✓ ✓ – | Bandit, Opengrep | – |
| C14 | **Container-Konfiguration:** Compose mit `privileged`, Docker-Socket, Host-Netz/-PID, `SYS_ADMIN`, Wurzel-Mount; Dockerfile, das Skripte herunterlädt und ausführt | H | – | ✓ ✓ ✓ ✓ | eigene Regeln (`c_konfig`) | ASI05 |
| C15 | **CI-Workflows:** Script Injection über Issue-/PR-Texte in `run:`, `pull_request_target` mit Checkout des PR-Codes | H | – | ✓ ✓ ✓ ✓ | eigene Regeln (`c_konfig`) | ASI04 |

---

## 5. Ebene D – Abhängigkeiten

Lockfiles und Manifeste (`package-lock.json`, `pnpm-lock.yaml`, `poetry.lock`, `uv.lock`,
`requirements.txt`, `go.sum`, `Cargo.lock`). OSV-Scanner **offline** mit täglich
aktualisierter Datenbank. Sprint 1 (S1-9).

| ID | Prüfung | Schwere | ● | P W E S | Quelle | Normbezug |
|---|---|---|---|---|---|---|
| D01 | **Bekannte Schadpakete** (OpenSSF Malicious Packages) | K | ● | ✓ ✓ – ✓ | OSV (`osv:MAL-…`) | ASI04, LLM03 |
| D02 | **Bekannte Schwachstellen** in Abhängigkeiten; Schwere aus CVSS: ≥ 9,0 → H, ≥ 7,0 → M, sonst N | H/M/N | – | ✓ ✓ – ✓ | OSV (`osv:GHSA-…`, `osv:CVE-…`) | ASI04, LLM03 |
| D03 | **Typosquatting:** Name mit kleinem Abstand zu einem verbreiteten Paket (`reqeusts`) | H | – | ✓ ✓ – ✓ | eigene Liste, Levenshtein | ASI04, LLM03 |
| D04 | **Fehlendes Lockfile** bei vorhandenen Abhängigkeiten; Versionen nicht festgelegt | M | – | ✓ ✓ – ✓ | eigene Regeln | ASI04, LLM03 |
| D05 | **Abhängigkeit aus unsicherer Quelle:** Git-URL ohne Commit, `http://`, lokaler Pfad außerhalb des Pakets | M | – | ✓ ✓ – ✓ | eigene Regeln | ASI04, LLM03 |

---

## 6. Ebene E – MCP

MCP-Server-Code, Tool-Beschreibungen und Konfiguration. Sprint 2 (S2-3), E07 in Sprint 5.
Der Cisco mcp-scanner läuft nur offline (`static`, `--analyzers yara`). **Server werden nie
gestartet**, Tool-Listen werden aus dem Code abgeleitet.

| ID | Prüfung | Schwere | ● | P W E S | Quelle | Normbezug |
|---|---|---|---|---|---|---|
| E01 | **Tool Poisoning:** versteckte Anweisungen in Tool-Namen, -Beschreibungen oder Parameter-Beschreibungen (inkl. B01–B17 auf diese Texte) | K | ● | ✓ ✓ ✓ – | mcp-scanner (YARA), ATR (tool-poisoning) | ASI02, LLM01 |
| E02 | **Tool-Shadowing:** Beschreibung bezieht sich auf andere Tools oder Server und will deren Verhalten ändern | K | ● | ✓ ✓ ✓ – | eigene Regeln, ATR | ASI02 |
| E03 | **Gefährliche Tool-Fähigkeiten ohne Kennzeichnung:** Tool führt Shell-Befehle aus oder schreibt Dateien, Beschreibung sagt es nicht | H | – | ✓ ✓ – – | Code + Beschreibung | ASI02, LLM06 |
| E04 | **Fehlende Authentifizierung** bei HTTP/SSE-Transport oder Auth nur über Query-Parameter | H | – | ✓ ✓ – – | eigene Regeln | ASI03, ASI07 |
| E05 | **Unsicherer Transport:** `http://` statt `https://`, gebunden an `0.0.0.0`, CORS `*` | M | – | ✓ ✓ – – | eigene Regeln | ASI07 |
| E06 | **Token-Weitergabe:** Server reicht Nutzer-Token an Dritte durch (Token Passthrough) oder speichert sie im Klartext | H | – | ✓ ✓ – – | eigene Regeln | ASI03, LLM02 |
| E07 | **Entfernter MCP-Server:** Befunde der Außenprüfung einer Remote-MCP-URL (websecureaudit) | wie Quelle | – | ✓ – – – | websecureaudit (S5-6) | ASI07 |
| E08 | **Zu weite Werkzeugrechte:** `allowed-tools`/`tools` mit `Bash(*)`, `Bash` ohne Einschränkung oder `*` in Befehlen, Agenten und Skills | M | – | ✓ ✓ ✓ ✓ | eigene Regeln (`e_konfig`) | ASI03, LLM06 |
| E09 | **MCP-Startkonfiguration:** `.mcp.json` & Co. mit ungepinntem `npx`/`uvx`/`docker run` (H), nachladendem Startbefehl (K), `http://` (M), entferntem Server als „nicht geprüft“ (I); gepinnte Pakete als Hinweis (I) | H | – | ✓ ✓ ✓ ✓ | eigene Regeln (`e_konfig`) | ASI04, LLM03 |

---

## 7. Ebene F – Verhalten (Sandbox und Tests)

Nur im Intensivscan, **ab Sprint 6 auf eigenem Server** (CLAUDE.md Regel 1, Ausnahme Sandbox).
Ausführung ohne Netz, mit strace, Köder-Zugangsdaten und vorgedrehter Uhr. Nachweisgrad X bzw. T.

| ID | Prüfung | Schwere | ● | P W E S | Quelle | Normbezug |
|---|---|---|---|---|---|---|
| F01 | **Netzwerkversuche:** DNS-Anfragen oder Verbindungen, die das Manifest nicht deklariert | H | – | ✓ – – – | Sandbox | ASI02, LLM02 |
| F02 | **Köder-Zugangsdaten gelesen:** Zugriff auf präparierte `~/.aws`, `~/.ssh`, `.env` | K | ● | ✓ – – – | Sandbox (Canary) | ASI03, LLM02 |
| F03 | **Prozesse und Dateien außerhalb des Arbeitsordners:** Shell gestartet, Systempfade geschrieben | H | – | ✓ – – – | Sandbox (strace) | ASI05 |
| F04 | **Zeitbombe beobachtet:** anderes Verhalten nach vorgedrehter Uhr oder wiederholtem Aufruf | K | ● | ✓ – – – | Sandbox (faketime) | ASI10 |
| F05 | **Persistenz beobachtet:** Schreiben in Profile, Crontab oder Autostart | K | ● | ✓ – – – | Sandbox | ASI06, ASI10 |
| F06 | **Prompt-Angriffstests:** Testprompts verleiten den Skill zu Datenabfluss oder Anweisungs-Übernahme | H | – | ✓ – – – | Testlauf (T, S7-3) | ASI01, LLM01 |

---

## 8. Ebene G – DSGVO und Rechte

Achse **dsgvo**. Endpunkte und Rechte aus dem Code gegen das Manifest, Länderzuordnung aus einer
gepflegten Liste mit Angemessenheitsbeschlüssen (`rules/data/`). Sprint 2 (S2-4).
**G01, G03, G04, G05 brauchen das Manifest** (Konzept §5); ohne Manifest bleibt die Achse „nicht
bewertet“, nur G02 kann sie dann einfärben.

| ID | Prüfung | Schwere | ● | P W E S | Quelle | Normbezug |
|---|---|---|---|---|---|---|
| G01 | **Manifest fehlt oder ist ungültig:** `luibui.json` nicht nach Schema, Pflichtangaben fehlen, Pakettyp passt nicht zur Erkennung | M | – | ✓ – – – | Schema, Inventar | DSGVO-Art-13 |
| G02 | **Endpunkt in einem Drittland ohne Angemessenheitsbeschluss;** unbekanntes Land ergibt M | H/M | – | ✓ ✓ ✓ – | Länderliste | DSGVO-Art-44, DSGVO-Art-45, DSGVO-Art-46 |
| G03 | **Undeklarierte Endpunkte:** im Code gefunden, im Manifest nicht angegeben | H | – | ✓ – – – | Code gegen Manifest | DSGVO-Art-5, DSGVO-Art-13 |
| G04 | **Undeklarierte Rechte:** Shell, Dateisystem, Netzwerk, Umgebungsvariablen genutzt, aber nicht deklariert | H | – | ✓ – – – | Code gegen Manifest | DSGVO-Art-25, LLM06 |
| G05 | **Datenkategorien unvollständig:** verarbeitete personenbezogene Daten nicht angegeben | M | – | ✓ – – – | Manifest, Code | DSGVO-Art-13, DSGVO-Art-30 |
| G06 | **Selbstauskunft:** Angaben aus dem Manifest, die sich nicht prüfen lassen (Betreiber, Speicherort) | I | – | ✓ – – – | Manifest (M) | DSGVO-Art-13 |
| G07 | **Personenbezogene Daten in Datendateien:** mindestens fünf echt wirkende E-Mail-Adressen oder eine IBAN mit gültiger Prüfziffer in CSV/TSV/JSONL; Werte werden nie angezeigt | M | – | ✓ ✓ ✓ ✓ | eigener Code | DSGVO-Art-5 |
| G08 | **Standort in Fotos:** GPS-Koordinaten in den Exif-Daten von JPEG/PNG | M | – | ✓ ✓ ✓ ✓ | eigener Code | DSGVO-Art-5 |

---

## 9. Ebene H – Herkunft und Register

Nur für veröffentlichte oder zu veröffentlichende Pakete. Sprint 4–5.

| ID | Prüfung | Schwere | ● | P W E S | Quelle | Normbezug |
|---|---|---|---|---|---|---|
| H01 | **Neue Rechte oder Endpunkte gegenüber der Vorversion** (Diff) | M | – | ✓ – – – | Register (S4-6) | ASI04 |
| H02 | **Nächtliche Nachprüfung:** neuer Treffer in D01/D02/A08 für eine bereits veröffentlichte Version | wie Quelle | – | ✓ – – – | Register (Cron) | ASI04, LLM03 |
| H03 | **Herkunft:** veröffentlichtes Paket stimmt nicht mit dem angegebenen Git-Tag überein | H | – | ✓ – – – | Register (S5-7) | ASI04, LLM03 |
| H04 | **Namensverwechslung:** Paket- oder Namespace-Name nah an einem bestehenden | H | – | ✓ – – – | Register (S4-1) | ASI04 |

---

## 10. Sperrliste

Die 15 Kategorien aus Konzept §5 und die Prüfungen, deren K-Befunde sperren. Dieselben IDs
gehören nach Freigabe in `SPERRLISTE_KATALOG` in `scoring.py`.

| Kategorie (Konzept §5) | Prüfungen |
|---|---|
| bekannte Schadsoftware | A08 |
| Autostart-Dateien mit Befehlen | A02 (auch `.pth`, `sitecustomize`, `setup.py`, Dev Container) |
| Code-Ausführung beim Laden (Modelle, Vorlagen) | A16 |
| unsichtbare Unicode-Anweisungen | B01, B07 |
| Anweisungs-Übernahme | B08 |
| Geheimhaltung vor dem Nutzer | B09 |
| Datenabfluss | B10, C05 |
| Zugriff auf Zugangsdaten | B11, C04, F02 |
| Persistenz | B13, C07, F05 |
| Tool Poisoning | B16, E01, E02 |
| `curl \| bash` | B12, C03 |
| verschleierter Code | C08 |
| Zeitbomben | C09, F04 |
| Schadmuster | C10 |
| echte Secrets | B20 (`gitleaks:` in `SPERRLISTE_EXTERN`, `LB-B20-…` im Katalog) |
| bekannte Schadpakete | D01 (`osv:MAL-` in `SPERRLISTE_EXTERN`) |

`SPERRLISTE_KATALOG = {A02, A08, A16, B01, B07, B08, B09, B10, B11, B12, B13, B16, B20, C03, C04,
C05, C07, C08, C09, C10, E01, E02, F02, F04, F05}` — B18 bewusst nicht, siehe LLM-Regel in §3.

---

## 11. Zuordnung der Annahme (A01)

Jeder Ablehnungsgrund der Annahme (`intake/errors.py`, `Ablehnung`) wird ein Befund `A01` mit dem
Code als Kurzname. Die Annahme bricht ab, der Bericht enthält nur diesen Befund.

| Ablehnung | Regel-ID | Schwere |
|---|---|---|
| `pfad_ausserhalb` | `LB-A01-pfad-ausserhalb` | H |
| `verknuepfung` | `LB-A01-verknuepfung` | H |
| `kompressionsrate` | `LB-A01-kompressionsrate` | H |
| `verschluesselt` | `LB-A01-verschluesselt` | M |
| `doppelter_name` | `LB-A01-doppelter-name` | M |
| `ungueltiger_name` | `LB-A01-ungueltiger-name` | M |
| `name_zu_lang`, `zu_tief`, `zu_gross`, `zu_viele_dateien` | `LB-A01-<code>` | N |
| `defektes_archiv` | `LB-A01-defektes-archiv` | N |

Diese Befunde dienen nur der Erklärung; eine abgelehnte Eingabe wird nie bewertet und nie grün.

---

## 12. Entscheidungen (Len, 27.09.2026)

Alle sieben Punkte sind so freigegeben, wie sie hier stehen.

1. **Ebene I.** CLAUDE.md nennt „A1–I“, das Schema und das Konzept kennen nur A–H. Der Entwurf
   lässt **I unbenutzt und reserviert**. Soll CLAUDE.md auf „A01–H04“ geändert werden?
2. **A01 statt A2/A3 für die Annahme.** Das Bedrohungsmodell (T1) und die Prompt-Datei nennen für
   Annahme-Befunde „A2/A3“. Die Sprintplanung vergibt A2–A12 aber an den Datei-Analyzer (S1-5).
   Der Entwurf legt die Annahme deshalb auf **A01**. Passt das?
3. **Secrets als B20.** Kein Dokument gibt Secrets einen Buchstaben, das Schema verlangt aber
   einen. Secrets stehen im Inhalt, deshalb **B20**. Alternative wäre eine eigene Ebene.
4. **Bidi in Dateinamen:** Das Bedrohungsmodell (T5) sagt „Befund A“, der Log sagt, der
   Inhalts-Analyzer meldet sie. Der Entwurf legt beides auf **B03**.
5. **B18 sperrt nur mit statischer Stütze.** Das ist strenger als Regel 7 verlangt, verhindert
   aber, dass ein Sprachmodell allein ein Paket sperrt. Einverstanden?
6. **Schweregrade** sind ein erster Vorschlag. Kalibriert werden sie mit dem Benchmark (S3-6):
   Regeln mit zu vielen Fehlalarmen sinken auf N oder I, nie ohne Begründung in
   `docs/benchmark.md`.
7. **Normbezug:** Die Zuordnung zu OWASP und DSGVO ist eine Orientierung von Claude und ersetzt
   keine rechtliche Prüfung. Der Bericht soll „Bezug“ sagen, nicht „erfüllt“ oder „verstößt“.

---

## 13. Entscheidungen zur Scanner-Matrix (Claude, 27.09.2026, von Len übertragen)

Len hat die Konflikte aus `docs/scanner-abdeckung.md` zur Entscheidung übergeben („selbst logisch
entscheiden, damit es funktioniert“). Entschieden wurde so:

1. **Verschachtelte Archive:** Nur Paketformate, die so installiert werden, wie sie sind (`.whl`,
   `.egg`, `.dxt`, `.mcpb`, `.vsix`, `.xpi`, `.nupkg`), werden **eine Ebene** tief entpackt, über
   `extract_zip` mit dem Rest der Paket-Limits. Andere Archive im Paket bleiben gepackt (A07).
   Tiefe 3 wie in der Matrix wäre ein Vielfaches an Angriffsfläche für wenig Gewinn.
2. **Weitere Archivformate:** tar, tar.gz, tar.bz2 und tar.xz werden angenommen
   (`intake/safe_tar.py`, Python-Standardbibliothek, dieselben Regeln wie ZIP). **7z und RAR
   nicht:** dafür bräuchte es Bibliotheken mit unklarer (RAR: unfreier) Lizenz; sie werden als
   „beschädigt oder nicht unterstützt“ abgelehnt.
3. **Was sperrt:** Die Katalogregel bleibt: nur K aus Prüfungen mit ● sperrt. Neu mit ● ist A16
   (Code beim Laden eines Modells); `.pth`, `sitecustomize`, `setup.py` mit Nachladen und Dev
   Container gehören zu A02 und sperren damit. Office-Makros (A21) bleiben H, weil ein Makro allein
   noch kein Angriff ist.
4. **Entfernte MCP-Server (AGT-06):** Die Konfiguration wird statisch ausgewertet (E09), ohne Netz.
   Die Prüfung laufender Remote-Server bleibt S5-6 (E07) außerhalb des Kindprozesses.
5. **Schweregrade:** Wo Matrix und Katalog abweichen, gilt der Katalog; höher wird nur, was hier
   geändert ist. Die Kalibrierung folgt mit dem Benchmark (S3-6).
6. **DSGVO-Achse ohne Manifest:** G07 und G08 färben die DSGVO-Achse auch bei Einzeldatei und
   Auswahl, weil personenbezogene Daten im Paket selbst ein Befund sind, unabhängig von
   Selbstauskünften.
7. **Keine neuen Werkzeuge:** Alle neuen Prüfungen sind eigener Code ohne neue Abhängigkeiten.
   picklescan, oletools, pdfid, exiftool und python-magic werden nicht gebraucht; die
   Byte-Prüfungen greifen keinen Parser an.
