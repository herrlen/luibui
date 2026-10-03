# Prüfregeln

Eigene Regeln von luibui (YAML, YARA, Opengrep). Jede Regel hat mindestens einen positiven und
einen negativen Testfall. Regel-IDs: `LB-<Prüfkatalog-ID>-<kurzname>`.

| Ordner | Inhalt | Tests |
|---|---|---|
| `b-muster/` | Anweisungsmuster B08–B17 (YAML, Regex) | Testfälle in jeder Regeldatei |
| `opengrep/` | Code-Regeln C01–C12 für Python, JavaScript/TypeScript und Shell | gleichnamige Testdateien daneben (`# ruleid:` / `# ok:`), `opengrep scan --test rules/opengrep` |
| `yara/` | YARA-X-Regeln für Programmdateien: Schadmuster C10 (Miner, Reverse Shell, Lösegeld, Keylogger, Anti-Analyse), gepackte Programme A04 | Positiv- und Negativfall je Regel in `packages/engine/tests/test_analyzer_a_yara.py` |
| `bandit/` | leere Konfiguration, damit Bandit keine `.bandit` aus dem Paket liest | – |
| `gitleaks/` | gitleaks-Konfiguration für B20 | – |
| `external/` | übernommene Regeln mit eigener Lizenz | – |

Testdateien in `opengrep/` sind entschärfte Nachbildungen wie `corpus/malicious/`: Endpunkte nur
`*.invalid` oder `*.example`, Befehle harmlos (`echo`), erste Zeile `LUIBUI-TESTFIXTURE`.
Opengrep-Regeln brauchen UTF-8: `LANG=C.UTF-8 LC_ALL=C.UTF-8 opengrep scan --test rules/opengrep`.

**Lizenz:** proprietär wie das übrige Repository (siehe `../LICENSE`). Übernommene Regeln in
`external/` behalten ihre eigene Lizenz.
TODO: auf MIT umstellen, sobald Len die Entscheidung freigegeben hat (Konzept §13).
