# Sicherheitslücken in luibui melden

Dieses Dokument betrifft Lücken **in luibui selbst**, also in der Prüfstelle, der API, der
Weboberfläche, der Engine oder der CLI. Befunde in fremden Paketen, die luibui geprüft hat,
gehören nicht hierher.

## Bitte nicht öffentlich melden

Keine öffentlichen Issues, Pull Requests oder Posts zu Sicherheitslücken. Melde sie vertraulich:

- über die Funktion **„Report a vulnerability“** (GitHub Private Vulnerability Reporting) in diesem Repository, oder
- per E-Mail an **security@luibui.com** <!-- TODO(Len): Postfach einrichten, sonst Adresse ersetzen -->

Hilfreich sind: betroffene Komponente und Version, Schritte zum Nachvollziehen, erwartetes und
tatsächliches Verhalten sowie deine Einschätzung der Auswirkung.

## Was dann passiert

| Schritt | Frist |
|---|---|
| Eingangsbestätigung | innerhalb von 3 Werktagen |
| Erste Einschätzung | innerhalb von 10 Werktagen |
| Behebung kritischer Lücken | angestrebt innerhalb von 30 Tagen |
| Veröffentlichung | abgestimmt mit dir, spätestens 90 Tage nach Meldung |

luibui ist ein nicht-kommerzielles Projekt und zahlt keine Prämien. Wer möchte, wird in den
Versionshinweisen genannt.

## Besonders interessant

- Ausführung von Code aus Uploads (die Prüfstelle darf Paketinhalte nie ausführen)
- Ausbruch aus dem Entpacken oder Git-Clone (Pfade, Symlinks, Größenlimits)
- XSS oder HTML-Injection über Belege im Bericht, im PDF oder in der CSV
- Zugriff auf Projekte, Dateien oder Berichte anderer Nutzer
- Prompt-Injection, die den LLM-Prüfer zu einem besseren Urteil bringt

## Bitte nicht

Keine Tests gegen Konten oder Daten anderer, keine Last- oder DoS-Tests gegen luibui.com und
keine Uploads echter Schadsoftware. Nutze für Tests ein eigenes Konto oder eine lokale Installation.
