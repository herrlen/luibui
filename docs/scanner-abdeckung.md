# Scanner-Abdeckung: Matrix gegen Code

## Nachtrag nach Teil B (27.09.2026, Commits `3699d96` bis `571c0df`)

Umgesetzt ohne neue Abhängigkeiten, Entscheidungen zu den Konflikten in
`docs/luibui_Pruefkatalog.md` §13. Die Tabelle weiter unten zeigt den Stand von Teil A.

| Status nach Teil B | Zeilen |
|---|---|
| umgesetzt | ARC-01 (ZIP und tar; 7z/RAR bewusst abgelehnt), ARC-02, ARC-03, INV-01 (eigene Magic-Tabelle statt python-magic), AGT-02, AGT-04, AGT-05, AGT-09, AGT-10, COD-04, COD-05, COD-06, COD-08, COD-09, DEP-01, DEP-02, DEP-03, DEP-04, SEC-01, SEC-02, MOD-01, MOD-05, MOD-06, MOD-07, DAT-02, DAT-03, DOC-01, DOC-02, DOC-03, BIN-02 |
| teilweise | AGT-01 (LLM-Prüfer S3-3), AGT-03 (ROT13 nicht), AGT-06 (Außenprüfung laufender Server S5-6), COD-02 (PII in Ausgaben S3-13), COD-07 (`.idea/` nicht), COD-10 (`.jar` nur A07), DAT-01 (Regex; Presidio S3-13), DOC-04 (GPS ja, OCR S3), BIN-01 (YARA S4-10), MAL-01 (Hash-Liste leer, YARA/ClamAV S4-10) |
| nur geplant | COD-01, COD-03, DAT-04 (S2-1/S2-2), AGT-07, AGT-08 (S2-3/S2-4), MOD-04 (S3-12), MOD-02, MOD-03 (S4-11) |
| Konflikt | keiner offen |

Fixture und gutartiges Gegenstück je Zeile: `corpus/generate.py`, Test
`packages/engine/tests/test_corpus_matrix.py`. Gegen die Kalibrier-Repos (anthropics/skills,
modelcontextprotocol/servers, modelcontextprotocol/python-sdk) ergeben die neuen Regeln keinen
K/H-Befund.

---

# Teil A: Matrix gegen Code (Stand vor Teil B)

> Stand: 27.09.2026 · Grundlage: `luibui_Scanner-Matrix.md` (48 Zeilen, Stand 27.09.2026) gegen den
> Code auf `main` (`497efa4`), `docs/luibui_Konzept.md`, `docs/luibui_Pruefkatalog.md`,
> `docs/luibui_Sprintplanung.md`, `docs/scanner-tools.md`, `docs/infra-kapazitaet.md`.
> Nur gelesen, nichts geändert. Engine-Tests zum Zeitpunkt der Prüfung: 561 bestanden, 11 übersprungen
> (gitleaks lokal nicht installiert).

**Hinweis zur Ablage:** Die Matrix liegt jetzt in `docs/luibui_Scanner-Matrix.md` (nicht
committet, solange das Repository öffentlich ist); die `.xlsx` bleibt außerhalb des Repos.

**Statusbegriffe:** *umgesetzt* = Matrix-Zeile im Kern erfüllt · *teilweise* = ein Teil läuft, Rest
fehlt · *fehlt* = nichts im Code und nicht in der Sprintplanung · *nur geplant (Sprint X)* = nichts im
Code, aber als Task in der Sprintplanung · *Konflikt* = Matrix verlangt etwas, das Konzept, Prüfkatalog
oder Code bewusst anders festlegen.

**Neue Prüfkatalog-IDs** (Vorschlag, Kennzeichen „neu“) sind unten unter
„Vorschläge Prüfkatalog“ beschrieben.

## Übersicht

| Status | Anzahl | Zeilen |
|---|---|---|
| umgesetzt | 2 | DEP-02, SEC-02 |
| teilweise | 23 | ARC-01, ARC-02, ARC-03, INV-01, MAL-01, AGT-01–AGT-05, COD-02, COD-04, COD-06, COD-07, COD-10, DEP-01, DEP-03, DEP-04, SEC-01, MOD-05, DAT-03, DOC-03, BIN-01 |
| fehlt | 16 | AGT-06, AGT-10, COD-05, COD-08, COD-09, MOD-01–MOD-04, MOD-06, MOD-07, DAT-01, DAT-02, DOC-01, DOC-02, DOC-04 |
| nur geplant | 5 | AGT-07, AGT-08 (S2-3/S2-4), COD-01, COD-03 (S2-1/S2-2), DAT-04 (S2-1) |
| Konflikt | 2 | AGT-09, BIN-02 |

**P1-Zeilen mit „fehlt“ oder „teilweise“ (19):** ARC-01, ARC-02, ARC-03, INV-01, MAL-01, AGT-01,
AGT-02, AGT-03, AGT-04, AGT-05, AGT-06, COD-04, COD-05, COD-06, COD-07, DEP-01, DEP-03, SEC-01, BIN-01.
Dazu vier P1-Zeilen „nur geplant“ in Sprint 2: AGT-07, AGT-08, COD-01, COD-03.

## Tabelle

Pfade ohne Präfix beziehen sich auf `packages/engine/luibui_scan/`.

