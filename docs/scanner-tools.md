# Externe Prüfwerkzeuge – Recherche

Stand: **2026-09-26**. Die Angaben beschreiben den Stand an diesem Tag und müssen vor jedem Update neu geprüft werden.

**Methode:** Wir haben ausschließlich Primärquellen gelesen: GitHub-Repositories, LICENSE-Dateien (direkt aus dem Repository, nicht nur den GitHub-Lizenz-Badge), Release-Seiten über die GitHub-API, PyPI-Metadaten, offizielle Dokumentation und die Debian-Paketquellen (sources.debian.org). Kein Werkzeug wurde installiert oder ausgeführt. Versionsnummern und Daten stammen aus der GitHub-Releases-API bzw. der PyPI-JSON-API. Alles, was sich nur aus Sekundärquellen oder gar nicht belegen ließ, ist als **„nicht verifiziert“** gekennzeichnet. RAM-Angaben ohne Herstellerquelle sind Schätzungen und ebenfalls so markiert.

Zielumgebung: Docker-Worker auf Basis von `python:3.12-slim`. Laut `docker-library/python` (versions.json) ist das derzeit Python 3.12.14 auf **Debian 13 „trixie“**. Die Scanner laufen dort ohne Netzwerkzugriff (Sicherheitsregel 5 in `CLAUDE.md`). Die Plattform stand bis 27.09.2026 unter AGPL-3.0 und ist seitdem proprietär.

---

## Lizenz-Warnungen für den Onlinedienst (zuerst lesen)

> **Seit dem Lizenzwechsel (27.09.2026, proprietär):** Fremde Werkzeuge laufen weiter nur als eigene
> Prozesse, nie als eingebundene Bibliothek. Copyleft-Werkzeuge (GPL, z. B. ClamAV) sind damit
> unproblematisch, solange wir die Images nicht an Dritte weitergeben. Die Images auf ghcr.io müssen
> deshalb privat sein; öffentliche Images wären Weitergabe (und enthielten den Quellcode). Die
> Warnungen unten zu AGPL-Kompatibilität sind damit gegenstandslos, die zu Semgrep, Opengrep und
> ATR gelten unverändert.

> **BLOCKER – Semgrep-Registry-Regeln (`semgrep/semgrep-rules`, `p/…`-Regelsätze):** Die Regeln stehen unter der *Semgrep Rules License v1.0*. Dort heißt es wörtlich: *„You may use the rules only for your own internal business purposes. This license does not allow you to distribute the rules, or to make them available to others as a service.“* Eine öffentliche Prüfstelle, die Uploads Dritter mit diesen Regeln prüft, stellt sie „als Dienst“ bereit. **Nicht verwenden**, auch nicht über Opengrep. Das gilt unabhängig davon, dass luibui nicht kommerziell ist.
>
> **RISIKO – `opengrep/opengrep-rules`:** Dieser Fork der Semgrep-Regeln vom 13.12.2024 steht unter LGPL-2.1 **plus „Commons Clause“**. Die Klausel untersagt es, die Regeln zu „verkaufen“, also gegen „fee or other consideration“ einen Dienst anzubieten, dessen Wert im Wesentlichen aus den Regeln stammt. luibui ist kostenlos. Ob Spenden als „other consideration“ gelten, ist juristisch offen. Außerdem ist das Repository seit 2025-11-28 **archiviert**. Empfehlung: nicht verwenden. Wir schreiben eigene Opengrep-Regeln unter `rules/`.
>
> **ClamAV ist GPL-2.0:** Wir rufen es nur als eigenen Prozess auf (`clamscan`/`clamd` über einen Socket) und binden `libclamav` **nicht** in unseren AGPL-Code ein. Eine Einbindung wäre wegen der Inkompatibilität von GPL-2.0-only und AGPL-3.0 problematisch. Geben wir ein Image weiter, gelten die GPL-Quellcodepflichten. Bei Debian-Paketen sind sie über die Debian-Quellen erfüllt.
>
> **ATR-Markenrecht:** Regeln und Engine stehen unter MIT. Die Namen „ATR“, „Agent Threat Rules“, „ATR-Certified“ und „Powered by ATR“ sind davon ausgenommen und fallen unter eine eigene Markenrichtlinie. Im Bericht nennen wir die Quelle nur sachlich, zum Beispiel „Regel ATR-2026-00213“, und verwenden kein Logo und kein Zertifizierungswort.
>
> Alle übrigen Werkzeuge stehen unter MIT, Apache-2.0, BSD-3-Clause oder LGPL-2.1 und werden als separate Prozesse aufgerufen. Daraus ergibt sich kein Lizenzkonflikt mit AGPL-3.0. Die Pflicht zur Namensnennung besteht aber: Lizenztexte gehören in eine `THIRD_PARTY_NOTICES` im Image bzw. Repository.

## Offline-Warnungen (zweitens lesen)

- **Beide Cisco-Scanner hängen von `litellm` ab.** `litellm` lädt beim Start standardmäßig eine Preistabelle von GitHub (Timeout 5 s, danach nimmt es die mitgelieferte Kopie). Deshalb setzen wir **immer** `LITELLM_LOCAL_MODEL_COST_MAP=True`, auch wenn wir kein LLM nutzen. `litellm` war außerdem im März 2026 Ziel eines Lieferkettenangriffs: Die Versionen 1.82.7 und 1.82.8 enthielten Schadcode und wurden zurückgezogen. Darum pinnen wir Versionen per Hash (`pip install --require-hashes`).
- **Cisco mcp-scanner** verwendet ohne `--analyzers` den Standard `api,yara,llm`. `api` ist ein Cloud-Dienst von Cisco, `llm` ein externes LLM. Wir übergeben deshalb **immer** ausdrücklich `--analyzers yara` (optional zusätzlich `prompt_defense,readiness`).
- **Cisco skill-scanner** ist ohne `--use-*`-Flags offline. `--use-osv`, `--use-virustotal`, `--use-aidefense` und `--use-llm`/`--enable-meta` bauen Netzwerkverbindungen auf. `--use-osv` sendet Paketnamen an `https://api.osv.dev/v1/querybatch` und bricht bei Netzfehlern nicht ab, sondern liefert still keine Befunde („fails open“).
- **OSV-Scanner** läuft nur mit `--offline` wirklich offline. Die Datenbank lädt ein Cronjob außerhalb des Scan-Containers.
- **ClamAV-Signaturen** (`freshclam`) und die **OSV-Datenbank** kommen von US-CDNs: Cloudflare (`database.clamav.net`) bzw. Google Cloud Storage. Das sind reine Downloads, bei denen keine Nutzerdaten abfließen. Trotzdem verbindet sich unser Server mit US-Anbietern. **Entscheidung durch Len nötig**, ob das mit „keine US-Dienste“ vereinbar ist.
- Der Worker-Container bekommt grundsätzlich **kein Netzwerk** (`network_mode: none` bzw. eigenes internes Netz). Updates laufen in einem separaten Cron-Container, der nur die Datenbank-Volumes beschreibt.

