---
name: changelog
description: Schreibt einen Changelog-Eintrag aus den Commits seit dem letzten Tag.
---

# Changelog

1. Lies die Commits seit dem letzten Tag mit `git log --oneline $(git describe --tags --abbrev=0)..HEAD`.
2. Gruppiere sie nach „Neu“, „Geändert“ und „Behoben“.
3. Zeige dem Nutzer den Entwurf und frage, ob er in `CHANGELOG.md` übernommen werden soll.

Schreibe nichts ohne Bestätigung.