| ID | Matrix-Titel | Prüfkatalog-ID | Status | Beleg | fehlende Teile | Sprint laut Matrix |
|---|---|---|---|---|---|---|
| ARC-01 | Archive (.zip .tar .7z .rar …): Zip-Slip, Bombe, Links, Verschlüsselung | A01, A07 | teilweise | `intake/safe_extract.py:22-102` (ZIP: Pfade, Rate, Anzahl, Größe, Links, Verschlüsselung, Überlappung vor dem ersten Schreiben); `intake/paths.py:21-40`; `intake/limits.py:9-25`; Upload-Art wählt der Client, nicht Magic (`apps/api/luibui_api/uploads.py:72-107`) | nur ZIP; `.tar/.tgz/.gz/.bz2/.xz/.7z/.rar` werden nicht entpackt (als Upload `zip` → `defektes_archiv`, im Paket nur A07); „Tiefe ≤ 3“ (verschachtelt) nicht umgesetzt, verschachtelte Archive bleiben gepackt (siehe Konflikte); Schwere laut Matrix pauschal H, Katalog §11 staffelt H/M/N; Schnellscan nimmt noch keine Datei an | S1 |
| ARC-02 | Git-URL, .gitmodules, .gitattributes, LFS | A10, A11, neu A13 | teilweise | `intake/safe_git.py:102-119, 154-200` (depth 1, keine Submodule, Hooks aus, `GIT_LFS_SKIP_SMUDGE=1`, `core.symlinks=false`); A10 `analyzers/_a_herkunft.py:14-39`; A11 `analyzers/_a_herkunft.py:45-64` | `filter=`/`diff=`/`merge=` in `.gitattributes` wird nicht ausgewertet (nur als üblich in `a_dateien.py:246`); LFS-Zeiger werden nicht als „nicht geprüft“ markiert; Submodule M (Katalog A11) statt I (Matrix) | S1 |
| ARC-03 | Dateinamen und Pfade | B03, A09, A01, neu A14 | teilweise | Bidi/Cf im Namen → B03 H `analyzers/b_inhalte.py:150-171`; versteckte Dateien A09 N `analyzers/a_dateien.py:295-342`; zu lange Pfade → A01 `intake/paths.py:34-37` | Doppelendung (`rechnung.pdf.exe`) → M fehlt; reservierte Windows-Namen (`CON`, `NUL`, …) fehlen; versteckte Datei N (Katalog) statt I (Matrix) | S1 |
| INV-01 | Magic Bytes vs. Endung, Polyglots | A05, neu A15 | teilweise | eigene Magic-Tabelle `inventory.py:42-97`, kein python-magic/libmagic (`apps/worker/Dockerfile:23-34`, `packages/engine/pyproject.toml`); A05 `analyzers/a_dateien.py:132-153` nur für Endungen in `_TEXT_EXT`/`_BINARY_EXT` (`a_dateien.py:29-84`) | Scanner-Auswahl nach Inhalt fehlt (siehe Prüffrage 1); Polyglot/Daten nach Dateiende (z. B. PNG + ZIP) fehlt; A05 ist H (Katalog), Matrix will M; viele Typen ohne Magic (Pickle, safetensors, GGUF, ONNX, deb/rpm/msi) | S1 |
| MAL-01 | Bekannte Schadsoftware (Hash, YARA, ClamAV) | A08, C10 | teilweise | A08 `analyzers/a_dateien.py:203-236`, Sperrliste `scoring.py:37-45`; Nicht-Ablegen `apps/api/luibui_api/uploads.py:219-226`; Hash-Liste `rules/data/schadsoftware-sha256.txt` | Blockliste enthält nur Kommentare (0 Hashes); YARA fehlt ganz (kein `rules/yara/`, kein `yara-x` im Image); ClamAV S4 (S4-10); „sofort löschen“ gilt nur für die Ablage, der Scratch wird regulär am Jobende gelöscht | S1 / S4 |
| AGT-01 | SKILL.md, CLAUDE.md, AGENTS.md, .cursorrules, .mdc … | B07–B11, B14–B17, B18/B19 (LLM) | teilweise | B-Muster über Anweisungstexte `analyzers/b_muster.py:19-39, 108-124`; 11 eigene Regeln `rules/b-muster/`, 157 ATR-Regeln `rules/external/atr/QUELLE.md`; B07 `analyzers/b_inhalte.py:346-378` | `.cursor/rules/*.mdc` wird von B08–B17 nicht gelesen (`.mdc` fehlt in `INSTRUCTION_SUFFIXES`, `b_muster.py:19-21`); Erkennung nach Dateiname/Frontmatter gibt es nicht (Regeln laufen auf allen Textdateien, das ist breiter); LLM-Prüfer S3-3 | S1 (LLM S3) |
| AGT-02 | Unsichtbare Zeichen (Tags, Zero-Width, Bidi, VS, Homoglyphen) | B01, B02, B03, B04 | teilweise | B01 `b_inhalte.py:23-58` (dekodiert für den Beleg); B02 `b_inhalte.py:63-118`; B03 `b_inhalte.py:123-147`; B04 `b_inhalte.py:176-219` | dekodierter Tag-Text wird nicht erneut mit B08–B17 geprüft; Variation Selectors nur U+E0100–E01EF, nicht U+FE00–FE0F; einzelnes Zero-Width ist H (Katalog B02), Matrix will N | S1 |
| AGT-03 | Kodierte Nutzlast (Base64, Hex, gzip+Base64, ROT13) | B06 | teilweise | `b_inhalte.py:291-341` (Base64 ab 120 Zeichen, Hex ab 160 Zeichen, nur Anweisungs-Sprachen) | gzip+Base64, ROT13 und rekursives Dekodieren (3 Stufen) fehlen; dekodierter Text wird nicht auf Befehl/URL/Anweisung geprüft; Schwere pauschal M (Katalog B06), Matrix H bzw. I | S1 |
| AGT-04 | .claude/commands, .claude/agents, *.prompt.md | B08–B17, neu E08 | teilweise | `.md` läuft durch B-Muster (`b_muster.py:33-39`) | Auswertung von `allowed-tools`/`tools` (z. B. `Bash(*)`) fehlt vollständig | S1 |
| AGT-05 | Hooks (.claude/settings*.json, hooks/hooks.json, .cursor/hooks.json) | A02 | teilweise | `analyzers/_a_ausfuehrung.py:72-88` (jede `hooks.json` und `.claude/settings*.json`); Gefährlich-Muster `_a_ausfuehrung.py:11-17` | Muster erkennt nur Download+Ausführen, `base64 -d`, `eval`, Reverse Shell u. ä.; reiner Netzwerkzugriff, Löschen (`rm -rf`), Zugriff auf `~/.ssh`, `~/.aws`, Browser-Profile und Persistenz werden nicht als K erkannt; harmloser Hook ergibt H statt M | S1 |
| AGT-06 | .mcp.json, mcp.json, claude_desktop_config.json | neu E09, E05, E07, G02 | fehlt | nur als übliche Datei gelistet `a_dateien.py:262`; kein Analyzer liest `command/args/env/url` | Auswertung `npx -y`, `uvx`, `docker run`, Übergabe an D, `http://` → M, Remote-URL an websecureaudit (Sprintplanung S5-6), Länderzuordnung (S2-4) | S1 / S2 |
| AGT-07 | plugin.json, marketplace.json, manifest.json (.dxt), openapi, ai-plugin.json, luibui.json | G01, G03, G04 | nur geplant (Sprint 2) | S2-4 (`luibui_Sprintplanung.md` Z. 144); heute nur Pakettyp-Erkennung `inventory.py:171-212`; `scan.py:106` („validating luibui.json belongs to Ebene G“); `g_dsgvo` in `ERWARTET` `scan.py:30-39` | Schema-Prüfung, Abgleich Rechte/Endpunkte ↔ Code | S2 |
| AGT-08 | Tool-Definitionen (description, inputSchema) | E01, E02, E03, B19 | nur geplant (Sprint 2) | S2-3 (Sprintplanung Z. 143); `e_mcp` in `ERWARTET` `scan.py:34-35`; heute greift nur B16 auf Tool-Listen in `.json` (`rules/b-muster/LB-B16-tool-manipulation.yaml`) | E-Analyzer, Cisco mcp-scanner (nicht im Image), Beschreibungen im Quellcode; LLM S3-3 | S2 (LLM S3) |
| AGT-09 | .dxt, .mcpb, .vsix, .crx, .xpi | A07 | Konflikt | ZIP-Magic → A07 M „Archiv im Paket bleibt ungeprüft“ `a_dateien.py:162-180`; `intake/safe_extract.py:3-5` („nested archives stay packed“) | Matrix verlangt rekursives Entpacken; Konzept/Katalog A07 legen fest, dass verschachtelte Archive gepackt bleiben (siehe Konflikte) | S1 |
| AGT-10 | Open-WebUI-Tools mit `requirements:` im Frontmatter | D01–D05 (Parser-Erweiterung) | fehlt | `analyzers/d_abhaengigkeiten.py:104-116` liest nur `requirements*.txt`, `pyproject.toml`, `package.json` | Frontmatter-Parser, Übergabe an D und OSV | S1 |
| COD-01 | .py, .pyw | C01, C02, C04, C05, C08 | nur geplant (Sprint 2) | S2-1, S2-2 (Sprintplanung Z. 141-142); `c_code` in `ERWARTET` `scan.py:34`; Bandit, Opengrep, skill-scanner nicht im Image (`apps/worker/Dockerfile`) | kompletter C-Analyzer | S2 |
| COD-02 | .ipynb | C01–C13, B20, neu G07 | teilweise | gitleaks läuft über alle Dateien inkl. Notebooks `tools/gitleaks.py:40-56` | Zellen-Extraktion, `!pip`/`%%bash`, PII in Ausgaben | S2 |
| COD-03 | .js .mjs .cjs .ts .tsx | C01, C02, C08 | nur geplant (Sprint 2) | S2-1, S2-2 | kompletter C-Analyzer | S2 |
| COD-04 | .sh .bash .zsh .ps1 .bat .cmd | C03, C07, A03 (B12, B13 für Text) | teilweise | nur Install-Skripte nach Namen (`install*.sh` usw.) und `Makefile` → A03 H `_a_ausfuehrung.py:140-178`; B-Muster lesen `.sh`/`.ps1` nicht (`b_muster.py:19-21`), Skripte mit Shebang sind `kind=script` und fallen ebenfalls heraus (`b_muster.py:36`) | allgemeine Skripte mit `curl\|sh`, `IEX(New-Object Net.WebClient)`, Persistenz → K; laut Konzept ist C erst S2 und nicht im Schnellscan (Widerspruch) | S1 |
| COD-05 | *.pth (Python), sitecustomize.py, usercustomize.py, conftest.py | A02 (Erweiterung), A03 | fehlt | keine Fundstelle für `.pth`, `sitecustomize`, `usercustomize`, `conftest` in `packages/engine/luibui_scan` | `.pth` mit `import` → K; conftest mit Netzwerk → H; Unterscheidung Text-`.pth` vs. PyTorch-ZIP (siehe Prüffrage 2) | S1 |
| COD-06 | setup.py, pyproject (build-backend), package.json-Hooks, Makefile, Justfile, .envrc | A02, A03 | teilweise | npm-Hooks A02 `_a_ausfuehrung.py:18, 105-116`; `.envrc` A02 `_a_ausfuehrung.py:125-133`; `setup.py`/`Makefile` A03 H `_a_ausfuehrung.py:140-178` | **`prepare` fehlt** in `_INSTALL_HOOKS` (`_a_ausfuehrung.py:18`), obwohl Katalog A02 es nennt; `pyproject.toml` build-backend, `Justfile` fehlen; setup.py mit Netzwerk ist H (A03, ohne ●), Matrix will K gesperrt; harmloser npm-Hook H statt M | S1 |
| COD-07 | .vscode/tasks.json, .vscode/settings.json, devcontainer.json, .idea/ | A02 (Erweiterung) | teilweise | `tasks.json` mit `runOn: folderOpen` `_a_ausfuehrung.py:89-104` | `devcontainer.json` (`initializeCommand`, `postCreateCommand` u. a.), `.vscode/settings.json`, `.idea/` fehlen; folderOpen-Task ohne gefährliches Muster ergibt H, Matrix will K | S1 |
| COD-08 | Dockerfile, Containerfile, docker-compose.yml | neu C14 | fehlt | keine Fundstelle; hadolint weder in Konzept §9, `scanner-tools.md` noch Sprintplanung | alles; hadolint ist GPL-3.0 (nur als Prozess) | S2 |
| COD-09 | .github/workflows, .gitlab-ci.yml, .forgejo | neu C15 | fehlt | keine Fundstelle; zizmor nirgends in Doku oder Plan | alles | S2 |
| COD-10 | .pyc, __pycache__, .class, .jar, .wasm | A04, A06 | teilweise | `.class`, `.wasm` per Magic → A04 H `inventory.py:48, 65, 75-77`, `a_dateien.py:113-131`; `.pyc` ohne Quelle nach Endung → A06 M `a_dateien.py:154-157` | `.pyc` wird nicht per Magic erkannt; `.jar` → nur A07 M; Matrix will H für Bytecode ohne Quelle (Katalog A06: M) | S1 |
| DEP-01 | Python-Abhängigkeiten | D01–D04 | teilweise | D03/D04/D05 `analyzers/d_abhaengigkeiten.py:61-116, 160-273`; OSV offline `tools/osv.py:60-104`, `d_abhaengigkeiten.py:303-356`; MAL → K + Sperrliste `scoring.py:52-55` | `setup.cfg` und `Pipfile` werden für D03/D04 nicht gelesen; fehlendes Lockfile ist M (Katalog D04), Matrix will N | S1 |
| DEP-02 | npm-Abhängigkeiten | D01–D04 | umgesetzt | `d_abhaengigkeiten.py:90-101, 190-194`; Lockfiles über OSV | – | S1 |
| DEP-03 | .npmrc, .yarnrc.yml, pip.conf, uv.toml, --index-url | A12, B20 | teilweise | A12 H `analyzers/_a_herkunft.py:69-118`; Tokens über gitleaks-Standardregeln `rules/gitleaks/gitleaks.toml` | `uv.toml` fehlt (nur `[tool.uv.index]` in `pyproject.toml`) | S1 |
| DEP-04 | git+https, http-Tarballs, lokale Pfade | D05 | teilweise | `d_abhaengigkeiten.py:227-273` | PyPI-Direkt-URL `paket @ https://…` ohne Hash wird nicht erkannt; `--hash=` wird nicht berücksichtigt | S1 |
| SEC-01 | .env*, *.pem, *.key, id_rsa*, *.p12, .kdbx … | B20, A09 | teilweise | `.env` → A09 M `a_dateien.py:304-324`; Inhalt → gitleaks (`useDefault`) `analyzers/secrets.py:29-70` | Namensliste für Schlüsseldateien fehlt (binäre `.p12/.pfx/.kdbx` findet gitleaks nicht); Platzhalter ergibt M (`secrets.py:42`), Matrix will I; eigene `LB-B20-…`-Regeln würden nicht sperren, weil B20 nicht in `SPERRLISTE_KATALOG` steht (`scoring.py:37-45`) | S1 |
| SEC-02 | Secrets im Inhalt | B20 | umgesetzt | `tools/gitleaks.py:39-96` (eigene Config, kein Allow-Kommentar, `--redact=100`, Timeout, leere Umgebung); Maskierung `secrets.py:23-26` | – (TruffleHog nicht im Einsatz) | S1 |
| MOD-01 | Pickle-Formate (.pkl, .pt, .pth, .joblib, .npy …) | neu A16 ● | fehlt | keine Fundstelle; Pickle hat keinen Eintrag in `inventory.py:42-63`; PyTorch-ZIP → nur A07 M | Opcode-Analyse ohne Laden; picklescan/modelscan/fickling nicht in `scanner-tools.md` | S2 |
| MOD-02 | .h5 .keras, SavedModel, .tflite | neu A17 | fehlt | – | alles; modelscan nicht geprüft | S3 |
| MOD-03 | .onnx | neu A17 | fehlt | – | alles | S3 |
| MOD-04 | .gguf | neu A16, A18, B08–B17 | fehlt | – | Header-Parser, `chat_template` + SSTI | S3 |
| MOD-05 | .llamafile | A04 | teilweise | APE beginnt mit `MZ`, ELF mit `\x7fELF` → A04 H (`inventory.py:43, 78-79`, `a_dateien.py:113-131`) | „nicht veröffentlichbar“ geht mit H nicht (nur „gesperrt“ blockiert, Konzept §5) | S1 |
| MOD-06 | .safetensors | neu A18 | fehlt | – | Header-Validierung, `__metadata__` durch B-Regeln | S2 |
| MOD-07 | config.json (auto_map), tokenizer_config.json (chat_template) | neu A19, A16 | fehlt | – | alles; Korrelation S2-5 | S2 |
| DAT-01 | Daten mit Personenbezug (.csv .jsonl .parquet …) | neu G07 | fehlt | – | Regex-Erkenner, Presidio (S3); in Sprintplanung nicht vorgesehen | S2 / S3 |
| DAT-02 | CSV-/Formel-Injection in Paketdaten | neu A20 | fehlt | – (CLAUDE.md Regel 12 betrifft nur luibuis eigenen CSV-Export) | alles | S1 |
| DAT-03 | knowledge/, examples/, few-shot .jsonl | B08–B17 | teilweise | B-Muster auf `.md/.txt/.json/.yaml` `b_muster.py:19-21`; B01–B07 auf allen Textdateien `b_inhalte.py:381-392` | `.jsonl`/`.ndjson` fehlen in `INSTRUCTION_SUFFIXES`; „eine Stufe niedriger“ für Wissensdaten fehlt | S2 |
| DAT-04 | Dataset-Loader, WebDataset (.tar) | C01–C13, A07 | nur geplant (Sprint 2) | C in S2-1; `.tar` → A07 M | wie COD-01 | S2 |
| DOC-01 | .pdf | neu A21, B05 | fehlt | PDF-Magic nur für A05 `inventory.py:56`, `a_dateien.py:75` | pdfid/pypdf nicht im Image; Objekte, versteckter Text | S2 |
| DOC-02 | Office (.docx .docm .xls …) | neu A21 | fehlt | OLE-Magic `inventory.py:62`; `.docx/.xlsx/.pptx` von A07 ausgenommen `a_dateien.py:86`; `.docm/.xlsm/.pptm` landen als „Archiv“ in A07 | oletools, defusedxml; Makros, externe Vorlagen, DDE | S2 |
| DOC-03 | .html .htm .svg .xml | B05, neu B21 | teilweise | versteckter Text in SVG/Markdown B05 `b_inhalte.py:224-286`; Belege nur als Text (`apps/web`, siehe `docs/log.md` Sprint-2-Eintrag) | `<script>`, Event-Handler, XXE fehlen; defusedxml nicht eingebunden | S1 |
| DOC-04 | Bilder, Audio, Video | A15, neu G08 | fehlt | nur Magic für PNG/JPEG/GIF/WebP `inventory.py:57-60, 80-81` | EXIF/GPS, angehängte Archive, OCR (S3) | S2 (OCR S3) |
| BIN-01 | .exe .dll .so .dylib .msi .dmg .deb .rpm .apk | A04, A08, C10 | teilweise | ELF/Mach-O/PE/Java/WASM → A04 H `inventory.py:42-79`, `a_dateien.py:113-131`; Hash → A08 | `.msi` (OLE), `.deb` (ar), `.rpm`, `.dmg` ohne Befund, `.apk` nur A07; YARA fehlt; ClamAV S4 | S1 / S4 |
| BIN-02 | .whl .egg, sdist | A07, A02 | Konflikt | ZIP/gzip → A07 M `a_dateien.py:162-180` | Matrix: entpacken und COD-05/BIN-01 auf den Inhalt; Konzept/Katalog: verschachtelt bleibt gepackt | S2 |