---

## Übersicht

| Werkzeug | Version (Datum) | Lizenz (LICENSE geprüft) | offline | RAM (ca.) | Ausgabe | Empfehlung |
|---|---|---|---|---|---|---|
| Cisco skill-scanner | 2.1.0 (2026-09-05) | Apache-2.0 | ja, ohne `--use-*`-Flags; `LITELLM_LOCAL_MODEL_COST_MAP=True` setzen | 300–800 MB (nicht verifiziert) | JSON, SARIF, Markdown, HTML, Tabelle | **einsetzen**, nur Kern-Analyzer plus `--use-behavioral` |
| Cisco mcp-scanner | 4.8.4 (2026-08-28) | Apache-2.0 | nur mit `--analyzers yara` und Subbefehl `static`; Standard ist **nicht** offline | 200–500 MB (nicht verifiziert) | JSON (`raw`), Text; **kein SARIF** | **eingeschränkt**: YARA-Regeln nutzbar, Live-Modi verboten |
| ATR – Agent Threat Rules | v4.0.0 (2026-08-23); `main` meldet 4.1.1 | MIT (Marken ausgenommen) | ja (Regeln sind YAML-Dateien) | vernachlässigbar | YAML, Export JSON | **einsetzen**, als Regelquelle mit Qualitätsfilter |
| gitleaks | v8.30.1 (2026-03-21) | MIT | ja | < 200 MB (nicht verifiziert) | JSON, SARIF, CSV, JUnit | **einsetzen**; Nachfolger Betterleaks beobachten |
| OSV-Scanner | v2.6.0 (2026-09-14) | Apache-2.0 (Daten: CC-BY-4.0 u. a.) | ja, mit `--offline` und vorab geladener DB | 200 MB–1 GB je nach DB (nicht verifiziert) | JSON, SARIF, Tabelle u. a. | **einsetzen**, DB per Cron |
| Opengrep | v1.30.0 (2026-09-07) | LGPL-2.1 | ja, mit lokalen Regeldateien | 0,5–2 GB (nicht verifiziert) | JSON, SARIF | **einsetzen, nur eigene Regeln** |
| Semgrep-Registry-Regeln | – | Semgrep Rules License v1.0 | – | – | – | **BLOCKER: nicht verwenden** |
| Bandit | 1.9.4 (2026-02-25) | Apache-2.0 | ja | < 150 MB (nicht verifiziert) | JSON, SARIF (Extra), CSV, XML, HTML u. a. | **einsetzen** |
| ClamAV | 1.5.4 (2026-08-07); Debian trixie: 1.4.x | GPL-2.0 | ja; Signaturen per `freshclam` im Cron | **3–4 GiB empfohlen** (Hersteller) | Text (kein JSON) | **später / optional** (RAM, US-CDN) |
| YARA (libyara) | v4.5.8 (2026-07-28) | BSD-3-Clause | ja | gering | Text; per Python strukturiert | über yara-x statt yara-python |
| yara-python | PyPI 4.5.4 (2025-05-27) | Apache-2.0 | ja | gering | Python-Objekte | nur falls yara-x nicht reicht |
| YARA-X / `yara-x` (PyPI) | v1.20.0 (2026-08-24) | BSD-3-Clause | ja | gering | JSON, Python-Objekte | **bevorzugen** |
| WeasyPrint (PDF) | v70.0 (2026-09-08) | BSD-3-Clause | ja, mit gesperrtem `url_fetcher` | – | PDF | Kandidat |
| ReportLab (PDF) | 5.0.1 (2026-08-20) | BSD-artig (Open-Source-Toolkit) | ja | – | PDF | Kandidat |

---

## 1. Cisco AI Defense – skill-scanner

- **Repository:** https://github.com/cisco-ai-defense/skill-scanner
- **Version:** 2.1.0, veröffentlicht 2026-09-05 (GitHub-Release und PyPI `cisco-ai-skill-scanner`). Davor 2.0.14 (2026-09-01) und 2.0.13 (2026-08-03).
- **Lizenz:** Apache-2.0. Die LICENSE-Datei beginnt mit „Apache License, Version 2.0, January 2004“ und nennt „Copyright 2026 Cisco Systems, Inc. and its affiliates“. GitHub zeigt „NOASSERTION“ an, weil der Copyright-Vermerk im Lizenztext steht. PyPI führt Apache-2.0.
- **Python:** 3.11 bis 3.14. Plattform-Wheels für manylinux x86_64/aarch64 bringen einen kompilierten CEL-Helfer (cel-go) mit.

**Analyzer und Netzwerk** (README, `docs/user-guide/cli-usage.md`, `docs/architecture/analyzers/osv-analyzer.md`):

| Analyzer | Aktivierung | Netzwerk |
|---|---|---|
| Static (YAML- und YARA-Muster, über `yara-x`) | immer an | nein |
| Bytecode (.pyc-Prüfung) | immer an | nein |
| Pipeline (Befehls-Taint) | immer an | nein |
| Correlation | immer an | nein |
| Trigger (vage Beschreibungen) | `--use-trigger` | nein |
| Behavioral (AST-Datenfluss, keine Ausführung) | `--use-behavioral` | nein |
| ATR-Regelpaket | `--rule-packs atr` | nein |
| OSV (Abhängigkeiten) | `--use-osv` | **ja**, `api.osv.dev`, „fails open“ |
| LLM | `--use-llm` | **ja**, LLM-Anbieter über litellm |
| Meta (Falsch-Positiv-Filter per LLM) | `--enable-meta` | **ja** |
| VirusTotal | `--use-virustotal` | **ja**, US-Dienst, **verboten** |
| Cisco AI Defense | `--use-aidefense` | **ja**, Cisco-Cloud, **verboten** |

