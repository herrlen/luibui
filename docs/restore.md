# Backup und Wiederherstellung (S3-10)

## Was wann gesichert wird

| Was | Wie | Wann | Aufbewahrung |
|---|---|---|---|
| Datenbank (Konten, Projekte, Berichte, Guthaben) | `pg_dump` im Container `ops`, verschlüsselt mit age an Lens öffentlichen Schlüssel, Volume `luibui-backup` | täglich 01:05 (Berlin) | 14 Dateien im Volume |
| Alle Volumes (auch `luibui-backup`, `luibui-projects`) | Projekt-Backup von mittwald | täglich 01:39 | 30 Tage bei mittwald |
| `MASTER_KEY`, `POSTGRES_PASSWORD`, `REGISTER_SIGNING_KEY` | nur in der Stack-Konfiguration bei mittwald | – | **zusätzlich bei Len sichern** |

Vor jeder Verschlüsselung prüft `ops`, ob sich das Backup wiederherstellen lässt: Der Dump wird in
die Datenbank `luibui_restore_test` auf demselben Server eingespielt, die Zeilenzahl jeder Tabelle
muss mit dem gesicherten Stand übereinstimmen (gleicher Snapshot), danach wird die Testdatenbank
gelöscht. Weicht etwas ab, gibt es kein Backup und eine Alarm-Mail. Der Server kennt nur den
öffentlichen Schlüssel: Wer an den Server oder an das mittwald-Backup kommt, kann die Backups nicht
lesen. Der unverschlüsselte Dump liegt nur kurz in `/tmp` des Containers und wird immer gelöscht.

Projekt-Dateien (`luibui-projects`) sind schon mit AES-256-GCM verschlüsselt (CLAUDE.md Regel 10).
Ihre Datenschlüssel liegen, mit `MASTER_KEY` verschlüsselt, in der Datenbank. **Ohne `MASTER_KEY`
sind Projekt-Dateien auch mit einem Backup verloren.**

Veröffentlichte Register-Versionen (S4-2) sind mit `REGISTER_SIGNING_KEY` (Ed25519) signiert; ihre
Archive liegen verschlüsselt wie Projekt-Dateien. **Ohne `REGISTER_SIGNING_KEY` lässt sich keine
neue Version mehr mit dem Schlüssel signieren, dem installierte Pakete vertrauen.**

## Einrichten (einmalig, Len)

```bash
brew install age                       # macOS; Debian/Ubuntu: apt install age
age-keygen -o luibui-backup.key        # gibt "Public key: age1…" aus
```

1. `luibui-backup.key` (privater Schlüssel) in den Passwortmanager und auf einen Datenträger
   offline. Nie auf den Server, nie ins Repo, nie in einen Chat.
2. Den öffentlichen Schlüssel und die Alarm-Adresse in `~/.config/luibui/ops.env`:
   ```
   BACKUP_AGE_RECIPIENT=age1…
   ALARM_AN=…
   ```
3. `scripts/release.sh` übernimmt beides in den Stack (danach aus dem laufenden Stack).

Ohne `BACKUP_AGE_RECIPIENT` läuft `ops` trotzdem (Health-Alarm), schreibt aber kein Backup und
meldet nach 26 Stunden „Kein aktuelles Backup“.

## Alarme (Mail von noreply@luibui.com an `ALARM_AN`)

- **Nicht erreichbar / Wieder erreichbar:** `http://api:8000/health`, `http://web:3000/healthz` und
  `https://luibui.com/healthz` alle 5 Minuten; Alarm nach zwei Fehlschlägen hintereinander (ein
  Ausrollen löst keinen aus), Entwarnung, sobald es wieder geht.
- **Backup fehlgeschlagen:** mit dem fehlgeschlagenen Schritt (`pg_dump`, Restore-Test, `age`).
- **Kein aktuelles Backup:** das letzte erfolgreiche ist älter als 26 Stunden; höchstens einmal am Tag.

Grenze: `ops` läuft auf demselben Server. Fällt der ganze Server aus, kommt keine Mail.

## Wiederherstellen

1. **Backup holen.** Aus dem Volume (neuestes Backup):
   ```bash
   mw container list -p p-yw5cv5          # ID des ops-Containers
   mw container exec <ops-id> "ls -l /backup"
   mw container cp <ops-id>:/backup/luibui-<zeit>.dump.age .
   ```
   Ist das Volume weg: das mittwald-Projekt-Backup des passenden Tages im mStudio wiederherstellen
   oder herunterladen (`mw project backup download`) und die Datei aus `luibui-backup` nehmen.
2. **Prüfen und entschlüsseln** (auf dem Mac, mit dem privaten Schlüssel):
   ```bash
   age --decrypt -i luibui-backup.key luibui-<zeit>.dump.age > luibui.dump
   pg_restore --list luibui.dump | head        # Inhaltsverzeichnis, nichts wird verändert
   ```
3. **Einspielen.** In eine leere Datenbank (nie über die laufende): api, worker und ops stoppen, im
   postgres-Container eine neue Datenbank anlegen, Dump einspielen, Namen tauschen.
   ```bash
   mw container stop <api-id> && mw container stop <worker-id> && mw container stop <ops-id>
   mw container cp luibui.dump <postgres-id>:/tmp/luibui.dump
   mw container exec <postgres-id> "createdb -U luibui luibui_neu"
   mw container exec <postgres-id> "pg_restore -U luibui --no-owner --exit-on-error -d luibui_neu /tmp/luibui.dump"
   mw container exec <postgres-id> "psql -U luibui -d postgres -c 'ALTER DATABASE luibui RENAME TO luibui_alt'"
   mw container exec <postgres-id> "psql -U luibui -d postgres -c 'ALTER DATABASE luibui_neu RENAME TO luibui'"
   mw container exec <postgres-id> "rm /tmp/luibui.dump"
   mw container start <api-id> && mw container start <worker-id> && mw container start <ops-id>
   ```
   Die API führt beim Start fehlende Migrationen aus. `luibui_alt` erst löschen, wenn alles läuft.
4. `luibui.dump` und die heruntergeladene Datei lokal löschen (`rm -P` auf dem Mac).

## Restore-Tests

| Datum | Was | Ergebnis |
|---|---|---|
| 2026-10-01 | Ops-Image (`pg_dump` 17.11, age 1.2.1) gegen PostgreSQL 17 mit Testdaten (2 Tabellen, 1.700 Zeilen): Backup mit eingebautem Restore-Test, dann mit dem privaten Testschlüssel entschlüsselt und in eine frische PostgreSQL 17 eingespielt | 500/1.200 Zeilen wieder da; falscher Schlüssel scheitert; kein Klartext in der Datei; Testdatenbank danach entfernt |
| jede Nacht ab dem Ausrollen | eingebauter Restore-Test in `ops` (Zeilenzahl je Tabelle) | Log des ops-Containers, Status in `/backup/status.json` |
| offen (Len, nach dem ersten Ausrollen) | ein echtes Produktions-Backup holen, mit dem privaten Schlüssel entschlüsseln, lokal einspielen | – |

Empfehlung: den manuellen Test (Schritte 1, 2 und 3 lokal) einmal im Quartal wiederholen und hier
eintragen.