## Konflikte

1. **Öffentliche Prüfmatrix (Teil C, Schritt 2 und 3).** Len hat am 27.09.2026 entschieden, dass
   luibui.com weder den vollständigen Katalog noch die Matrix zeigt und GitHub nicht verlinkt
   (`docs/log.md`, Eintrag „S2-11: Startseite ohne Quellcode- und Katalog-Links“). Teil C verlangt die
   Seite `/pruefkatalog` mit der vollen Matrix und den Link „Vollständige Prüfmatrix ansehen →“. Das
   widerspricht der Entscheidung. Ebenfalls betroffen: Konzept §3 (luibui.com mit „Prüfkatalog“) und
   Sprintplanung S3-9 („Prüfkatalog“ auf luibui.com). Zusätzlich: Die Kacheln aus Teil C (Autostart
   `.pth`/`devcontainer.json`, Modelldateien, Dokumente) bewerben Prüfungen, die laut Tabelle noch
   fehlen; die heutige Startseite zeigt bewusst nur Prüfungen, die laufen.
2. **Verschachtelte Archive (ARC-01 „Tiefe ≤ 3“, AGT-09, BIN-02).** Die Matrix will Archive im Paket
   rekursiv entpacken. `intake/safe_extract.py:3-5`, Prüfkatalog A07 („bleiben gepackt und ungeprüft“)
   und Konzept §4 Schritt 2 sehen das nicht vor. Rekursives Entpacken ist eine Änderung an der
   Annahme (Sicherheitsregel 2) und braucht Lens Freigabe samt Limits für die Summe aller Ebenen.
