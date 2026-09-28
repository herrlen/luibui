# Drittanbieter-Komponenten

luibui nutzt die folgenden Werke Dritter. Die Lizenztexte liegen jeweils daneben oder sind
verlinkt. Namen und Marken der Projekte gehören ihren Inhabern; luibui nennt sie nur sachlich.

| Komponente | Version | Lizenz | Wo | Einsatz |
|---|---|---|---|---|
| Agent Threat Rules (Regeldateien) | v4.0.0, Commit `464548b` | MIT, Marken ausgenommen | `rules/external/atr/` (Lizenz: `rules/external/atr/LICENSE`) | Muster für B08–B17, nur Regex-Regeln, siehe `rules/external/atr/QUELLE.md` |
| MalwareBazaar SHA-256-Liste (Daten) | täglich | Nutzungsbedingungen von abuse.ch, https://bazaar.abuse.ch/faq/#tos (kostenlos, Fair Use, nicht-kommerziell) | vom Worker nach `/rules/malware/sha256.bin` geladen, nicht im Repository | bekannte Schadsoftware (A08), nur Hash-Abgleich |
| gitleaks (Programm) | 8.30.1 | MIT | im Worker-Image unter `/usr/local/bin/gitleaks`, Quelle https://github.com/gitleaks/gitleaks | Secrets (B20), als eigener Prozess |
| osv-scanner (Programm) | 2.6.0 | Apache-2.0 (Daten: CC-BY-4.0 u. a.) | im Worker-Image unter `/usr/local/bin/osv-scanner`, Quelle https://github.com/google/osv-scanner | bekannte Schwachstellen und Schadpakete (D), als eigener Prozess, offline |
| Opengrep (Programm) | 1.30.0 | LGPL-2.1 | im Worker-Image unter `/usr/local/bin/opengrep`, Quelle https://github.com/opengrep/opengrep | Code-Analyse (C01–C12), als eigener Prozess, nur mit eigenen Regeln aus `rules/opengrep/` (keine Semgrep- oder Opengrep-Regelsammlungen) |
| Bandit (Python-Paket) | 1.9.4 | Apache-2.0 | Abhängigkeit von `luibui-scan`, Quelle https://github.com/PyCQA/bandit | Code-Analyse für Python (C01, C02, C11, C13), als eigener Prozess |

Python-Abhängigkeiten stehen mit ihren Lizenzen in `uv.lock` bzw. in den installierten Paketen.
