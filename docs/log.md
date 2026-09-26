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

## 2026-09-26, 21:00 — S0-12 Deploy auf mittwald

Stack `default` in `p-yw5cv5` mit vier Containern auf `ec78e49`. `https://api.luibui.com/health`
→ 200 mit Datenbank ok, `luibui.com` und `app.luibui.com` → 200, `luibui.de` und `www.*` →
301 auf `https://luibui.com/`. Details, Container-IDs und Ausrollbefehl in
`docs/infra-kapazitaet.md`.

**Wichtig für Sprint 1:** mittwald übernimmt keine Netzwerke, kein `read_only` und kein
`cap_drop`. Auf dem Server hat der Worker also Internetzugang, und alle Container im Projekt
erreichen sich. Bevor der Worker Uploads verarbeitet, braucht es dafür eine Lösung
(Bedrohungsmodell T13 und offene Frage 2). Ungeprüft ist außerdem, ob der Worker auf
`luibui-scratch` schreiben darf.

**Nicht gemessen:** RAM auf dem Server (keine Messwerte über API/CLI, kein SSH-Schlüssel).

**Definition of Done Sprint 0 (aktualisiert):**
- [x] `docker compose up` startet alle vier Container lokal
- [x] `https://api.luibui.com/health` = 200
- [x] Schemas validieren Beispiel-Befunde (Tests)
- [ ] `scanner-tools.md` und `threat-model.md` freigegeben — wartet auf Len (S0-6)
- [x] Worker räumt Scratch auch nach absichtlichem Absturz auf (Test)

## 2026-09-26 — S1-2 Sichere Annahme (vorgezogen)

`packages/engine/luibui_scan/intake/`: `extract_zip` (ZIP), `accept_file` (Einzeldatei),
`accept_selection` (Dateiauswahl und Ordner, relative Pfade wie ZIP-Einträge) und `accept_text`
(Text als `eingabe.md`). Jede Ablehnung ist ein `IntakeRejectedError` mit Maschinencode
(`Ablehnung`) und bricht die ganze Annahme ab. 65 neue Tests; die präparierten Archive entstehen
im Test und liegen nicht im Korpus.

**Entscheidungen, die im Code stecken:**
- Bei ZIPs werden alle Einträge geprüft, bevor das erste Byte geschrieben wird. Maßgeblich ist
  nur das Central Directory. Geprüft wird der Originalname (`orig_filename`), weil `zipfile` Namen
  am NUL-Byte stillschweigend abschneidet.
- Abgelehnt werden: `..`, absolute Pfade, Laufwerksbuchstaben, Backslash, NUL, Steuerzeichen,
  leere und `.`-Segmente, Segmente > 255 Byte, Pfade > 1024 Byte, mehr als 20 Segmente,
  Symlinks, Hardlinks, Geräte, FIFOs, Windows-Reparse-Points, verschlüsselte Einträge,
  überlappende Einträge sowie Namen, die nach NFC und Groß/Klein gleich sind (auch Datei gegen
  gleichnamigen Ordner). Bidi- und Formatzeichen im Namen sind **erlaubt**: Sie meldet der
  Inhalts-Analyzer (S1-6) als Befund, statt die Prüfung abzubrechen (Bedrohungsmodell T5).
- Größen werden beim Schreiben gezählt. Pro ZIP-Eintrag darf nie mehr geschrieben werden, als der
  Header angibt, und `zipfile` prüft die CRC.
- **Kompressionsrate > 100** wird pro Eintrag und für das ganze Archiv geprüft, aber erst ab
  1 MiB entpackter Größe. Ohne diese Schwelle scheitert schon eine kleine `SKILL.md` mit vielen
  Leerzeichen. Unterhalb von 1 MiB kann die Rate die Platte nicht füllen.
- MB bedeutet MiB (1024 × 1024).
- Dateien entstehen mit `O_CREAT | O_EXCL | O_NOFOLLOW`, Modus 0600, Ordner mit 0700. Liegt im
  Scratch schon ein Symlink, wird abgebrochen und nicht durchgegangen.
- Verschachtelte Archive bleiben gepackt.

**Offen:**
- Welche Prüfkatalog-ID (A1–A3?) ein Ablehnungsgrund im Bericht bekommt, bleibt offen, bis
  `luibui_Pruefkatalog.md` da ist. Bis dahin liefert die Annahme nur den Code `Ablehnung`, noch
  keinen `Finding`.
- Die API-Routen (S1-1) und der Git-Clone (S1-3) rufen dieses Modul noch nicht auf. Wo geklont
  wird, hängt an der offenen Frage 1 im Bedrohungsmodell.