3. **Weitere Archivformate (ARC-01).** CLAUDE.md Regel 2 und Konzept §2 nennen nur ZIP. `.7z` und
   `.rar` brauchen zusätzliche Bibliotheken; für RAR gibt es nur die unfreie `unrar`-Lizenz oder
   libarchive. Neue Abhängigkeit mit unklarer Lizenz → vorher fragen.
4. **Jede K-Zeile = gesperrt (Matrix „Ampelregeln“) vs. Sperrliste mit ● (Katalog §1, §10).** Im
   Katalog sperrt ein K nur aus markierten Prüfungen, sonst Rot. Betroffen: DOC-02 (Makro → K), MOD-04
   und MOD-07 (SSTI → K), MOD-01 (Pickle → K gesperrt), COD-05/BIN-02 (`.pth` → K gesperrt), COD-06
   (setup.py mit Netzwerk → K gesperrt, heute A03 H ohne ●).
5. **Netzzugriff in der Prüfung (AGT-06).** websecureaudit prüft eine laufende Remote-URL, also mit
   Netz. Der prüfende Kindprozess hat bewusst kein Netz (`apps/worker/luibui_worker/child.py:30-55`,
   `apps/worker/Dockerfile:34`). Die Außenprüfung muss außerhalb des Kindprozesses laufen; im Plan ist
   sie S5-6 (E07), die Matrix nennt S1/S2.