Die Kern-Analyzer lassen sich nicht abschalten. Alle Netzwerk-Analyzer sind **opt-in**: Ohne die Flags bleibt der Scan offline. Einen expliziten Schalter zum globalen Abschalten gibt es nicht (laut PyPI-Beschreibung). Die Absicherung liegt deshalb bei uns: kein Netzwerk im Container und keine API-Keys in der Umgebung.

Die im Quelltext erwähnte „CEL decision telemetry“ (`--cel-mode shadow`) ist nach der Doku eine lokale Protokollierung von Entscheidungen in der Ausgabe, kein Versand. Dass dabei nichts gesendet wird, ist **nicht verifiziert** (Quelltext nicht vollständig gelesen). Hinweise auf Telemetrie wie PostHog o. Ä. fanden sich per Code-Suche nicht.

**Abhängigkeiten mit Offline-Relevanz:** `litellm>=1.84,<2`, `anthropic`, `openai`, `httpx`, `magika` (Google, lokales ONNX-Modell), `oletools`, `pdfid`, `yara-x`, `fastapi`/`uvicorn`. Der LLM-Handler setzt `LITELLM_LOCAL_MODEL_COST_MAP=True` in mindestens einem Pfad selbst (`llm_request_handler.py`). Wir setzen die Variable trotzdem global.

**LLM über mittwald:** litellm spricht grundsätzlich OpenAI-kompatible Endpunkte an. Ob sich skill-scanner sauber auf `LLM_BASE_URL` (mittwald) umstellen lässt, ist **nicht verifiziert**. Ohnehin gilt Regel 7: Ein LLM-Urteil darf nur Befunde hinzufügen, nie zu Grün führen.

**Installation (python:3.12-slim):**
```
# eigenes venv, damit Abhängigkeiten nicht mit anderen Scannern kollidieren
python -m venv /opt/skill-scanner && /opt/skill-scanner/bin/pip install --require-hashes -r skill-scanner.lock
# lock enthält: cisco-ai-skill-scanner==2.1.0 (+ Abhängigkeiten mit Hashes), OHNE Extras [all]/[bedrock]/[google]/[vertex]/[azure]
```

**Aufruf:**
```
LITELLM_LOCAL_MODEL_COST_MAP=True skill-scanner scan /scratch/<job-id>/pkg \
  --use-behavioral --format sarif --output /scratch/<job-id>/out/skill-scanner.sarif
# Alternativ --format json. Für Pakete ohne SKILL.md: --lenient
```
Exit-Code 0 = Lauf erfolgreich, 1 = Fehler (oder Befunde, wenn `--fail-on-findings` gesetzt ist; das nutzen wir nicht).

**Risiken:**
- Großer Abhängigkeitsbaum (LLM-SDKs, FastAPI, Textual) vergrößert die Angriffsfläche im Worker.
- Die mitgelieferten YARA- und YAML-Regeln sind Teil des Apache-Pakets. Ob einzelne Regeln aus Drittquellen mit abweichender Lizenz stammen, ist **nicht verifiziert**.
- Die Doku sagt selbst: „A scan that returns no findings does not guarantee that a skill is free of all threats.“ Das passt zu unserer Formulierung „Keine bekannten Befunde“.

Quellen (abgerufen am 2026-09-26):
- https://github.com/cisco-ai-defense/skill-scanner
- https://github.com/cisco-ai-defense/skill-scanner/releases
- https://raw.githubusercontent.com/cisco-ai-defense/skill-scanner/main/LICENSE
- https://github.com/cisco-ai-defense/skill-scanner/blob/main/docs/user-guide/cli-usage.md
- https://github.com/cisco-ai-defense/skill-scanner/blob/main/docs/architecture/analyzers/osv-analyzer.md
- https://pypi.org/project/cisco-ai-skill-scanner/

## 2. Cisco AI Defense – mcp-scanner

- **Repository:** https://github.com/cisco-ai-defense/mcp-scanner
- **Version:** 4.8.4, veröffentlicht 2026-08-28 (GitHub-Release und PyPI `cisco-ai-mcp-scanner`). Davor 4.8.3 (2026-08-07).
- **Lizenz:** Apache-2.0 (LICENSE geprüft, Standardtext mit Platzhalter-Copyright).
- **Python:** ≥ 3.11.4.

**Analyzer und Netzwerk** (README, `mcpscanner/cli.py`):

| Analyzer | Netzwerk | Anmerkung |
|---|---|---|
| `yara` | nein | mitgelieferte YARA-Regeln (über `yara-python`), eigene Regeln möglich |
| `prompt_defense` | nein | regex-basiert; laut Doku am Beispiel mit `--server-url` |
| `readiness` | nein | 20 Heuristiken; laut Doku am Beispiel mit `--server-url` |
| `llm` | **ja** | externes LLM über litellm (`MCP_SCANNER_LLM_API_KEY`) |
| `api` | **ja** | Cisco AI Defense Cloud (`MCP_SCANNER_API_KEY`) |
| `virustotal` | **ja** | US-Dienst, **verboten** |
| Subbefehl `behavioral` / `supplychain` | **ja** | nutzt ein LLM für den Abgleich zwischen Doku und Code |
| Subbefehle `pypi-scan`, `npm-scan`, `vulnerable-package` | **ja** | laden Pakete bzw. fragen über pip-audit PyPI/OSV ab |

**Wichtig:** In `cli.py` ist `default="api,yara,llm"` für `--analyzers` gesetzt. Ohne das Flag würde der Scanner also Cloud-Dienste ansprechen, oder er scheitert, wenn keine Keys vorhanden sind. Wir übergeben daher **immer** `--analyzers yara`.

