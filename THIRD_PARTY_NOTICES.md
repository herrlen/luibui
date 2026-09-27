# Drittanbieter-Komponenten

luibui nutzt die folgenden Werke Dritter. Die Lizenztexte liegen jeweils daneben oder sind
verlinkt. Namen und Marken der Projekte gehören ihren Inhabern; luibui nennt sie nur sachlich.

| Komponente | Version | Lizenz | Wo | Einsatz |
|---|---|---|---|---|
| Agent Threat Rules (Regeldateien) | v4.0.0, Commit `464548b` | MIT, Marken ausgenommen | `rules/external/atr/` (Lizenz: `rules/external/atr/LICENSE`) | Muster für B08–B17, nur Regex-Regeln, siehe `rules/external/atr/QUELLE.md` |
| gitleaks (Programm) | 8.30.1 | MIT | im Worker-Image unter `/usr/local/bin/gitleaks`, Quelle https://github.com/gitleaks/gitleaks | Secrets (B20), als eigener Prozess |

Python-Abhängigkeiten stehen mit ihren Lizenzen in `uv.lock` bzw. in den installierten Paketen.