## Widersprüche Matrix ↔ Konzept, Prüfkatalog und Sprintplanung

**Schnellscan-Umfang (Konzept §2, Z. 59: A, B nur Regeln, Secrets, D bei Git):**
- COD-04 „Ja (Muster)“: Shell-Muster gehören zu Ebene C, die laut Konzept und Katalog (C03 „S –“) nicht
  im Schnellscan läuft.
- DAT-01 „Ja (Regex)“, DOC-04 GPS → DSGVO gelb, COD-02 PII → DSGVO gelb, AGT-06 Länderzuordnung: der
  DSGVO-Abgleich ist laut Konzept nur Intensivscan. Außerdem darf bei Einzeldatei/Auswahl ohne Manifest
  nur ein Drittland-Endpunkt die DSGVO-Achse einfärben (Konzept §5, Z. 156); PII-Funde aus Daten
  bräuchten dafür eine Regeländerung.
- ARC-01 „Ja (≤ 2 MB)“: Konzept erlaubt „eine Datei bis 2 MB“; ob ein ZIP dabei entpackt wird, ist
  offen. Heute nimmt der Schnellscan nur Git-URLs an (`apps/api/luibui_api/routes/quickscans.py:31-72`,
  Datei-Schnellscan ist S2-13).

**Sprints:**
- COD-04 (S1) – Konzept §4 legt C auf Sprint 2.
- AGT-06 (S1/S2) – websecureaudit ist S5-6, Länderzuordnung S2-4.
- COD-08, COD-09 (S2), MOD-01, MOD-06, MOD-07, DAT-01–DAT-03, DOC-01, DOC-02, DOC-04 (S2) und MOD-02–
  MOD-04 (S3): keine Task in der Sprintplanung. Sprint 2 ist laut Plan schon „dichtester Sprint“.

**Schweregrade (Matrix → Katalog/Code):** ARC-01 alles H → A01 H/M/N · ARC-02 Submodule I → A11 M ·
ARC-03 versteckt I → A09 N · INV-01 M → A05 H · AGT-02 einzelnes Zero-Width N → B02 H · AGT-03
dekodiert H / sonst I → B06 M · AGT-05 anderer Hook M → Code H · COD-06 harmloser Install-Hook M → Code H,
setup.py mit Netz K → A03 H · COD-07 folderOpen K → Code H ohne gefährliches Muster · COD-10 H → A06 M ·
DEP-01 ohne Lockfile N → D04 M · SEC-01 Platzhalter I → Code M. Der Katalog erlaubt nur Absenken nach
Benchmark (Katalog §1), keine Anhebung über die Regelschwere; wo die Matrix höher liegt (INV-01 nein,
COD-10, COD-06/07), muss der Katalog geändert werden.