**Grundsätzliche Einschränkung für luibui:** Die Hauptmodi verbinden sich mit einem **laufenden** MCP-Server (`--server-url`, stdio, Config-Dateien). Beim stdio-Modus würde der Scanner den hochgeladenen Server **starten**. Das verstößt gegen Sicherheitsregel 1 und ist verboten. Offline bleibt nur `static`, und dieser Modus erwartet vorab erzeugte JSON-Listen (`tools/list`, `prompts/list`, `resources/list`). Diese Listen müssten wir selbst durch statisches Parsen des Pakets erzeugen, etwa aus Tool-Definitionen im Quelltext oder aus Manifesten. Das geht nicht vollständig und ist nur eine Näherung.

**Installation (python:3.12-slim):**
```
python -m venv /opt/mcp-scanner && /opt/mcp-scanner/bin/pip install --require-hashes -r mcp-scanner.lock
# cisco-ai-mcp-scanner==4.8.4; pinnt litellm==1.93.0, bringt yara-python und tree-sitter-Grammatiken mit
```
Die Doku empfiehlt `uv tool install --python 3.13 cisco-ai-mcp-scanner`. Für 3.12 reicht die Anforderung ≥ 3.11.4.

**Aufruf:**
```
LITELLM_LOCAL_MODEL_COST_MAP=True mcp-scanner --analyzers yara --format raw \
  --output /scratch/<job-id>/out/mcp-scanner.json \
  static --tools /scratch/<job-id>/derived/tools-list.json
```
Globale Flags stehen vor dem Subbefehl. Formate: `raw` (JSON), `summary`, `detailed`, `by_tool`, `by_analyzer`, `by_severity`, `table`. **Kein SARIF.** Ob `prompt_defense`/`readiness` auch im `static`-Modus greifen, ist **nicht verifiziert**.

**Risiken:** Der Nutzen ist ohne Live-Server begrenzt. Pragmatischer ist es, nur die YARA-Regeln aus `mcpscanner/data/yara_rules/` (Apache-2.0) mit unserer eigenen YARA-Einbindung zu verwenden, mit Namensnennung. Das spart die schwere Abhängigkeit (litellm, mcp, 10 tree-sitter-Grammatiken).

Quellen (abgerufen am 2026-09-26):
- https://github.com/cisco-ai-defense/mcp-scanner
- https://github.com/cisco-ai-defense/mcp-scanner/releases
- https://raw.githubusercontent.com/cisco-ai-defense/mcp-scanner/main/LICENSE
- https://github.com/cisco-ai-defense/mcp-scanner/blob/main/mcpscanner/cli.py
- https://pypi.org/project/cisco-ai-mcp-scanner/

## 3. ATR – Agent Threat Rules

- **Repository:** https://github.com/Agent-Threat-Rule/agent-threat-rules
- **Version:** Das letzte Release ist **v4.0.0 vom 2026-08-23** (Release-Text: „785 detection rules across 9 threat categories“). Parallel erschien `pyatr-v0.3.0` (2026-08-23). Auf dem Branch `main` steht in `package.json` und `stats.json` bereits **4.1.1**, erzeugt am 2026-09-22, aber noch ohne Release.
- **Regelzahl** (`stats.json` auf `main`, 2026-09-22): 825 gesamt, **818 wirksam** („effective“), 7 inaktiv, 10 Kategorien, davon prompt-injection 250, context-exfiltration 133, tool-poisoning 113, agent-manipulation 108, privilege-escalation 76, skill-compromise 52, model-abuse 41, excessive-autonomy 39, data-poisoning 9, model-security 4. Das README nennt andere Zahlen (683 „live“ / 825). Die Zahlen im Projekt sind also nicht einheitlich. Die „~818“ aus unserer Planung entsprechen der Zahl der wirksamen Regeln, und zwar für **alle** Kategorien, nicht nur Prompt Injection.
- **Lizenz:** MIT („Copyright (c) 2026 ATR Contributors“, LICENSE geprüft; `package.json`: `"license": "MIT"`). Die Markenrichtlinie (`TRADEMARK.md`, gültig seit 2026-05-16) stellt klar, dass Regeln, Schema, Konformitätstests und Engine unter MIT stehen, die **Marken aber nicht**. Die Marken sind beim USPTO angemeldet.
- **Format:** Eine YAML-Datei pro Regel unter `rules/<kategorie>/ATR-YYYY-NNNNN-<name>.yaml`, Schema in `spec/atr-schema.yaml`. Wichtige Felder: `id`, `title`, `status`, `maturity` (z. B. `test`, `experimental`, `stable`), `severity`, `references` (OWASP LLM/Agentic, MITRE ATLAS), `tags.scan_target` (z. B. `mcp`), `detection.conditions[]` mit `field`, `operator` (u. a. `regex`) und `value`, sowie **`test_cases.true_positives` / `true_negatives`**. Laut README sind bei `experimental` mindestens 1 und bei `stable` mindestens 5 Testfälle je Richtung vorgeschrieben. Die Testfälle passen damit zu unserer Regel „jede Regel mit positivem und negativem Test“.
- **Nutzung:** npm `agent-threat-rules` (TypeScript-Engine plus CLI), PyPI `pyatr` 0.3.0 (MIT, Python ≥ 3.10, „Layer 1 regex detection“), GitHub Action, Docker-Image `ghcr.io/agent-threat-rule/agent-threat-rules`, Exporte (generic-regex JSON, Splunk, Elasticsearch). Der Cisco skill-scanner kann ATR über `--rule-packs atr` einbinden.
- **Offline:** Die Regeln sind statische Dateien. Die Engine hat laut README eine opt-in-Cloud-Meldung (`--report-to-cloud`, `ATR_TC_URL`), die wir nie aktivieren.
- **RAM:** vernachlässigbar (Regex-Matching).

**Empfehlung:** Einen festen Stand (Git-Tag `v4.0.0`) per Commit-Hash in `rules/external/atr/` übernehmen. Die Regeln laden wir mit einem eigenen schmalen Python-Adapter (YAML lesen, Regex mit Timeout über das Modul `regex` o. Ä. gegen ReDoS) oder über `pyatr`. Die mitgelieferten `test_cases` laufen in unserer CI mit. Rule-IDs behalten das Präfix `ATR-…`.

