# luibui – Scanner-Matrix

> Stand: 27.09.2026 · Gehört zu `luibui_Konzept.md`, `luibui_Pruefkatalog.md`, `CLAUDE.md`
> Grundregel: **Scanner nach Inhalt (Magic Bytes) wählen, nie nach Dateiendung.** Alle Werkzeuge laufen offline auf mittwald.

Spalten: Schnellscan = luibui.com ohne Anmeldung (≤ 2 MB, ohne Gewähr) · Intensivscan = app.luibui.com · Schwere K/H/M/N/I laut Konzept §5 · Priorität P1 = vor Launch 20.11.2026.

## Annahme & Archive

| ID | Dateien / Muster | Erkennung | Risiko | Prüfung | Werkzeug | Ebene | Schnellscan | Intensivscan | Ampel-Regel | Sprint | Priorität |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ARC-01 | .zip .tar .tar.gz .tgz .7z .rar .gz .bz2 .xz | Magic Bytes | Zip-Slip, Zip-Bombe, Symlinks/Hardlinks, verschachtelte oder verschlüsselte Archive | Pfade (kein .., keine absoluten Pfade), Kompressionsrate, Tiefe ≤ 3, Dateianzahl, entpackte Größe, Links, Verschlüsselung → Abbruch vor dem Entpacken | eigener Entpacker (zipfile/tarfile mit filter='data') | Annahme | Ja (≤ 2 MB) | Ja | Verstoß = Annahme abgelehnt, Befund H | S1 | P1 |
| ARC-02 | Git-URL, .gitmodules, .gitattributes, LFS-Pointer | Clone --depth 1, ohne Hooks, ohne Submodule | Filter-/Diff-Treiber führen Befehle aus, Submodule ziehen fremde Repos, LFS-Pointer ohne Inhalt | filter=/diff=/merge= in .gitattributes, Submodule auflisten (nicht klonen), LFS-Pointer als 'nicht geprüft' markieren | eigener Code | Annahme / A | Ja | Ja | filter-Treiber → M; Submodule/LFS → I mit Hinweis 'nicht geprüft' | S1 | P1 |
| ARC-03 | alle Dateinamen und Pfade | Pfadanalyse | Doppelendung (rechnung.pdf.exe), Bidi-Zeichen im Namen, versteckte Dateien, reservierte Windows-Namen, überlange Pfade | Namensregeln, Unicode-Prüfung auf Pfaden | eigener Code | A | Ja | Ja | Bidi im Dateinamen → H; Doppelendung → M; versteckte Datei → I | S1 | P1 |
| INV-01 | alle Dateien | Magic Bytes vs. Endung | Getarnte Dateien, Polyglots (z. B. PNG + ZIP), falsche Endung umgeht Prüfung | Echten Typ bestimmen, danach Scanner nach Inhalt wählen (nie nach Endung); Anhang nach Dateiende erkennen | python-magic / libmagic | Inventar | Ja | Ja | Endung ≠ Inhalt → M; Polyglot → H | S1 | P1 |
| MAL-01 | alle Dateien | SHA-256, Signaturen | Bekannte Schadsoftware | Hash gegen eigene Blockliste; YARA eigene Regeln; ClamAV ab S4 | Blockliste, YARA, ClamAV | A | Ja (Hash, YARA) | Ja (+ ClamAV) | Treffer → K gesperrt; Datei sofort löschen, nur Hash behalten | S1 / S4 | P1 |

## Agent- & Skill-Dateien