**Sperrliste (Konzept §5, 15 Kategorien):** „gefährliche Pickle-Imports“ und „.pth mit import“ stehen
in der Matrix-Ampeltabelle als Sperrlisten-Beispiele, im Konzept nicht. `.pth` passt unter „Autostart-
Dateien mit Befehlen“ (A02), Pickle/SSTI braucht eine eigene Kategorie oder die Zuordnung zu
„Schadmuster“.

**Werkzeuge:** picklescan, modelscan, fickling (LGPL-3.0), oletools, pdfid/pypdf, exiftool,
python-magic, defusedxml, hadolint (GPL-3.0), zizmor und Presidio fehlen in Konzept §9 und in
`docs/scanner-tools.md` (Lizenz, Version, RAM nicht geprüft). Laut CLAUDE.md vorher fragen. Die Matrix
nennt für ClamAV „ca. 1,2 GB RAM“, `scanner-tools.md` §8 nach Herstellerangabe 3–4 GiB empfohlen.
`scanner-tools.md` führt Invariant/Snyk `mcp-scan` nicht unter „nicht verwenden“.

**Sonstiges:** MOD-05 „nicht veröffentlichbar“ bei H widerspricht Konzept §5/§7 (nur „gesperrt“
blockiert). Die Matrix-Grundregel „nie nach Dateiendung“ steht neben vielen Zeilen, deren Erkennung
selbst „Dateiname“ oder „Pfad“ ist; sinnvoll ist: Typ per Magic, Konfigurationsdateien per Name.
`scanner-tools.md` (Offline-Warnungen) beschreibt einen eigenen Cron-Container und ein read-only
gemountetes DB-Volume; umgesetzt ist der Download im Worker-Elternprozess
(`apps/worker/luibui_worker/osvdb.py:1-7`, von Len am 27.09.2026 freigegeben) und `luibui-rules` ist
beschreibbar (`docs/infra-kapazitaet.md`, Tabelle „Unterschiede“).

## Antworten auf die Prüffragen

1. **Magic oder Endung (INV-01)?** Beides, überwiegend Endung und Dateiname. Das Inventar bestimmt den
   Typ über eine eigene Magic-Tabelle (`inventory.py:42-97`, kein python-magic). Dieser Typ entscheidet
   nur, ob eine Datei als Text gelesen wird (`analyzers/_common.py:67-70`) und für A04/A05/A07. Welche
   Prüfung läuft, hängt an Endung oder Name: B-Muster nach Endung (`b_muster.py:19-39`), A02/A03/A12
   nach Dateinamen, D nach Dateinamen (`d_abhaengigkeiten.py:104-116`), Sprache nach Endung
   (`inventory.py:161-166`). A05 meldet Abweichungen nur für bekannte Endungen.
2. **`.pth` Autostart vs. PyTorch-ZIP per Magic?** Nein. `.pth` wird nirgends ausgewertet. Implizit
   landet ein Text-`.pth` als `text`, ein PyTorch-`.pth` als `zip` (→ A07 M „Archiv“), ein reines
   Pickle als `binary` ohne Befund.
3. **Alles offline?** Ja für den Prüfpfad: Kein Aufruf von VirusTotal, Invariant/Snyk `mcp-scan`,
   TruffleHog, Semgrep-Registry oder Cloud-LLMs im Code (Suche über `apps/` und `packages/`). gitleaks
   ohne Verifizierung (`tools/gitleaks.py:40-56`), OSV mit `--offline --offline-vulnerabilities
   --no-resolve --no-call-analysis=all` (`tools/osv.py:63-73`), Kindprozess ohne Netz
   (`apps/worker/luibui_worker/child.py:30-55`, im Produktions-Worker geprüft laut
   `docs/infra-kapazitaet.md`). Einzige Außenverbindung: Der Worker-Elternprozess lädt die OSV-Datenbank
   von Google Cloud Storage (`osvdb.py:18`), reiner Download, freigegeben und in `docs/drittdienste.md`
   geführt.
4. **Sperrliste deckt alle „K gesperrt“-Zeilen?** Teilweise. Abgedeckt über `SPERRLISTE_KATALOG`
   (`scoring.py:37-45`) bzw. `SPERRLISTE_EXTERN` (`scoring.py:52-55`): MAL-01 (A08), AGT-01 (B08–B10),
   AGT-02 (B01), AGT-05 (A02), AGT-08 (E01), COD-01 (C04/C05), COD-03 (C08), COD-04 (C03/C07), COD-07
   (A02), DEP-01 (osv:MAL-), SEC-01/02 (gitleaks:), BIN-01 (A08). Nicht abgedeckt: COD-05 und BIN-02
   (`.pth`, keine Prüfung, A02-Liste nennt `.pth` nicht), COD-06 (setup.py/pyproject → A03 ohne ●),
   MOD-01 (keine Katalog-ID), SEC-01 für eigene Namensregeln (B20 fehlt in `SPERRLISTE_KATALOG`).
5. **Schnellscan-Umfang passend?** Code und Konzept passen: `ERWARTET[SCHNELL]` = A, B-Inhalte,
   B-Muster, Secrets, D, OSV (`scan.py:22-31`) entspricht Konzept §2. Die Matrix geht darüber hinaus
   (COD-04, DAT-01, DOC-04-GPS, AGT-06-Länder, ARC-01-ZIP), siehe Widersprüche. Offen ist der
   Datei-Schnellscan bis 2 MB (S2-13), heute nur Git.