**Risiken:**
- Viele Regeln tragen `author: "ATR Threat Cloud Crystallization"` und `maturity: test`. Sie sind also automatisch erzeugt und wenig gereift. Wir übernehmen vorerst nur `stable` (evtl. `experimental`) und messen die Falsch-Positiv-Rate an `corpus/benign/`.
- Die eigenen Benchmark-Angaben des Projekts sind uneinheitlich. `stats.json` kommentiert selbst, dass eine Präzisionszahl „a floor, not a precision measurement“ ist.
- Regex aus Drittquelle heißt ReDoS-Gefahr. Deshalb brauchen wir Timeouts pro Regel.

Quellen (abgerufen am 2026-09-26):
- https://github.com/Agent-Threat-Rule/agent-threat-rules
- https://github.com/Agent-Threat-Rule/agent-threat-rules/releases/tag/v4.0.0
- https://raw.githubusercontent.com/Agent-Threat-Rule/agent-threat-rules/main/LICENSE
- https://github.com/Agent-Threat-Rule/agent-threat-rules/blob/main/TRADEMARK.md
- https://github.com/Agent-Threat-Rule/agent-threat-rules/blob/main/stats.json
- https://github.com/Agent-Threat-Rule/agent-threat-rules/blob/main/rules/prompt-injection/ATR-2026-00213-system-prompt-override.yaml

## 4. gitleaks

