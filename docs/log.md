# Log

Arbeitsprotokoll des Repos: was, warum, offene Punkte. Neueste Einträge unten.

## 2026-09-26 — Sprint 0 gestartet

- Repo verknüpft mit `github.com/herrlen/luibui` (vorerst privat, bis S0-6 freigegeben ist).
- Lokale Werkzeuge: `uv` (Python 3.12) und Colima als Docker-Laufzeit, statt Docker Desktop.
- Offen: `docs/luibui_Pruefkatalog.md` fehlt noch (S0-2, Len).

## 2026-09-26 — Sprint 0, erster Tag

**Erledigt (je ein Commit):** S0-1 Monorepo, S0-3 Schemas, S0-4 Scanner-Werkzeuge (Recherche),
S0-5 Bedrohungsmodell, S0-7 Compose-Stack, S0-8 API-Skelett, S0-9 Worker, S0-10 Engine-Skelett,
S0-11 CI. Auf `main` gepusht, CI grün (87 Python-Tests ohne Überspringen, Web-Build, drei Images
privat in GHCR).

**Entscheidungen, die im Code stecken:**
- Der Worker führt jeden Job in einem Kindprozess mit leerer Umgebung und eigener Prozessgruppe aus.
  Der Prozess, der Paketinhalte anfasst, hat keine Datenbank-Zugangsdaten; ein Timeout tötet auch
  Enkelprozesse (Scanner). Scratch wird im `finally` gelöscht, auch bei `os._exit`.
- Der Worker hängt lokal nur am internen Compose-Netz und hat keinen Internetzugang (geprüft).
  Git-Clones müssen deshalb in der API laufen (Bedrohungsmodell, offene Frage 1).
- Ein abgestürzter Analyzer wird in der Pipeline als `failed` gemeldet, nie still übersprungen,
  damit die Bewertung (S1-10) bei unvollständigen Prüfungen kein Grün vergeben kann.
- `scoring.py` wirft bis S1-10 `NotImplementedError`, statt irgendein Urteil zu liefern.
- Maschinencodes statt Wörtern im Schema: `nachweisgrad` z. B. `statisch_erkannt`,
  Ampel `gruen/gelb/rot/gesperrt`, DSGVO zusätzlich `nicht_bewertet`.

**Lokal gemessen (Colima, leerer Stack, keine Prüfung aktiv):** worker 50 MiB, api 62 MiB,
web 35 MiB, postgres 34 MiB. Images: api 303 MB, worker 258 MB (noch ohne Scanner), web 322 MB.
Die Zahlen vom Server kommen mit S0-12 in `docs/infra-kapazitaet.md`.

**Definition of Done Sprint 0:**
- [x] `docker compose up` startet alle vier Container lokal
- [ ] `https://api.luibui.com/health` = 200 — **blockiert**, siehe unten
- [x] Schemas validieren Beispiel-Befunde (Tests)
- [ ] `scanner-tools.md` und `threat-model.md` freigegeben — wartet auf Len (S0-6)
- [x] Worker räumt Scratch auch nach absichtlichem Absturz auf (Test)

**Blockiert — S0-12 Deploy:** Der Registry-Eintrag `ghcr.io` in `p-yw5cv5` hat keine
Zugangsdaten, mittwald kann die privaten Images nicht ziehen. Braucht einen GitHub-Token mit
`read:packages` (Len). `app.` und `api.luibui.com` gibt es als Virtual Host noch nicht.

**Offen für Len:**
1. Registry-Zugang für `ghcr.io` in `p-yw5cv5` setzen (S0-12).
2. S0-6: `docs/threat-model.md` und `docs/scanner-tools.md` lesen und freigeben.
3. S0-2: `luibui_Pruefkatalog.md` nach `docs/`.
4. Aus `scanner-tools.md`: ClamAV-Signaturen und OSV-Datenbank kommen von US-CDNs (Cloudflare,
   Google Cloud Storage). Reine Downloads, aber Verbindungen zu US-Anbietern — vereinbar mit
   „keine US-Dienste“?
5. Aus `threat-model.md`: Postfach `security@luibui.com` für `SECURITY.md` einrichten?