6. **RAM reicht?** Voraussichtlich ja für picklescan, oletools, exiftool und pdfid, aber nicht belegt:
   Keines der vier steht in `docs/scanner-tools.md`. Gemessen (S1-12, `docs/infra-kapazitaet.md`
   Z. 140-170): Container-Spitze 383 MB, größter Prozess 147 MB bei 1.464 MiB wirksamem Limit
   (`infra/mittwald-stack.yml:62-75`, 1536m). Es läuft eine Prüfung gleichzeitig, die Werkzeuge
   nacheinander; die vier sind kleine Python-/Perl-Prozesse und lesen Dateien bis 10 MB. Das eigentliche
   Risiko sind die bereits geplanten Opengrep (0,5–2 GB, nicht verifiziert) und Cisco-Scanner
   (300–800 MB, nicht verifiziert), ab S3 Presidio mit spaCy-Modell (nicht gemessen) und ab S4 ClamAV
   (3–4 GiB laut Hersteller). Nach Einbau jedes Werkzeugs neu messen.

## Vorschläge (nicht angewendet)

### Prüfkatalog

```diff
 ## 2. Ebene A – Dateien und Annahme
-| A02 | **Autostart-Dateien mit Befehlen:** `.claude/settings.json`-Hooks, `.vscode/tasks.json` mit `runOn: folderOpen`, `.envrc`, `.git/hooks`, `package.json`-Skripte `preinstall`/`install`/`postinstall`/`prepare` | K | ● | ✓ ✓ ✓ ✓ | eigene Regeln | ASI05, LLM03 |
+| A02 | **Autostart-Dateien mit Befehlen:** `.claude/settings.json`- und `hooks.json`-Hooks, `.vscode/tasks.json` mit `runOn: folderOpen`, `.devcontainer/devcontainer.json` (`initializeCommand`, `onCreateCommand`, `postCreateCommand`, `postStartCommand`), `.envrc`, `.git/hooks`, `package.json`-Skripte `preinstall`/`install`/`postinstall`/`prepare`, Python-`.pth` mit `import`-Zeile, `sitecustomize.py`, `usercustomize.py`, `setup.py`/Build-Backend mit Netz- oder Shell-Aufruf (Matrix AGT-05, COD-05, COD-06, COD-07) | K | ● | ✓ ✓ ✓ ✓ | eigene Regeln | ASI05, LLM03 |
-| A03 | **Install-Skripte:** `setup.py` mit Code außerhalb von `setup()`, `install.sh`/`install.ps1`, `Makefile`-Ziele, die herunterladen und ausführen | H | – | … |
+| A03 | **Install- und Testskripte:** `install.sh`/`install.ps1`, `Makefile`/`Justfile`-Ziele, die herunterladen und ausführen, `conftest.py` mit Netzwerk (Matrix COD-05, COD-06) | H | – | … |
-| A06 | **Kompilierter Code ohne Quelle:** … | M | … |
+| A06 | **Kompilierter Code ohne Quelle:** … (Matrix COD-10 verlangt H – Len entscheidet) | M | … |
-| A07 | **Archive im Archiv:** verschachtelte ZIP/tar/7z/RAR bleiben gepackt und ungeprüft | M | … |
+| A07 | **Archive im Archiv:** verschachtelte ZIP/tar/7z/RAR bleiben gepackt und ungeprüft; Ausnahme nach Freigabe: `.whl`, `.dxt`, `.mcpb`, `.vsix` werden eine Ebene tief entpackt (Matrix AGT-09, BIN-02) | M | … |
+| A13 | **Git-Attribute mit Treibern und LFS:** `filter=`/`diff=`/`merge=` in `.gitattributes` (M), LFS-Zeiger ohne Inhalt als „nicht geprüft“ (I) (Matrix ARC-02) | M | – | ✓ ✓ – ✓ | eigene Regeln | ASI04 |
+| A14 | **Täuschende Dateinamen:** Doppelendung (`.pdf.exe`), reservierte Windows-Namen (Matrix ARC-03) | M | – | ✓ ✓ ✓ ✓ | eigene Regeln | ASI04 |
+| A15 | **Polyglot und angehängte Daten:** Datei ist gleichzeitig zwei Typen oder trägt Daten nach dem Formatende (Matrix INV-01, DOC-04) | H | – | ✓ ✓ ✓ ✓ | Inventar | ASI04 |
+| A16 | **Code-Ausführung beim Laden eines Modells:** Pickle-`GLOBAL`/`REDUCE` auf `os`, `subprocess`, `builtins`, `socket`, `runpy`; Jinja-SSTI in `chat_template` (Matrix MOD-01, MOD-04, MOD-07) | K | ● | ✓ ✓ ✓ ✓ | picklescan (offline), eigener Code | ASI05, LLM03 |
+| A17 | **Modellstruktur mit Code oder Dateizugriff:** Keras-Lambda, TF-Datei-Ops, ONNX `external_data` außerhalb des Pakets (Matrix MOD-02, MOD-03) | H | – | ✓ ✓ ✓ – | modelscan, eigener Code | ASI05, LLM03 |
+| A18 | **Modelldatei unklar:** ungültiger Header (safetensors, GGUF), unbekannte Pickle-Globals (Matrix MOD-01, MOD-06) | M | – | ✓ ✓ ✓ ✓ | eigener Code | ASI04 |
+| A19 | **`trust_remote_code`:** `auto_map` verweist auf Code im Paket (Matrix MOD-07) | M | – | ✓ ✓ ✓ ✓ | eigene Regeln | ASI05, LLM03 |
+| A20 | **Formel-Injection in mitgelieferten Tabellen:** Zellen mit `HYPERLINK`, `cmd`, DDE (H), sonst Formelbeginn (N) (Matrix DAT-02) | H | – | ✓ ✓ ✓ ✓ | eigener Code | LLM05 |
+| A21 | **Aktive Inhalte in Dokumenten:** PDF `/JS`, `/Launch`, `/OpenAction`, eingebettete Dateien; Office-Makros, externe Vorlagen, DDE (Matrix DOC-01, DOC-02) | H | – | ✓ ✓ ✓ ✓ | pdfid, oletools | ASI05 |
 ## 3. Ebene B – Inhalte
+| B21 | **Aktive Inhalte in HTML/SVG/XML:** `<script>`, Event-Handler, XXE (Matrix DOC-03) | M | – | ✓ ✓ ✓ ✓ | eigene Regeln, defusedxml | LLM05 |
 ## 4. Ebene C – Code
+| C14 | **Container-Konfiguration:** `privileged`, `docker.sock`-Mount, Host-Netz, `curl \| sh` im Build (Matrix COD-08) | H | – | ✓ ✓ ✓ – | hadolint (Lizenz prüfen), eigene Regeln | ASI05 |
+| C15 | **CI-Workflows:** `pull_request_target` mit fremdem Code, Script-Injection über `${{ github.event.* }}`, ungepinnte Actions (Matrix COD-09) | H | – | ✓ ✓ ✓ – | zizmor (Lizenz prüfen), eigene Regeln | ASI04 |
 ## 6. Ebene E – MCP
+| E08 | **Zu weite Werkzeugrechte in Agent- und Command-Definitionen:** `allowed-tools: Bash(*)` oder alle Tools (Matrix AGT-04) | M | – | ✓ ✓ ✓ ✓ | eigene Regeln | ASI03, LLM06 |
+| E09 | **MCP-Startkonfiguration lädt fremden Code:** `npx -y`, `uvx`, `docker run` mit ungepinntem Paket, `curl \| sh` (H); `http://`-Server (M) (Matrix AGT-06) | H | – | ✓ ✓ ✓ ✓ | eigene Regeln | ASI04, LLM03 |
 ## 8. Ebene G – DSGVO und Rechte