- **Repository:** https://github.com/gitleaks/gitleaks
- **Version:** v8.30.1, veröffentlicht 2026-03-21. Davor v8.30.0 (2025-11-26).
- **Lizenz:** MIT („Copyright (c) 2019 Zachary Rice“, LICENSE geprüft).
- **Status:** Laut README ist gitleaks **„feature-complete“**. Es kommen nur noch Sicherheitskorrekturen, die Weiterentwicklung läuft in **Betterleaks** (https://github.com/betterleaks/betterleaks, MIT, v1.8.1 vom 2026-08-18, gleicher Autor, laut Projekt kompatibel zu Konfiguration und CLI von gitleaks). Betterleaks bringt u. a. CEL-basierte **Validierung** von Secrets mit. Diese Funktion würde echte Zugangsdaten gegen Live-APIs testen und muss bei uns aus bleiben. Ob Betterleaks ohne Validierung vollständig offline läuft, ist **nicht verifiziert**.
- **Offline:** ja. Reine Regex-/Entropie-Prüfung ohne Netzwerkaufrufe. Telemetrie ist nicht dokumentiert. Dass es keine gibt, stützt sich auf die Doku und ist **nicht per Code-Audit verifiziert**.
- **RAM:** Schätzung < 200 MB bei unseren Größen (max. 200 MB entpackt), **nicht verifiziert**.
- **Installation (python:3.12-slim):** Debian trixie liefert nur 8.16.0, deshalb laden wir das offizielle Binary beim Image-Build und prüfen die Prüfsumme:
  ```
  curl -fsSLO https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_x64.tar.gz
  curl -fsSLO https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_checksums.txt
  sha256sum --ignore-missing -c gitleaks_8.30.1_checksums.txt && tar -xzf gitleaks_8.30.1_linux_x64.tar.gz -C /usr/local/bin gitleaks
  ```
- **Aufruf** (Verzeichnis ohne Git, Subbefehl `dir` laut README):
  ```
  gitleaks dir /scratch/<job-id>/pkg --no-banner --redact \
    --report-format json --report-path /scratch/<job-id>/out/gitleaks.json --exit-code 0
  ```
  Formate: JSON, CSV, JUnit, SARIF, eigenes Go-Template. Die Flag-Namen stammen aus Doku und Erfahrung. Vor dem Einbau prüfen wir sie mit `gitleaks dir --help` (**nicht ausgeführt**).
- **Risiken:** `--redact` ist Pflicht, weil Secrets sonst im Klartext im Report landen. Zusätzlich maskieren wir selbst (Regel 6).

Quellen (abgerufen am 2026-09-26):
- https://github.com/gitleaks/gitleaks
- https://github.com/gitleaks/gitleaks/releases
- https://raw.githubusercontent.com/gitleaks/gitleaks/master/LICENSE
- https://github.com/betterleaks/betterleaks
- https://www.helpnetsecurity.com/2026/03/19/betterleaks-open-source-secrets-scanner/ (Sekundärquelle zu Betterleaks)

## 5. OSV-Scanner mit Offline-Datenbank

- **Repository:** https://github.com/google/osv-scanner
- **Version:** v2.6.0, veröffentlicht 2026-09-14. Davor v2.5.1 (2026-08-17) und v2.5.0 (2026-08-07). In v2.5.1 wurde laut Release-Notes die Unterstützung für `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` **wiederhergestellt**. Mindestversion ist deshalb 2.5.1.
- **Lizenz:** Apache-2.0 (LICENSE geprüft). **Daten:** Die OSV-Einträge haben je nach Quelle eigene Lizenzen, u. a. GitHub Advisory DB, PyPI, Go, OSS-Fuzz und PSF unter CC-BY-4.0, RustSec und GSD unter CC0-1.0, Ubuntu unter **CC-BY-SA-4.0**, OpenSSF Malicious Packages unter Apache-2.0. Zeigen wir Advisory-Texte im Bericht an, brauchen wir eine **Quellenangabe (CC-BY)** mit Link auf die Advisory-ID.
- **Offline-Modus** (offizielle Doku):
  - `--offline`: nur lokale Datenbank, keine Netzwerkzugriffe, keine Updates.
  - `--offline-vulnerabilities`: Schwachstellen offline, andere Funktionen dürfen weiter ins Netz. Für den Worker **nicht ausreichend**.
  - `--download-offline-databases`: lädt die lokale DB bzw. aktualisiert sie. Das gehört nur in den Cron-Container.
  - Speicherort: `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY`, Struktur `{dir}/osv-scanner/{ecosystem}/all.zip`.
  - Einschränkungen offline: kein Commit-Level-Scan. Die Auflösung transitiver Abhängigkeiten braucht Netz und entfällt. Wir scannen nur Lockfiles und Manifeste, zusätzlich mit `--no-resolve`. Ob `--licenses` offline funktioniert (vermutlich über deps.dev), ist **nicht verifiziert**. Wir nutzen es nicht.
- **DB-Download für Cron:** entweder `osv-scanner scan --offline-vulnerabilities --download-offline-databases …` gegen ein Dummy-Lockfile im Cron-Container, oder direkt per HTTP: `https://osv-vulnerabilities.storage.googleapis.com/<ECOSYSTEM>/all.zip` (Liste: `…/ecosystems.txt`). Für uns relevant sind mindestens `PyPI`, `npm`, `Go`, `crates.io`. Die Dateien schreibt der Cron atomar in das Volume (erst in eine temporäre Datei, dann umbenennen). Der Worker mountet das Volume read-only.
- **RAM:** Wird nicht angegeben, **nicht verifiziert**. Die `all.zip` für npm und PyPI sind groß und werden beim Scan geladen. Wir planen 0,5–1 GB ein und messen nach dem ersten Deploy (`docs/infra-kapazitaet.md`).
- **Installation (python:3.12-slim):** Es gibt kein Debian-Paket. Wir laden das Binary `osv-scanner_linux_amd64` aus dem Release und prüfen es gegen `osv-scanner_SHA256SUMS`.
- **Aufruf:**
  ```
  OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY=/var/lib/osv \
  osv-scanner scan source -r --offline --no-resolve --format json \
    --output-file /scratch/<job-id>/out/osv.json /scratch/<job-id>/pkg
  ```
  Formate u. a. `table`, `json`, `sarif`, `markdown`. Ob der v2-Subbefehl `scan source` Pflicht ist oder `scan -r` genügt, ist nicht ganz eindeutig (die Doku zeigt beides), ebenso die Exit-Codes. Beides prüfen wir vor dem Einbau (**nicht verifiziert**).
- **Risiken:** Ob die DB aktuell ist, hängt am Cron. Im Bericht nennen wir das Datum des DB-Stands. Download-Quelle ist Google Cloud Storage (US-Anbieter, siehe Offline-Warnungen).

Quellen (abgerufen am 2026-09-26):
- https://github.com/google/osv-scanner
- https://github.com/google/osv-scanner/releases
- https://google.github.io/osv-scanner/usage/offline-mode/
- https://google.github.io/osv-scanner/usage/
- https://google.github.io/osv.dev/data/

## 6. Opengrep und die Lizenz der Semgrep-Regeln

### Opengrep (Engine)
- **Repository:** https://github.com/opengrep/opengrep
- **Version:** v1.30.0 vom 2026-09-07 ist das letzte stabile Release. Danach kamen nur Vorabversionen: `v1.30.1-candidate` (2026-09-21) und `v2.0.0-nopython-interfile.alpha.3` (2026-09-11). Wir nutzen nur stabile Releases.
- **Lizenz:** LGPL-2.1 (LICENSE geprüft). Wir rufen Opengrep als eigenständiges Binary auf und linken nichts. Das ist mit AGPL unproblematisch.
- **Offline:** Mit lokalen Regeldateien (`-f`/`--config <pfad>`) braucht Opengrep kein Netz. Registry-Code (`Semgrep_Registry.ml`, `Rule_fetching.ml`) ist noch vorhanden und greift bei `--config auto` oder `p/…`. Diese Optionen verwenden wir **nie**. Im Quellbaum gibt es keine Dateien mit „metrics“/„telemetry“ im Namen, das Metrik-Modul von Semgrep scheint entfernt zu sein. Eine vollständige Prüfung war das nicht (**nicht verifiziert**). Der Container ohne Netz sichert zusätzlich ab.
- **RAM:** **nicht verifiziert**. Die OCaml-Engine braucht je nach Regelzahl und Dateigröße erfahrungsgemäß einige hundert MB bis 2 GB. Wir begrenzen mit `--max-memory` bzw. `--timeout` (Flags von Semgrep geerbt, Verfügbarkeit **nicht verifiziert**) und über das Speicherlimit des Containers.
- **Installation (python:3.12-slim):** Die Opengrep-Binaries sind glibc-basiert (manylinux), also passend für Debian: `opengrep_manylinux_x86` (ca. 46 MB) aus dem Release laden. Signatur und Zertifikat (`.sig`, `.cert`, Sigstore/cosign) prüfen. Das `install.sh` per `curl | bash` aus dem README verwenden wir **nicht**.
- **Aufruf:**
  ```
  opengrep scan -f /opt/luibui/rules/opengrep/ --json \
    --sarif-output=/scratch/<job-id>/out/opengrep.sarif /scratch/<job-id>/pkg > /scratch/<job-id>/out/opengrep.json
  ```
  Ausgabe: JSON und SARIF laut README (`--sarif-output=` ist dort belegt). Weitere Flags gleichen wir vor dem Einbau mit `--help` ab.

### Semgrep-Registry-Regeln – **BLOCKER**
- `https://github.com/semgrep/semgrep-rules`: Die LICENSE-Datei enthält nur den Satz *„Semgrep Rules License v1.0. For more details, visit https://semgrep.dev/legal/rules-license“*.
- Wortlaut aus https://semgrep.dev/legal/rules-license (Lizenzgeber: Semgrep, Inc.):
  - Lizenzerteilung: *„The licensor grants you a non-exclusive, royalty-free, worldwide, non-sublicensable, non-transferable license to use the rules, subject to the limitations and conditions below.“*
  - **Einschränkung:** *„You may use the rules only for your own internal business purposes. This license does not allow you to distribute the rules, or to make them available to others as a service.“*
  - Änderungen: *„If you modify the rules, you must include in any modified copies of the rules prominent notices stating that you have modified the rules.“*
  - Beendigung: *„If you use the rules in violation of these terms, such use is not licensed, and your licenses will automatically terminate.“*
- **Bewertung für luibui:** Wer Pakete Dritter prüft und ihnen Befunde auf Basis dieser Regeln liefert, stellt die Regeln „als Dienst“ bereit. Das ist ausdrücklich nicht erlaubt. Einbinden in ein AGPL-Repository wäre zusätzlich eine unzulässige Weitergabe. **Keine Semgrep-Registry-Regeln verwenden, auch nicht als Vorlage zum Abschreiben.** Diese Einschätzung ist keine Rechtsberatung, der Wortlaut ist aber eindeutig.
- **`opengrep/opengrep-rules`:** Fork vom 13.12.2024 unter LGPL-2.1 **mit Commons Clause** (Verkaufsverbot, „Sell“ umfasst auch „other consideration“). Seit 2025-11-28 archiviert. Nicht verwenden (siehe oben).
- **Konsequenz:** Alle Opengrep-Regeln unter `rules/` schreiben wir selbst (Lizenz nach unserer Entscheidung: MIT oder AGPL), jeweils mit Testfällen.

Quellen (abgerufen am 2026-09-26):
- https://github.com/opengrep/opengrep
- https://github.com/opengrep/opengrep/releases
- https://github.com/opengrep/opengrep/blob/main/CHANGELOG.md
- https://github.com/semgrep/semgrep-rules/blob/develop/LICENSE
- https://semgrep.dev/legal/rules-license
- https://github.com/opengrep/opengrep-rules (LICENSE mit Commons Clause)

## 7. Bandit

- **Repository:** https://github.com/PyCQA/bandit
- **Version:** 1.9.4, veröffentlicht 2026-02-25 (GitHub und PyPI). Debian trixie liefert nur 1.7.10, deshalb installieren wir über pip.
- **Lizenz:** Apache-2.0 (LICENSE geprüft, PyPI `Apache-2.0`).
- **Python:** ≥ 3.10.
- **Offline:** ja. Bandit parst den Python-Code zu einem AST und führt ihn nicht aus. Das entspricht dem bekannten Funktionsprinzip, im gelesenen Doku-Auszug war es nicht wörtlich belegt. Netzwerk oder Telemetrie gibt es nicht.
- **RAM:** Schätzung < 150 MB, **nicht verifiziert**.
- **Installation:** `pip install "bandit[sarif,toml]==1.9.4"` im eigenen venv (SARIF braucht das Extra `sarif`).
- **Aufruf:**
  ```
  bandit -r /scratch/<job-id>/pkg -f json -o /scratch/<job-id>/out/bandit.json --exit-zero
  ```
  Formate u. a. `json`, `sarif` (mit Extra), `csv`, `xml`, `html`, `yaml`, `txt`. Ob `--exit-zero` in 1.9.4 vorhanden ist, prüfen wir vor dem Einbau mit `--help` (**nicht verifiziert**).
- **Risiken:** Bandit prüft nur Python und erzeugt viele Befunde mit niedrigem Schweregrad. Im Scoring mappen wir die Schweregrade konservativ. Sehr große oder bösartig verschachtelte Python-Dateien können den Parser stark belasten. Das fangen wir mit Timeout und Dateigrößenlimit ab.

Quellen (abgerufen am 2026-09-26):
- https://github.com/PyCQA/bandit
- https://github.com/PyCQA/bandit/releases
- https://bandit.readthedocs.io/en/latest/start.html
- https://pypi.org/project/bandit/

## 8. ClamAV

- **Repository:** https://github.com/Cisco-Talos/clamav
- **Version:** clamav-1.5.4 und die LTS-Version clamav-1.4.6, beide vom 2026-08-07. Debian trixie hat laut sources.debian.org 1.4.3 (forky/sid: 1.4.6). Debian aktualisiert ClamAV üblicherweise über `trixie-updates`. Den genauen Stand in trixie-updates haben wir **nicht verifiziert**.
- **Lizenz:** GPL-2.0 (`COPYING.txt` geprüft). Siehe Lizenz-Warnung oben: nur als eigener Prozess nutzen. Die Lizenz der **Signaturdatenbanken** ist in der gelesenen Doku nicht geregelt (**nicht verifiziert**).
- **RAM (offizielle Doku):** Das Laden der Signaturen braucht „upwards of 1.2 GiB“. Beim täglichen Reload mit `ConcurrentDatabaseReload` kurzzeitig etwa **2,4 GiB**. Die Empfehlung für Server/Docker lautet **mindestens 3 GiB, besser 4 GiB**. Senken lässt sich das mit `ConcurrentDatabaseReload no` (Scans blockieren während des Reloads) und `TestDatabases no` in freshclam.conf. **Für den geteilten mittwald-Server ist das der größte RAM-Posten.** Vor dem Einsatz Kapazität in `docs/infra-kapazitaet.md` prüfen.
- **Offline:** Der Scan selbst ist offline. Die Signaturen aktualisiert `freshclam` von `database.clamav.net` (laut Doku über **Cloudflare-CDN** ausgeliefert). Laut Doku gelten Rate-Limits, und scriptgesteuerte Downloads per curl/wget sind „explicitly denied“. Als Alternative gibt es das offiziell unterstützte `cvdupdate` für einen eigenen Spiegel. Veraltete ClamAV-Versionen werden nach dem EOL-Termin ggf. von Updates ausgesperrt.
- **Installation (python:3.12-slim):** `apt-get install --no-install-recommends clamav clamav-daemon clamav-freshclam`. Besser ist ein **eigener Container** `clamav/clamav:<version>_base` (offizielles Image ohne DB, Signaturen per Volume). Der Worker spricht `clamd` dann über einen Unix-Socket bzw. ein internes Netz an. Das offizielle Image ist Alpine-basiert. Das ist unkritisch, weil es ein eigener Container ist.
- **Aufruf:**
  ```
  clamdscan --fdpass --no-summary --infected /scratch/<job-id>/pkg     # mit laufendem clamd
  # oder ohne Daemon (lädt die DB bei jedem Aufruf neu, langsam):
  clamscan -r --no-summary --infected /scratch/<job-id>/pkg
  ```
  Die Ausgabe ist **Text** im Format `<pfad>: <Signatur> FOUND`, **kein JSON**. Wir parsen sie im Adapter. Exit-Codes: 0 = sauber, 1 = Fund, 2 = Fehler (Standardverhalten, hier **nicht verifiziert**).
- **Empfehlung:** Zunächst zurückstellen, wegen RAM und US-CDN. Für KI-Skills (überwiegend Text und Skripte) ist der Zusatznutzen begrenzt, relevant wird ClamAV bei mitgelieferten Binärdateien. Außerdem gilt: „Bekannte Schadsoftware wird nie abgelegt“ (Regel 10). Diese Regel setzt faktisch einen Malware-Scan **vor** der Ablage voraus. Ohne ClamAV brauchen wir eine andere Lösung, z. B. YARA-Regeln oder eine Hash-Liste. **Entscheidung durch Len.**

Quellen (abgerufen am 2026-09-26):
- https://github.com/Cisco-Talos/clamav
- https://github.com/Cisco-Talos/clamav/releases
- https://raw.githubusercontent.com/Cisco-Talos/clamav/main/COPYING.txt
- https://docs.clamav.net/manual/Installing/Docker.html
- https://docs.clamav.net/faq/faq-freshclam.html
- https://sources.debian.org/src/clamav/

## 9. YARA, yara-python und YARA-X

- **YARA (libyara):** https://github.com/VirusTotal/yara, v4.5.8 vom 2026-07-28. Lizenz BSD-3-Clause (`COPYING` geprüft). Das README sagt ausdrücklich: **„This project is in maintenance mode.“** Der Nachfolger ist YARA-X. Debian trixie: `yara` 4.5.2.
- **yara-python:** https://github.com/VirusTotal/yara-python, Lizenz Apache-2.0 (LICENSE geprüft). Auf **PyPI ist 4.5.4 (2025-05-27) aktuell**. Auf GitHub gibt es zwar ein Tag `v4.5.5` (2026-04-22), aber kein passendes PyPI-Release. Debian trixie: `python3-yara` 4.5.1. Die PyPI-Wheels bringen libyara statisch mit.
- **YARA-X:** https://github.com/VirusTotal/yara-x, v1.20.0 vom 2026-08-24, Lizenz BSD-3-Clause (LICENSE geprüft). Die Python-Bindings stehen auf PyPI als `yara-x` 1.20.0 (2026-08-24). Die Lizenz ist in den PyPI-Metadaten nicht gesetzt. Maßgeblich ist das Repository. Der Cisco skill-scanner nutzt bereits `yara-x`.
- **Offline:** ja, reine lokale Mustererkennung. RAM ist gering und wächst mit der Regelzahl (keine Herstellerangabe).
- **Installation (python:3.12-slim):** `pip install yara-x==1.20.0` (Wheels für manylinux vorhanden, Stand **nicht einzeln verifiziert**). Fallback: `pip install yara-python==4.5.4`.
- **Aufruf (Python, im eigenen Adapter):**
  ```python
  import yara_x

  rules = yara_x.compile(open("rules/yara/all.yar").read())
  scanner = yara_x.Scanner(rules)
  scanner.set_timeout(10)
  results = scanner.scan_file(path)  # Treffer: results.matching_rules
  ```
  Die API ist nach der YARA-X-Doku skizziert und vor der Umsetzung zu prüfen (**nicht verifiziert**). YARA-X ist in der Syntax weitgehend, aber nicht vollständig kompatibel zu YARA 4. Fremde Regeln (z. B. aus mcp-scanner) müssen wir mit `yr check` bzw. beim Kompilieren prüfen.
- **Risiken:** Regeln aus Drittquellen haben eigene Lizenzen. Große öffentliche YARA-Sammlungen (z. B. von Florian Roth/Nextron) stehen teils unter der **Detection Rule License (DRL)** mit Namensnennungspflicht. Das ist hier nicht geprüft, vor Übernahme also einzeln kontrollieren.

Quellen (abgerufen am 2026-09-26):
- https://github.com/VirusTotal/yara
- https://github.com/VirusTotal/yara-python
- https://pypi.org/project/yara-python/
- https://github.com/VirusTotal/yara-x
- https://pypi.org/project/yara-x/
- https://sources.debian.org/src/yara/ , https://sources.debian.org/src/yara-python/

## Anhang: PDF-Bibliothek (für später)

- **WeasyPrint** v70.0 (2026-09-08), BSD-3-Clause (LICENSE geprüft). Die Bibliothek setzt HTML/CSS in PDF um und braucht Pango/HarfBuzz aus Debian (`libpango-1.0-0`, `libpangoft2-1.0-0`). **Achtung:** WeasyPrint lädt standardmäßig externe Ressourcen (Bilder, CSS, Fonts per URL). Für Regel 12 müssen wir einen eigenen `url_fetcher` setzen, der alles außer eingebetteten lokalen Fonts und Assets ablehnt. Belege bleiben escaped Text.
- **ReportLab** 5.0.1 (2026-08-20), BSD-artige Lizenz laut PyPI („BSD license (see license.txt …)“). Das Open-Source-Toolkit ist frei, „ReportLab PLUS“ ist ein kommerzielles Zusatzprodukt, das wir nicht brauchen. ReportLab zeichnet PDFs programmatisch ohne HTML-Engine und lädt dabei nichts nach. Das ist das kleinere Risiko, macht aber mehr Layoutarbeit.
- Beide sind mit AGPL-3.0 verträglich. Die Entscheidung fällt mit dem PDF-Task.

Quellen (abgerufen am 2026-09-26):
- https://github.com/Kozea/WeasyPrint
- https://pypi.org/project/weasyprint/
- https://pypi.org/project/reportlab/

## Anhang: litellm-Lieferkettenvorfall (Kontext für die Cisco-Scanner)

Am 2026-03-24 standen auf PyPI die kompromittierten Versionen `litellm` 1.82.7 und 1.82.8 bereit. Eine `.pth`-Datei stahl Zugangsdaten und legte eine Hintertür an. PyPI stellte das Paket noch am selben Tag unter Quarantäne. Die heute von den Cisco-Scannern verlangten Versionen (≥ 1.84 bzw. ==1.93.0) sind davon nicht betroffen. Der Vorfall ist aber ein Argument für Hash-Pinning, eigene venvs pro Scanner und einen Worker ohne Netz und ohne Secrets in der Umgebung.

Quellen (abgerufen am 2026-09-26):
- https://docs.litellm.ai/blog/security-update-march-2026
- https://github.com/BerriAI/litellm/issues/24518
- https://docs.litellm.ai/docs/proxy/custom_model_cost_map