| ID | Dateien / Muster | Erkennung | Risiko | Prüfung | Werkzeug | Ebene | Schnellscan | Intensivscan | Ampel-Regel | Sprint | Priorität |
|---|---|---|---|---|---|---|---|---|---|---|---|
| AGT-01 | SKILL.md, CLAUDE.md, AGENTS.md, GEMINI.md, .cursorrules, .cursor/rules/*.mdc, .windsurfrules, .github/copilot-instructions.md, GPT-Anweisungen, System-Prompts | Dateiname + Frontmatter | Prompt Injection, Übernahme von Anweisungen, Geheimhaltung vor dem Nutzer, Datenabfluss über Markdown-Bilder/Links | Regeln auf Anweisungsmuster, URLs mit Datenparametern, Aufforderung zu Shell/Netzwerk; ab S3 semantisch per LLM | ATR-Regeln, eigene Regeln (YAML), LLM-Prüfer (mittwald) | B | Ja (nur Regeln) | Ja (+ LLM) | Übernahme/Geheimhaltung/Datenabfluss → K gesperrt; verdächtige Formulierung → M | S1 (LLM S3) | P1 |
| AGT-02 | alle Textdateien | Zeichenanalyse | Unsichtbare Anweisungen: Unicode-Tags (U+E0000–E007F), Zero-Width, Bidi-Overrides, Variation Selectors, Homoglyphen | Zeichen finden, Tag-Zeichen dekodieren und den Klartext erneut prüfen | eigener Code | B | Ja | Ja | dekodierbare Tag-Anweisung → K gesperrt; Bidi → H; einzelnes Zero-Width → N | S1 | P1 |
| AGT-03 | alle Textdateien | Entropie + Muster | Versteckte Nutzlast in Base64, Hex, gzip+Base64, ROT13 | Blöcke > 200 Zeichen dekodieren und rekursiv prüfen (max. 3 Stufen) | eigener Code | B | Ja | Ja | dekodiert Befehl/URL/Anweisung → H; sonst I | S1 | P1 |
| AGT-04 | .claude/commands/*.md, .claude/agents/*.md, *.prompt.md, commands/ und agents/ in Plugins | Pfad + Frontmatter | Wie AGT-01, dazu zu weite Werkzeugrechte | allowed-tools/tools prüfen (z. B. Bash ohne Einschränkung), Anweisungen wie AGT-01 | eigene Regeln | B / E | Ja | Ja | Bash(*) oder alle Tools → M; Rest wie AGT-01 | S1 | P1 |
| AGT-05 | .claude/settings.json, .claude/settings.local.json, hooks/hooks.json (Plugins), .cursor/hooks.json | JSON-Schema | Hooks führen Shell-Befehle automatisch bei Ereignissen aus | Jeden Hook-Befehl auf Netzwerk, Löschen, Zugriff auf ~/.ssh, ~/.aws, Browser-Profile, Persistenz prüfen | eigene Regeln | A | Ja | Ja | Hook mit Netzwerk/Löschen/Zugangsdaten → K gesperrt; jeder andere Hook → M | S1 | P1 |
| AGT-06 | .mcp.json, mcp.json, .cursor/mcp.json, .vscode/mcp.json, claude_desktop_config.json | JSON-Schema | Startbefehle holen fremden Code (npx -y, uvx, docker run), Remote-Server in Drittländern, Secrets in env | command/args/env/url auswerten; Paketnamen an D übergeben; Remote-URL an websecureaudit (TLS, Header) und Länderzuordnung | eigene Regeln, websecureaudit (intern) | E / DSGVO | Ja | Ja | curl\|sh oder ungepinntes Paket aus fremder Quelle → H; http:// → M; Drittland unbekannt → DSGVO gelb | S1 / S2 | P1 |
| AGT-07 | .claude-plugin/plugin.json, marketplace.json, manifest.json (.dxt/.mcpb), openapi.yaml/json (GPT Actions), ai-plugin.json, luibui.json | Schema-Validierung | Zu weite Rechte, fremde Quellen, Manifest passt nicht zum Code | Schema prüfen; deklarierte Endpunkte/Rechte gegen Code abgleichen | eigene Regeln, JSON-Schema | E / DSGVO | Nein | Ja | undeklarierter Endpunkt → DSGVO rot; Rechte zu weit → M | S2 | P1 |
| AGT-08 | Tool-Definitionen in MCP-Servern (description, inputSchema, Prompts, Resources) | AST / JSON | Tool Poisoning, Tool Shadowing, Beschreibung ≠ Verhalten | Anweisungen an das Modell in Beschreibungen, Verweise auf andere Tools, Abgleich Beschreibung ↔ Code (LLM ab S3) | Cisco mcp-scanner (offline), ATR, LLM-Prüfer | E | Nein | Ja | Anweisung im Tool-Text → K gesperrt; Abweichung Beschreibung ↔ Code → H | S2 (LLM S3) | P1 |
| AGT-09 | .dxt, .mcpb, .vsix, .crx, .xpi | Magic (ZIP) | Paketierte Erweiterungen mit ausführbarem Server | Wie ARC-01 entpacken, Inhalt rekursiv mit allen Zeilen prüfen | eigener Entpacker | A | Ja | Ja | wie Inhalt | S1 | P2 |
| AGT-10 | Open-WebUI-Tools/-Functions (.py mit Frontmatter 'requirements:') | Frontmatter | Pakete werden beim Laden automatisch installiert | requirements auslesen, an D übergeben; Code wie COD-01 | eigene Regeln + OSV | A / D | Ja | Ja | Schadpaket → K; ohne Version → M | S1 | P2 |

## Code & Skripte

| ID | Dateien / Muster | Erkennung | Risiko | Prüfung | Werkzeug | Ebene | Schnellscan | Intensivscan | Ampel-Regel | Sprint | Priorität |
|---|---|---|---|---|---|---|---|---|---|---|---|
| COD-01 | .py, .pyw | Magic + Endung | eval/exec, Shell-Aufrufe mit Eingaben, Zugriff auf Zugangsdaten, Datenabfluss, Verschleierung | Musterregeln + Datenfluss (Quelle Zugangsdaten → Senke Netzwerk) | Bandit, Opengrep (eigene Regeln), Cisco skill-scanner | C | Nein | Ja | Zugangsdaten + Netzwerk → K gesperrt; shell=True mit Eingabe → H; eval → M | S2 | P1 |
| COD-02 | .ipynb | JSON (nbformat) | Code-Zellen, !pip/%%bash-Magics, Secrets und Personendaten in gespeicherten Ausgaben | Zellen extrahieren → COD-01/COD-04; Ausgaben → Secrets und PII | nbformat, gitleaks, eigene Regeln | C / Secrets | Ja (Secrets) | Ja | Secret in Ausgabe → K; !curl\|sh → K; PII in Ausgabe → DSGVO gelb | S2 | P2 |
| COD-03 | .js .mjs .cjs .ts .tsx | Magic + Endung | child_process, eval(atob()), dynamische Imports von URLs, Verschleierung | Musterregeln + Datenfluss | Opengrep (eigene Regeln), Cisco skill-scanner | C | Nein | Ja | verschleierter Code → K gesperrt; child_process mit Eingabe → H | S2 | P1 |
| COD-04 | .sh .bash .zsh .ps1 .psm1 .bat .cmd | Shebang + Endung | curl\|sh, base64 -d\|sh, rm -rf ~, IEX(New-Object Net.WebClient), Persistenz (crontab, Autostart) | Musterregeln | eigene Regeln (Regex/Opengrep) | C | Ja (Muster) | Ja | curl\|sh, IEX-Download, Persistenz → K gesperrt; sonst nach Muster | S1 | P1 |
| COD-05 | *.pth (Python), sitecustomize.py, usercustomize.py, conftest.py | Dateiname + Inhalt (.pth ≠ PyTorch per Magic) | Code läuft automatisch beim Python-Start oder bei Tests | import-Zeilen in .pth, Seiteneffekte in conftest | eigene Regeln | A | Ja | Ja | .pth mit import → K gesperrt; conftest mit Netzwerk → H | S1 | P1 |
| COD-06 | setup.py, pyproject.toml (build-backend), package.json (preinstall/install/postinstall/prepare), Makefile, Justfile, .envrc | Dateiname | Code läuft bei Installation oder beim Betreten des Ordners | Install-Hooks und Build-Backends auswerten, Befehle wie COD-04 prüfen | eigene Regeln | A | Ja | Ja | Install-Hook mit Netzwerk/Shell → K gesperrt; jeder Install-Hook → M | S1 | P1 |
| COD-07 | .vscode/tasks.json (runOn: folderOpen), .vscode/settings.json, .devcontainer/devcontainer.json (initializeCommand, postCreateCommand), .idea/ | Pfad | Ausführung beim Öffnen des Ordners im Editor | Autostart-Felder auswerten, Befehle wie COD-04 prüfen | eigene Regeln | A | Ja | Ja | folderOpen-Task oder initializeCommand mit Befehl → K gesperrt; sonst M | S1 | P1 |
| COD-08 | Dockerfile, Containerfile, docker-compose.yml | Dateiname | privileged, docker.sock-Mount, curl\|sh im Build, Host-Netzwerk | Regeln auf Compose und Dockerfile | hadolint, eigene Regeln | C | Nein | Ja | docker.sock / privileged → H; curl\|sh → H | S2 | P2 |
| COD-09 | .github/workflows/*.yml, .gitlab-ci.yml, .forgejo/workflows/*.yml | Pfad | pull_request_target mit fremdem Code, Script-Injection über ${{ github.event.* }}, ungepinnte Actions | Workflow-Regeln | zizmor, eigene Regeln | C | Nein | Ja | pull_request_target + Checkout PR-Code → H; Injection → H; ungepinnt → N | S2 | P2 |
| COD-10 | .pyc, __pycache__/, .class, .jar, .wasm | Magic | Nicht lesbarer Code ohne Quelle | Bytecode ohne passende Quelldatei markieren | Inventar, YARA, ClamAV (S4) | A | Ja | Ja | Bytecode ohne Quelle → H; mit Quelle → I | S1 | P2 |

## Abhängigkeiten

| ID | Dateien / Muster | Erkennung | Risiko | Prüfung | Werkzeug | Ebene | Schnellscan | Intensivscan | Ampel-Regel | Sprint | Priorität |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DEP-01 | requirements*.txt, pyproject.toml, poetry.lock, uv.lock, Pipfile(.lock), setup.cfg | Dateiname | Bekannte Schadpakete, CVEs, Typosquatting, fehlende Versionen | OSV-Abgleich offline, Namensähnlichkeit zu Top-Paketen | OSV-Scanner + Offline-DB, eigene Typo-Liste | D | Ja (bei Git) | Ja | Schadpaket (MAL-…) → K gesperrt; kritische CVE → H; Typosquatting → H; ohne Lockfile → N | S1 | P1 |
| DEP-02 | package.json, package-lock.json, pnpm-lock.yaml, yarn.lock | Dateiname | wie DEP-01 | wie DEP-01 | OSV-Scanner + Offline-DB | D | Ja (bei Git) | Ja | wie DEP-01 | S1 | P1 |
| DEP-03 | .npmrc, .yarnrc.yml, pip.conf, pip.ini, uv.toml, --index-url/--extra-index-url in requirements | Dateiname + Inhalt | Fremde Paketquellen (Dependency Confusion), http-Quellen, Tokens in Konfigdateien | Quellen auswerten, Tokens an Secrets übergeben | eigene Regeln | D | Ja | Ja | extra-index-url / http-Quelle → H; Token → K (Secret) | S1 | P1 |
| DEP-04 | git+https://, http-Tarballs, lokale Pfade in Abhängigkeiten | Inhalt | Code aus beliebiger Quelle ohne Prüfsumme | Direkt-URLs ohne Hash markieren | eigene Regeln | D | Ja | Ja | URL ohne Hash → M | S1 | P2 |

## Secrets

| ID | Dateien / Muster | Erkennung | Risiko | Prüfung | Werkzeug | Ebene | Schnellscan | Intensivscan | Ampel-Regel | Sprint | Priorität |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SEC-01 | .env*, *.pem, *.key, id_rsa*, id_ed25519*, *.p12, *.pfx, .netrc, .pypirc, credentials.json, service-account*.json, *.kdbx | Dateiname | Zugangsdaten werden mit veröffentlicht | Namensliste + Inhalt prüfen (Platzhalter vs. echt) | gitleaks, eigene Namensliste | Secrets | Ja | Ja | echter Schlüssel → K gesperrt; Platzhalter/Beispiel → I | S1 | P1 |
| SEC-02 | alle Textdateien inkl. Notebooks, Configs, Logs | Muster + Entropie | API-Keys, Tokens, Passwörter im Inhalt | Regeln + Entropie; im Bericht maskiert (erste 4 Zeichen + …); keine Online-Verifizierung | gitleaks (TruffleHog nur mit --no-verification) | Secrets | Ja | Ja | wie SEC-01 | S1 | P1 |

## Modelldateien

| ID | Dateien / Muster | Erkennung | Risiko | Prüfung | Werkzeug | Ebene | Schnellscan | Intensivscan | Ampel-Regel | Sprint | Priorität |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MOD-01 | .pkl .pickle .joblib .dill .ckpt .pt .pth(PyTorch) .bin(PyTorch) .pdparams .nemo .mar .npy/.npz | Magic (Pickle-Protokollbyte 0x80, ZIP mit data.pkl) | Pickle führt beim Laden beliebigen Code aus | Opcode-Analyse ohne Laden: GLOBAL/REDUCE auf os, subprocess, builtins, socket, runpy … | picklescan, modelscan, fickling | A (neu: Modelle) | Ja (Opcode-Scan) | Ja | gefährlicher Import → K gesperrt; unbekannte Globals → M; nur Tensoren → N + Hinweis 'safetensors nutzen' | S2 | P2 |
| MOD-02 | .h5 .keras, SavedModel (.pb), .tflite | Magic | Lambda-Layer mit eingebettetem Python-Bytecode, Custom Objects, Datei-Ops im Graph | Struktur lesen ohne Laden | modelscan | A | Nein | Ja | Lambda-Layer → H; Datei-Ops → H | S3 | P3 |
| MOD-03 | .onnx | Magic (Protobuf) | external_data mit Pfad-Traversal, Custom-Op-Domains | Protobuf lesen ohne Ausführung, Pfade prüfen | eigener Code (onnx), modelscan | A | Nein | Ja | ../ oder absoluter Pfad → H; Custom-Op → M | S3 | P3 |
| MOD-04 | .gguf | Magic 'GGUF' | Jinja-Chat-Template mit Template-Injection, manipulierte Header | Header parsen, tokenizer.chat_template extrahieren und wie AGT-01 + SSTI prüfen | eigener Code (gguf-Header) | A / B | Nein | Ja | __class__/__globals__/import im Template → K; Anweisungen im Template → M | S3 | P3 |
| MOD-05 | .llamafile | Magic (APE/ELF) | Ist eine ausführbare Datei | wie BIN-01 | Inventar | A | Ja | Ja | → H, nicht veröffentlichbar | S1 | P3 |
| MOD-06 | .safetensors | Magic (Header-Länge + JSON) | Sicheres Format; Risiko nur durch kaputte Header oder Text in __metadata__ | Header-JSON und Offsets validieren, __metadata__ wie AGT-01 | eigener Code | A / B | Ja | Ja | ungültiger Header → M; sonst grün | S2 | P3 |
| MOD-07 | config.json (auto_map), tokenizer_config.json (chat_template), generation_config.json, modeling_*.py | Dateiname + Schlüssel | trust_remote_code führt Repo-Code aus; Template-Injection im chat_template | auto_map → referenzierten Code mit COD-01 prüfen (Korrelation); chat_template wie MOD-04 | eigene Regeln | B / C | Ja | Ja | auto_map → M (+ Befunde im Code hochstufen); SSTI → K | S2 | P2 |

## Daten & DSGVO

| ID | Dateien / Muster | Erkennung | Risiko | Prüfung | Werkzeug | Ebene | Schnellscan | Intensivscan | Ampel-Regel | Sprint | Priorität |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DAT-01 | .csv .tsv .json .jsonl .ndjson .parquet .arrow .xlsx (Beispiel- und Trainingsdaten) | Endung + Magic | Personenbezogene Daten, besondere Kategorien (Art. 9 DSGVO) | Stichprobe: E-Mail, Telefon, IBAN, Steuer-ID, Adresse, Namen; ab S3 mit NER | Regex (S2), Microsoft Presidio mit deutschen Erkennern (S3) | DSGVO | Ja (Regex) | Ja | PII → DSGVO gelb; Art.-9-Daten → DSGVO rot | S2 / S3 | P2 |
| DAT-02 | .csv .tsv | Zellenanfang | CSV-/Formel-Injection beim Öffnen in Excel | Zellen, die mit = + - @ Tab CR beginnen | eigener Code | A | Ja | Ja | Zelle mit HYPERLINK-, cmd- oder DDE-Formel → H; sonst N | S1 | P2 |
| DAT-03 | knowledge/, examples/, few-shot .jsonl, RAG-Dokumente | Pfad | Injection in Daten, die später als Kontext ins Modell gehen | wie AGT-01, eine Stufe niedriger | ATR, eigene Regeln | B | Ja | Ja | Übernahme-Anweisung → H; verdächtig → M | S2 | P2 |
| DAT-04 | Dataset-Loader (*.py), WebDataset (.tar) | Pfad + Inhalt | Loader-Skripte führen Code aus | wie COD-01 / ARC-01 | wie COD-01 | C | Nein | Ja | wie COD-01 | S2 | P3 |

## Dokumente & Medien

| ID | Dateien / Muster | Erkennung | Risiko | Prüfung | Werkzeug | Ebene | Schnellscan | Intensivscan | Ampel-Regel | Sprint | Priorität |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DOC-01 | .pdf | Magic %PDF | JavaScript, /OpenAction, /Launch, eingebettete Dateien, versteckter Text (weiß, 0 pt, außerhalb der Seite) | Objekte zählen; Text extrahieren und wie AGT-01 prüfen | pdfid, pypdf | A / B | Ja (pdfid) | Ja | /Launch oder /JS → H; versteckte Anweisung → wie AGT-01 | S2 | P2 |
| DOC-02 | .docx .xlsx .pptx .docm .xlsm .pptm .doc .xls .odt | Magic (OLE/ZIP) | Makros, externe Vorlagen-Links, DDE, XXE | Makros analysieren; XML sicher parsen; externe Referenzen | oletools (olevba, oleid), defusedxml | A | Ja | Ja | Makro mit AutoOpen/Shell → K; externe Vorlage → H; Makro sonst → M | S2 | P2 |
| DOC-03 | .html .htm .svg .xml | Magic + Endung | Skripte, Event-Handler, externe Ressourcen, XXE; Gefahr für die eigene Oberfläche | Nie rendern, nur als Text; Skripte/XXE erkennen | eigene Regeln, defusedxml | B | Ja | Ja | XXE → H; Skript im SVG → M | S1 | P2 |
| DOC-04 | .png .jpg .jpeg .gif .webp .tiff .mp3 .wav .mp4 .mov | Magic | EXIF/XMP mit GPS und Namen, angehängte Archive (Polyglot), Text im Bild als Injection für Vision-Modelle | Metadaten lesen; Daten nach Dateiende; OCR ab S3 | exiftool, eigener Code, OCR über mittwald AI Hosting (S3) | A / DSGVO | Ja (EXIF, Polyglot) | Ja (+ OCR) | angehängtes Archiv → H; GPS/Personendaten → DSGVO gelb | S2 (OCR S3) | P3 |

## Binaries

| ID | Dateien / Muster | Erkennung | Risiko | Prüfung | Werkzeug | Ebene | Schnellscan | Intensivscan | Ampel-Regel | Sprint | Priorität |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BIN-01 | .exe .dll .so .dylib .msi .dmg .deb .rpm .apk, ELF, Mach-O | Magic | Nicht prüfbarer ausführbarer Code | Markieren; YARA; ClamAV ab S4; Fähigkeitsanalyse später | Inventar, YARA, ClamAV (S4), capa (nach S6) | A | Ja | Ja | Signaturtreffer → K gesperrt + löschen; Binary ohne Quelle → H | S1 / S4 | P1 |
| BIN-02 | .whl .egg, sdist (.tar.gz) | Magic (ZIP/TAR) | Wheels enthalten .pth-Dateien und kompilierte Module | wie ARC-01 entpacken; COD-05 und BIN-01 auf den Inhalt | eigener Entpacker | A | Ja | Ja | .pth im Wheel → K gesperrt; .so → H | S2 | P2 |

## Ampelregeln

| Schwere | Ampel | Regel |
|---|---|---|
| K – kritisch (Sperrliste) | gesperrt | Nicht veröffentlichbar. Beispiele: bekannte Schadsoftware, Autostart mit Netzwerk, unsichtbare Anweisungen, Tool Poisoning, curl\|sh, echte Secrets, Schadpakete, gefährliche Pickle-Imports, .pth mit import |
| H – hoch | rot | Prüfung nötig. Beispiele: Polyglot, Binary ohne Quelle, fremde Paketquelle, Typosquatting, Makro-Vorlagen-Link |
| M – mittel | gelb | Prüfung nötig. Beispiele: jeder Hook, Install-Skript, zu weite Rechte, Endung ≠ Inhalt |
| N – niedrig / I – Info | grün | Hinweise, z. B. fehlendes Lockfile, Submodule nicht geprüft |
| DSGVO-Achse | grün / gelb / rot / grau | Grau = nicht bewertet (Einzeldatei ohne Manifest). Gesamtampel = schlechtere Achse (Konzept §5) |

Note 0–100 = 100 − (K 40, H 15, M 5, N 1), mindestens 0.

## Werkzeuge

| Werkzeug | Lizenz (verifizieren) | Offline | Einsatz | Hinweis |
|---|---|---|---|---|
| python-magic / libmagic | MIT / BSD-2 | ja | Echter Dateityp (Magic Bytes) | Basis für die Scanner-Auswahl |
| gitleaks | MIT | ja | Secrets | Werte im Bericht maskieren |
| OSV-Scanner + OSV-Offline-DB | Apache-2.0 | ja (DB nächtlich per Cronjob) | CVEs, Schadpakete MAL-… | Offline-Modus erzwingen |
| ATR – Agent Threat Rules | MIT | ja | Injection-Muster in Anweisungen | eigene Regeln ergänzen |
| Cisco skill-scanner | Apache-2.0 | ja (LLM-Teil über mittwald) | Skills: statisch, YARA, Datenfluss | Cloud-LLM deaktivieren |
| Cisco mcp-scanner | Apache-2.0 | ja (nur Offline-Analyzer) | MCP-Code und Tool-Beschreibungen |  |
| Opengrep | LGPL-2.1 | ja | Code-Muster | nur eigene Regeln, keine Semgrep-Registry-Regeln |
| Bandit | Apache-2.0 | ja | Python |  |
| YARA | BSD-3 | ja | eigene Signaturen |  |
| ClamAV | GPL-2.0 | ja (Signaturen nächtlich) | klassische Schadsoftware | ca. 1,2 GB RAM, ab S4 |
| picklescan | MIT | ja | Pickle-Opcodes | leichtgewichtig, zuerst |
| modelscan (ProtectAI) | Apache-2.0 | ja | Pickle, Keras, TF, ONNX | ab S3 für Keras/TF |
| fickling (Trail of Bits) | LGPL-3.0 | ja | Pickle-Analyse (Detailbericht) | optional |
| oletools | BSD-2 | ja | Office-Makros |  |
| pdfid / pypdf | Public Domain / BSD-3 | ja | PDF-Objekte, Textextraktion |  |
| exiftool | Artistic/GPL | ja | Metadaten in Bildern/Medien |  |
| defusedxml | PSF | ja | sicheres XML-Parsen | gegen XXE im Scanner selbst |
| hadolint | GPL-3.0 | ja | Dockerfiles |  |
| zizmor | MIT | ja | GitHub-Workflows |  |
| Microsoft Presidio | MIT | ja | Personendaten (NER) | spaCy-Modell de_core_news_sm, RAM prüfen; ab S3 |
| websecureaudit (intern) | eigen | intern | Remote-MCP-Endpunkte: TLS, Header | interne API |

## Nicht verwenden

| Dienst / Modus | Grund |
|---|---|
| VirusTotal / Hybrid Analysis / andere Cloud-Scanner | lädt Dateien oder Hashes zu US-Diensten hoch |
| Invariant/Snyk mcp-scan (Standardmodus) | schickt Tool-Beschreibungen zur Prüfung an eine externe API; stattdessen Cisco mcp-scanner offline |
| TruffleHog mit Verifizierung | prüft gefundene Keys live bei den Anbietern (Netzwerkzugriff, Nutzung fremder Zugangsdaten) |
| Semgrep-Registry-Regeln | Lizenz erlaubt keinen Einsatz als Dienst |
| Cloud-LLMs (OpenAI, Anthropic API etc.) im Prüfer | nur mittwald AI Hosting |

Hinweis: Die Upload-Limits (10 MB pro Datei, 50 MB gesamt) lassen große Modellgewichte nicht zu. Die MOD-Zeilen betreffen kleine Pickle-/Joblib-Dateien in Skills und Tools.