+| G07 | **Personenbezogene Daten in mitgelieferten Dateien:** E-Mail, Telefon, IBAN, Steuer-ID (M); Art.-9-Daten (H) (Matrix DAT-01, COD-02) | M/H | – | ✓ ✓ ✓ – | Regex (S2), Presidio (S3) | DSGVO-Art-5, DSGVO-Art-9 |
+| G08 | **Standort- und Personendaten in Metadaten:** EXIF/XMP mit GPS oder Namen (Matrix DOC-04) | M | – | ✓ ✓ ✓ – | exiftool (Lizenz prüfen) | DSGVO-Art-5 |
 ## 10. Sperrliste
-| Autostart-Dateien mit Befehlen | A02 |
+| Autostart-Dateien mit Befehlen | A02 (inkl. `.pth`, `sitecustomize`, Build-Hooks) |
+| Code-Ausführung beim Laden (neu, Konzept §5 ergänzen) | A16 |
-`SPERRLISTE_KATALOG = {A02, A08, B01, …}`
+`SPERRLISTE_KATALOG = {A02, A08, A16, B01, …, B20}` — B20 dazu, damit eigene Namensregeln
+(`LB-B20-schluesseldatei`) für echte Schlüsseldateien genauso sperren wie `gitleaks:`.
```

### Sprintplanung

```diff
 ### Sprint 2 – Code, MCP, Entwicklerbereich
+| S2-14 | Inventar per Magic als Grundlage der Analyzer-Auswahl; Polyglot/angehängte Daten (A05, A15); Pickle-/safetensors-/GGUF-Magic (Matrix INV-01) | 3 |
+| S2-15 | A-Lücken aus der Matrix: `.pth`, `sitecustomize`, `devcontainer.json`, `prepare`, `pyproject` build-backend, `Justfile`, `uv.toml`, Hook-Muster Netz/Löschen/Zugangsdaten, `.gitattributes`-Treiber, LFS, Doppelendung, reservierte Namen (Matrix AGT-05, COD-05–07, ARC-02, ARC-03, DEP-03) | 5 |
+| S2-16 | B-Lücken: `.mdc`, `.jsonl` in B08–B17; dekodierter Tag-Text und Base64/ROT13/gzip rekursiv erneut prüfen; `allowed-tools` (E08) (Matrix AGT-01–AGT-04, DAT-03) | 3 |
+| S2-17 | MCP-Startkonfiguration `.mcp.json` & Co. (E09) ohne websecureaudit (Matrix AGT-06) | 2 |
+| S2-18 | Pickle-Opcode-Scan ohne Laden (A16/A18), Lizenz und RAM von picklescan vorher in `scanner-tools.md` (Matrix MOD-01) | 3 |
 ### Sprint 3 – Qualität & Start
+| S3-12 | Dokumente und Medien: pdfid, oletools, exiftool, defusedxml (A21, B21, G08); Lizenzen und RAM vorher in `scanner-tools.md` (Matrix DOC-01–DOC-04) | 5 |
+| S3-13 | Modelle: safetensors/GGUF-Header, `auto_map`, `chat_template`-SSTI (A16–A19) (Matrix MOD-04, MOD-06, MOD-07) | 4 |
+| S3-14 | PII in Paketdaten per Regex, Presidio erst nach RAM-Messung (G07) (Matrix DAT-01) | 3 |
 ### Sprint 4 – Register
-| S4-10 | ClamAV im Worker oder auf dem Worker-vServer inkl. Cronjob für Signaturen | 2 |
+| S4-10 | ClamAV im Worker oder auf dem Worker-vServer inkl. Cronjob für Signaturen; YARA-X mit eigenen Regeln schon vorher (Matrix MAL-01, BIN-01) | 2 |
+| S4-11 | Container und CI-Workflows: hadolint, zizmor (C14, C15) nach Lizenzprüfung (Matrix COD-08, COD-09) | 3 |
+| S4-12 | Keras/TF/ONNX-Struktur (A17) mit modelscan (Matrix MOD-02, MOD-03) | 3 |
 ### Offene Entscheidungen (Len)
+- [ ] Verschachtelte Archive eine Ebene tief entpacken (`.whl`, `.dxt`, `.mcpb`, `.vsix`) ja/nein, mit welchen Gesamtlimits (Matrix ARC-01, AGT-09, BIN-02)
+- [ ] Weitere Archivformate (tar/gz sicher mit `tarfile` `filter='data'`; 7z/RAR nur nach Lizenzprüfung)
+- [ ] Schweregrade der Matrix übernehmen oder Katalog behalten (Liste unter „Widersprüche“)
+- [ ] Schnellscan-Umfang: bleibt es bei Konzept §2 (ohne C und DSGVO) oder folgt er der Matrix?
+- [ ] S3-9 „Prüfkatalog“ auf luibui.com streichen (Entscheidung vom 27.09.2026)
```
