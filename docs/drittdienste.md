# Drittdienste

Jeder Dienst, den luibui im Betrieb oder in der Entwicklung nutzt (ENTWICKLERREGELN A11).
**Kein Eintrag → keine Einbindung.** Stand: 2026-09-27.

| Dienst | Anbieter, Sitz | Zweck | Welche Daten | Serverstandort | AV-Vertrag | Seit |
|---|---|---|---|---|---|---|
| Hosting (Container, Datenbank, Volumes, Domains, TLS) | Mittwald CM Service GmbH & Co. KG, Deutschland | Betrieb von luibui.com, app.luibui.com, api.luibui.com | alle Nutzer- und Projektdaten (Projekt-Dateien verschlüsselt) | Deutschland | S0-13 (Len) — Stand nicht dokumentiert | 2026-09-26 |
| Quellcode, CI, Container-Registry | GitHub Inc. (Microsoft), USA | Repository (wird privat, 27.09.2026), GitHub Actions, GHCR-Images | nur Quellcode und Images, **keine Nutzerdaten** | USA/weltweit | nicht nötig (keine personenbezogenen Daten) | 2026-09-26 |
| OSV-Datenbank (Download) | Google LLC (osv.dev, Google Cloud Storage), USA | tägliche Kopie der öffentlichen Schwachstellen-Datenbank für D01/D02 | **nichts wird gesendet**; der Worker lädt nur öffentliche Dateien herunter. Geprüfte Pakete bleiben lokal | USA | nicht nötig | 2026-09-27, freigegeben von Len |
| MalwareBazaar-Hashliste (Download) | abuse.ch (Spamhaus Technology), Schweiz; ausgeliefert über Google Cloud | tägliche Kopie der SHA-256-Liste bekannter Schadsoftware für A08 (Scanner-Matrix MAL-01) | **nichts wird gesendet**; der Worker lädt nur die öffentliche Liste herunter. Kein Abgleich einzelner Hashes online | Schweiz/USA (Auslieferung) | nicht nötig | 2026-09-27, freigegeben von Len; kostenlos nach den Fair-Use-Bedingungen für nicht-kommerzielle Nutzung |
| GitHub, Codeberg, GitLab (Klonen) | GitHub Inc. (USA), Codeberg e.V. (DE), GitLab Inc. (USA) | Klonen öffentlicher Repositories, die ein Nutzer zur Prüfung angibt | die Repository-URL (öffentlich); die IP des Servers | je Anbieter | nicht nötig | 2026-09-26 |

**Geplant, noch nicht eingebunden:**
- mittwald AI Hosting (LLM-Prüfer B18/B19, Sprint 3) — Deutschland, eintragen bei Einbindung.
- ClamAV-Signaturen (Sprint 4) — Download über Cloudflare, **Entscheidung offen**.
- E-Mail-Versand (Bestätigung, Passwort vergessen) — Anbieter offen.

**Bewusst nicht:** VirusTotal, Google Fonts, Analytics, externe CDNs, Session-Recorder (CLAUDE.md,
ENTWICKLERREGELN A4).
