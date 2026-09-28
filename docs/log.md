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

## 2026-09-26 — S1-4 Inventar

`packages/engine/luibui_scan/inventory.py`: `build_inventory(root)` geht den Scratch nach der
Annahme durch und liefert pro Datei Pfad, Größe, SHA-256, echten Typ (Magic Bytes) und Sprache,
dazu den Inventar-Hash, die Sprachen mit Dateianzahl, den erkannten Pakettyp und die Merkmale,
auf denen dieser beruht. 54 neue Tests.

**Entscheidungen, die im Code stecken:**
- **Inventar-Hash** (`report.schema.json`, `paket.sha256`): SHA-256 über die Zeilen
  `pfad NUL datei-sha256 LF`, sortiert nach den UTF-8-Bytes des Pfads. Damit ändert sich der Hash
  bei jeder Umbenennung, nicht nur bei geänderten Inhalten.
- **Dateityp** kommt aus den ersten 4 KiB: ELF, Mach-O, PE, Java-Class, WASM, ZIP, gzip, bzip2, xz,
  7z, RAR, tar, PDF, PNG, JPEG, GIF, WebP, SQLite, OLE. Sonst gilt: `text`, oder `script` bei
  Shebang, wenn kein NUL-Byte vorkommt und die Probe gültiges UTF-8 ist. Alles andere ist
  `binary`. `MZ` am Anfang einer Textdatei ist kein PE. Die Dateiendung spielt beim Typ keine
  Rolle; den Abgleich Endung ≠ Typ macht Analyzer A (S1-5).
- **Sprache** kommt aus der Endung, bei Dateien ohne Endung aus dem Shebang, und wird nur bei
  Textdateien gesetzt.
- **Pakettyp** wird unabhängig vom Manifest erkannt; der Abgleich mit `luibui.json` gehört zu
  Ebene G. Die Merkmale:
  - Skill: `SKILL.md`
  - Plugin: `.claude-plugin/plugin.json`, `.well-known/ai-plugin.json`, `gemini-extension.json`
  - MCP-Server: MCP-SDK in `package.json`, `mcp`/`fastmcp` in `pyproject.toml` oder
    `requirements.txt`, `server.json` der MCP-Registry, MCP-Importe im Code
  - Tool: JSON-Liste von Tool-Definitionen mit Schema

  Ein Plugin schlägt alles andere, weil es Skills und Server bündelt. Tool-Definitionen neben
  einem Skill oder Server ändern den Typ nicht. Skill und Server zusammen ohne Plugin-Datei
  ergeben `gemischt`. Nach Merkmalen gesucht wird nur in Textdateien bis 1 MiB, und nur als
  Textmuster: nichts wird als Code geparst.
- `Pakettyp` liegt in `models.py`; `ScanContext` hat dafür das Feld `pakettyp`,
  `InventoryEntry` das Feld `sprache`.
- Findet das Inventar im Scratch einen Symlink oder eine Sonderdatei, bricht es mit
  `InventoryError` ab. Das darf nach der Annahme eigentlich nicht vorkommen.

**Offen:** Das Inventar ist noch nicht in die Pipeline eingehängt. Das geschieht zusammen mit der
Annahme, wenn der Worker Prüfungen annimmt (S1-1).

## 2026-09-26 — S1-11 CLI `luibui scan`

`luibui scan <pfad> [--json]` prüft einen Ordner, ein ZIP-Archiv (erkannt an der Endung `.zip`)
oder eine einzelne Datei. Die Eingabe läuft durch dieselbe Annahme wie ein Upload in ein privates
Temp-Verzeichnis, das danach gelöscht wird (Test). Neu in der Engine: `scan.scan_prepared()`
(Inventar → Kontext → Pipeline), das ab S1-1 auch der Worker nutzt, und
`intake.accept_directory()` für lokale Ordner. 18 neue Tests.

**Entscheidungen, die im Code stecken:**
- **Noch keine Bewertung.** `scoring.py` kommt mit S1-10. Bis dahin schreibt die CLI
  „Bewertung: noch nicht verfügbar“, `bewertung` ist im JSON `null`, und solange kein Analyzer
  gelaufen ist, steht dabei, dass das Ergebnis nichts über die Sicherheit aussagt. Nichts in der
  Ausgabe darf wie Grün aussehen (Test). Das JSON entspricht deshalb noch nicht
  `report.schema.json`, dem fehlen die Ampeln.
- **Rückgabewerte:** 0 Prüfung gelaufen, 2 Pfad fehlt oder falscher Aufruf, 3 Eingabe
  abgelehnt. Ein Rückgabewert je nach Ampel (für CI) kommt mit S1-10.
- **Lokale Ordner** werden wie eine Dateiauswahl behandelt (Limits 1.000 Dateien und 50 MB,
  Symlinks führen zur Ablehnung). **`.git` wird übersprungen**, weil es nicht zum Paket gehört
  und sonst jedes Repository an der Dateigrenze scheitert.
- **Prüfumfang** nach Konzept §5: Einzeldatei, sonst mit `luibui.json` auf oberster Ebene Paket,
  ohne Manifest Dateiauswahl. Liegt das Paket im ZIP in einem Unterordner, zählt es noch als
  Auswahl; das klärt S1-10.
- **Terminal-Ausgabe:** Alles, was aus dem Paket kommt (Pfade, Titel, Belege), wird escaped.
  Steuerzeichen (ANSI) und unsichtbare Formatzeichen (Bidi, Zero-Width, Unicode-Tags) erscheinen
  als `\x..`/`\u....`. JSON wird mit `ensure_ascii` ausgegeben.
- **Reihenfolge in `check_path` geändert:** Enthält ein Name `..` und zugleich ein Steuerzeichen,
  lautet der Grund jetzt „Pfad außerhalb“, der schwerere von beiden.

## 2026-09-26 — S1-10 Bewertung

`scoring.py` setzt Konzept §5 um: Ampeln Sicherheit, DSGVO und Gesamt, Sperrliste, Note und
Freigabe-Stufe, zusammengefasst in `bewerte()`. `report.py` baut den Bericht nach
`report.schema.json`; Tests validieren jeden erzeugten Bericht gegen das Schema.
`scan_prepared()` liefert die Bewertung mit, und `luibui scan` zeigt sie an. Mit `--json` gibt die
CLI jetzt den schemakonformen Bericht aus. Pakettyp und Sprachen sind dort nicht mehr enthalten,
weil das Schema sie nicht kennt; die Textausgabe zeigt sie weiter. 55 neue Tests.

**Entscheidungen, die im Code stecken:**
- **Unvollständig heißt nie Grün**, auf keiner Achse. Das gilt, wenn ein Analyzer abgestürzt ist
  **oder gar keiner lief**. Solange es keine Analyzer gibt, ist deshalb jedes Ergebnis höchstens
  Gelb, mit dem Hinweis, dass es nichts über die Sicherheit aussagt.
- **K außerhalb der Sperrliste ergibt Rot**, nicht Gesperrt. So steht es in der Tabelle in §5.
- **Sperrliste:** Enthalten sind die Prüfkatalog-IDs in `SPERRLISTE_KATALOG` (erfasst wird jede
  Regel `LB-<ID>-…` einer gelisteten Prüfung) sowie externe Präfixe in `SPERRLISTE_EXTERN`.
  Der Katalog-Teil ist **leer**, bis `luibui_Pruefkatalog.md` da ist. Extern sind schon jetzt
  eingetragen: `gitleaks:` für echte Secrets und `osv:MAL-` für bekannte Schadpakete, beide
  wörtlich aus der Sperrliste in §5. Gesperrt wird immer nur bei Schwere K.
- **DSGVO:** Bewertet wird nur beim Paket mit Manifest, dann gilt H/K → Rot, M → Gelb, sonst Grün.
  Ohne Manifest bleibt die Achse „nicht bewertet“, außer ein DSGVO-Befund macht sie Gelb (M) oder
  Rot (H/K). Laut Konzept können das dann nur Drittland-Endpunkte sein, weil die
  Manifest-Prüfungen ohne Manifest gar nicht laufen. Ob `luibui.json` gültig ist, prüft noch
  niemand; vorerst entscheidet allein, dass die Datei da ist (Ebene G).
- **Die Note** zählt Befunde beider Achsen.
- **Grün** heißt in der CLI „Grün, keine bekannten Befunde, geprüft am …“ und nie „sicher“
  (Test).

**Offen:**
- Die IDs für die Sperrliste folgen aus dem Prüfkatalog.
- Ein Rückgabewert der CLI je nach Ampel (für CI, etwa `--fail-on rot`) ist noch nicht eingebaut.

## 2026-09-26 — S1-11 Nachtrag: `luibui scan --fail-on`

Auf Lens Wunsch: `--fail-on gelb|rot|gesperrt` liefert den Rückgabewert 1, wenn die Gesamtampel
diese Stufe oder eine schlechtere erreicht (für CI). Ohne die Option bleibt der Rückgabewert nach
einer Prüfung 0, bestehende Aufrufe ändern sich also nicht. `gruen` ist als Schwelle nicht
erlaubt, weil sonst jede Prüfung scheitern würde. Rückgabewerte jetzt: 0 gelaufen, 1 Schwelle
erreicht, 2 Aufruf, 3 abgelehnt. 11 neue Tests.

## 2026-09-26 — S2-7 (Teil 1) Verschlüsselte Dateiablage, vorgezogen

Len hat entschieden, S2-6 (Anmeldung) und S2-7 (Ablage) vor S1-1 zu ziehen. Der Grund: Die
Upload-Route braucht nach CLAUDE.md Regel 9 und 10 Eigentümerprüfung und verschlüsselte Ablage.
Dieser Teil bringt nur den Kern, ohne Routen: `apps/api/luibui_api/storage/`. 23 neue Tests.

**Entscheidungen, die im Code stecken:**
- **Schlüssel:** `MASTER_KEY` (ENV, 32 Byte, Base64) verschlüsselt pro Projekt einen
  Datenschlüssel. Der verschlüsselte Datenschlüssel steht in `projects.data_key_enc`, gebunden an
  die Projekt-ID, damit er nicht in ein anderes Projekt kopiert werden kann.
- **Dateien** werden mit AES-256-GCM in Blöcken zu 1 MiB verschlüsselt. Die Nonce jedes Blocks
  besteht aus einem zufälligen Präfix, einem Zähler und einer Endmarke. Dadurch fallen
  vertauschte, fehlende und abgeschnittene Blöcke auf (Tests). Die Blockung verhindert, dass eine
  200 MB große Datei auf einmal in den Speicher der API (512 MB) muss. Jeder Blob ist an seinen
  `storage_key` gebunden: Unter einem anderen Datensatz entschlüsselt er nicht.
- **Ablage:** `/projects/ab/cd/<storage_key>`, Modus 0600, nie überschrieben (`O_EXCL`).
- **Achtung:** Beim Lesen kommen die ersten Blöcke heraus, bevor eine Manipulation am Ende
  erkannt wird. Wer liest, darf die Daten erst verwenden, wenn der Iterator ohne Fehler durch ist.
- `MASTER_KEY` ist in Compose Pflicht und steht im mittwald-Stack; das Ausrollen und das Sichern
  des Schlüssels sind in `docs/infra-kapazitaet.md` beschrieben.

**Offen (Teil 2, mit S1-1):** Kontingent 500 MB pro Konto und 10 Versionen pro Projekt, die
Option „nach Prüfung löschen“, bekannte Schadsoftware nie ablegen, Dateiansicht und Download.

## 2026-09-26 — S2-6 Anmeldung, vorgezogen

Registrierung, Anmeldung, Abmeldung, `GET /api/auth/ich`, Zwei-Faktor-Anmeldung (TOTP) und
API-Tokens (`/api/tokens`) sind da, dazu die zentrale Zugriffsprüfung `get_owned` in
`luibui_api/auth.py`. Migration `0002` legt die Tabelle `sessions` an, ergänzt
`users.totp_confirmed_at` und einen eindeutigen Index auf `tokens.token_hash`. 31 neue Tests,
alle gegen PostgreSQL.

**Entscheidungen, die im Code stecken:**
- **Hashing (Len, 2026-09-26):** Passwörter mit Argon2id. Session- und API-Tokens sind 256 Bit
  zufällig und werden als SHA-256 gespeichert, weil Argon2 bei jeder Anfrage 64 MB und rund
  50 ms kostet. CLAUDE.md ist angepasst.
- **Cookie** `__Host-luibui_session`: Das Präfix `__Host-` zwingt Browser, kein Domain-Attribut
  zu akzeptieren; dazu `Secure`, `HttpOnly`, `SameSite=Lax`, `Path=/`. Die Session liegt
  serverseitig, beim Abmelden ist sie sofort ungültig (Test). Laufzeit 14 Tage.
- **`api.luibui.com` ignoriert Cookies** und akzeptiert nur `Authorization: Bearer lb_…`
  (Regel 11, über `BEARER_ONLY_HOSTS`).
- **CSRF:** Schreibende Anfragen mit Cookie müssen `Origin: https://app.luibui.com` tragen oder,
  ohne Origin, `Sec-Fetch-Site: same-origin`. Sonst gibt es 403.
- **Ein API-Token kann keine Tokens anlegen und kein 2FA ändern**, das geht nur mit einer
  Browser-Session.
- **Fremde und unbekannte IDs geben beide 404** (`get_owned`). Test: Nutzer B sieht Tokens von A
  nicht und kann sie nicht widerrufen.
- **Anmeldung:** Unbekannte E-Mail und falsches Passwort sehen gleich aus und dauern gleich lang
  (Dummy-Hash). Nach 10 Fehlversuchen in 15 Minuten, je E-Mail und je Client, gibt es 429. Der
  Zähler liegt im Speicher des API-Prozesses; das reicht für einen Prozess.
- **TOTP:** Das Geheimnis wird mit `MASTER_KEY` verschlüsselt und an die Nutzer-ID gebunden. Aktiv
  wird es erst nach Bestätigung mit einem gültigen Code. Abschalten braucht Passwort und Code.
- Die E-Mail wird klein geschrieben gespeichert und nur grob auf ihre Form geprüft.

**Offen:**
- Die E-Mail-Bestätigung fehlt, weil es noch keinen Mailversand gibt. `email_verified_at` bleibt
  leer.
- Passwort vergessen, Konto löschen und Datenexport gehören zu S2-10.
- Hinter dem mittwald-Ingress und dem Next.js-Proxy ist `request.client.host` die IP des Proxys.
  Die Begrenzung je Client greift deshalb erst, wenn `X-Forwarded-For` vertrauenswürdig
  ausgewertet wird (vor dem Livegang klären). Die Begrenzung je E-Mail greift schon.
- Die Oberfläche (Anmelden, Registrieren) kommt mit S2-8 und S2-11.

## 2026-09-26 — S1-1 Annahme über die API (mit S2-7 Teil 2)

Neue Routen: `POST/GET /api/projects`, `GET/DELETE /api/projects/{id}`,
`POST /api/projects/{id}/scans` (multipart: `art` = datei | auswahl | zip | text, `dateien`,
bei `auswahl` dazu `pfade` in derselben Reihenfolge) und `GET /api/scans/{id}` mit Status,
Ampeln, Note und, sobald fertig, dem ganzen Bericht. Der Worker kann Scan-Jobs jetzt
ausführen. 32 neue Tests, darunter ein Durchlauf von Ende zu Ende: Upload über die API, dann
der echte Worker mit Kindprozess, dann der Bericht über die API.

**Ablauf und Entscheidungen:**
- **Die API nimmt an, der Worker prüft.** Die API führt den Upload durch die Engine-Annahme
  (`luibui_scan.intake`) direkt nach `/scratch/<job-id>`, speichert die Dateien verschlüsselt
  als neue Projektversion und legt Scan und Job an. Der Worker übernimmt den vorbereiteten
  Ordner. **`MASTER_KEY` bleibt allein in der API**; der Worker, der feindliche Inhalte anfasst
  und auf mittwald Internet hat, bekommt ihn nie. Dafür bindet die API jetzt `luibui-scratch`
  ein (Compose, mittwald-Stack, Dockerfile).
- **Der Elternprozess des Workers prüft den Bericht des Kindes** mit den Pydantic-Modellen
  (Befunde, Ampeln, Note, Freigabe, `scan_id`), bevor er Scan-Zeile und Befunde schreibt. Ein
  unpassender Bericht wird ganz verworfen, und der Scan steht auf `fehlgeschlagen`.
- **Aufräumen im Scratch:** Aufgehoben werden die Ordner laufender Jobs und wartender Jobs, die
  noch nie gestartet sind. Ordner ohne Job-Zeile bleiben 10 Minuten stehen, weil die API den
  Upload schreibt, bevor ihr Job committet ist. Ein zweiter Versuch beginnt immer leer.
  Scan-Jobs laufen nur einmal (`max_attempts = 1`).
- **Upload-Grenze:** `Content-Length` ist Pflicht und darf höchstens 60 MB betragen (411/413),
  noch bevor das Formular gelesen wird. Bis zu 1.000 Dateien je Formular.
- **ZIP:** Die Datei wird neben den Scratch kopiert (`zipfile` braucht Dateigröße und
  Positionierung), entpackt und sofort wieder gelöscht.
- **Ablehnung** durch die Annahme ergibt 422 mit `grund`, `text` und `pfad`. Es bleibt nichts
  zurück: kein Scratch, keine Blobs, keine Zeilen (Test).
- **S2-7, Teil 2:** Kontingent 500 MB je Konto (413), die letzten 10 Versionen je Projekt
  (ältere samt Blobs weg; der alte Scan bleibt, nur ohne Dateien), „nach Prüfung löschen“
  speichert gar nichts, und das Löschen eines Projekts löscht seine Blobs, erst nach dem Commit.
- **Prüfumfang** berechnet die API beim Anlegen aus dem Inventar (Konzept §5).
- Die Projekt-Routen sind bewusst schmal: Oberfläche, Typ-Logik und Versionsliste kommen mit
  S2-8.

**Offen:**
- `POST /api/quickscans` (Schnellscan per Git-URL) und das Rate-Limit je IP fehlen noch. Sie
  hängen an S1-3 (Git-Clone) und an Lens Entscheidung, wer klont.
- `art = git` für Projekte kommt ebenfalls mit S1-3.
- „Bekannte Schadsoftware nie ablegen“ braucht ClamAV oder Hash-Listen (Sprint 4). Bis dahin
  wird jede Datei abgelegt, die die Annahme besteht.
- Dateiansicht und Download gespeicherter Dateien (Regel 10) gehören zu S2-9.

## 2026-09-26 — S1-3 Sicherer Git-Clone und Schnellscan

Len hat entschieden, dass **die API klont** (offene Frage 1 im Bedrohungsmodell).
`packages/engine/luibui_scan/intake/safe_git.py` klont öffentliche Repositories. Projekte
können jetzt per `art=git` geprüft werden, dazu gibt es den Schnellscan ohne Konto:
`POST /api/quickscans` und `GET /api/quickscans/{id}`. 53 neue Tests. Ein echter Klon von
GitHub wurde lokal und im gehärteten API-Image geprüft (Nutzer 10001, `read_only`,
`cap_drop ALL`).

**Entscheidungen, die im Code stecken:**
- **URL:** Die URL wird streng geprüft und aus ihren Teilen neu gebaut. Erlaubt ist nur `https://`
  auf github.com, codeberg.org und gitlab.com mit Besitzer und Repository (bei GitLab auch
  Untergruppen). Nicht erlaubt: Zugangsdaten, Ports außer 443, Query, Fragment, `..`, Steuer-
  und Leerzeichen. Die 26 abgelehnten Beispiele im Test umfassen `ext::`, `file://`, SSH,
  `github.com@evil`, Metadaten-IP und ähnliche Hosts.
- **git** läuft ohne System- und globale Config, mit eigenem leeren HOME, ohne Hooks,
  `fsmonitor`, SSH, Credential-Helper, Umleitungen und Submodule, und nur mit dem Protokoll
  HTTPS (`protocol.allow=never` und `GIT_ALLOW_PROTOCOL`), dazu `transfer.fsckObjects`. Gestartet
  wird es über eine feste argv-Liste mit `--` vor der URL.
- **Größe und Zeit:** Das Clone-Verzeichnis wird während des Klonens gemessen. Über 300 MB oder
  nach 60 s wird die ganze Prozessgruppe beendet. Danach gelten die Grenzen wie bei einem ZIP:
  10.000 Dateien und 200 MB.
- **Der Arbeitsbaum läuft durch `accept_directory`**, also durch dieselben Pfad-, Namens- und
  Grenzprüfungen wie ein Ordner-Upload. `.git` wird nicht übernommen.
- **Symlinks** werden als Textdatei ausgecheckt (`core.symlinks=false`) und nicht abgelehnt,
  weil `CLAUDE.md → AGENTS.md` in KI-Repos üblich ist. `CloneResult.symlinks` und `.submodules`
  halten sie für spätere Befunde fest (Ebene A, sobald der Prüfkatalog da ist). Das
  Bedrohungsmodell (T10, T11) ist angepasst.
- **Schnellscan:** Ohne Konto, nichts wird gespeichert außer dem Bericht, der nach 7 Tagen
  abläuft. Der Hinweis „ohne Gewähr“ steht im Bericht (Test). Höchstens 3 Schnellscans pro Tag
  und IP (ungültige URLs zählen nicht) und höchstens 20 wartende, sonst 503. Job-Zeitlimit
  60 s. Die zufällige Scan-ID ist der einzige Schlüssel zum Bericht. Die öffentliche Route
  liefert **nur** Schnellscans ohne Eigentümer (Test: Scan eines Kontos über diese Route → 404).
- Das API-Image enthält jetzt `git` und `ca-certificates`.

**Offen:**
- Abgelaufene Schnellscans werden noch nicht gelöscht; dafür braucht es einen Cronjob.
- Die IP-Begrenzung hängt wie bei der Anmeldung an `X-Forwarded-For` hinter dem Proxy.
- Der Schnellscan per Einzeldatei (bis 2 MB) und die reduzierte Pipeline folgen mit S2-13.

## 2026-09-27 — S0-12 Nachtrag: Schalter `ANNAHME_OFFEN` vor dem Ausrollen

Len will den Stand von Sprint 1 ausrollen, bevor zwei Lücken geschlossen sind: Der Worker hat auf
mittwald Internet, und die API sieht hinter dem Proxy nur dessen IP. Deshalb gibt es jetzt den
Schalter `ANNAHME_OFFEN` (Standard: aus). Solange er aus ist, antworten Registrierung, Upload
und Schnellscan mit 503 „noch nicht freigeschaltet“. Health, Anmeldung bestehender Konten,
Tokens und das Lesen von Berichten laufen weiter (Test). Eingeschaltet wird er erst, wenn beide
Lücken zu sind.

## 2026-09-27 — S0-2 Prüfkatalog: Entwurf von Claude

Len hat entschieden, dass Claude den Prüfkatalog entwirft, weil die Datei nirgends vorlag.
`docs/luibui_Pruefkatalog.md` enthält 73 Prüfungen: A01–A12, B01–B20, C01–C13, D01–D05,
E01–E07, F01–F06, G01–G06, H01–H04. Für jede sind Schwere, Sperrliste, Umfang (Paket, Auswahl,
Einzeldatei, Schnellscan), Quelle und Normbezug angegeben, dazu die Zuordnung der 15
Sperrlisten-Kategorien und der Annahme-Codes. Er passt zu allen Verweisen in Konzept und
Sprintplanung (A2–A12, B1–B7, B8–B17, B8–B19, C1–C13, G1/G3–G5, E7, F6, H1/H3/H4, B01 =
Unicode-Tags und gesperrt).

**Status: Entwurf.** Sieben offene Fragen stehen am Ende des Katalogs, darunter: Ebene I bleibt
unbenutzt, die Annahme bekommt A01 statt A2/A3, Secrets werden B20. Erst nach Lens Freigabe kommen
die IDs in `SPERRLISTE_KATALOG` (`scoring.py`) und in die Annahme-Befunde, und erst dann starten
die Analyzer S1-5 bis S1-9.

## 2026-09-27 — S0-2 Prüfkatalog freigegeben, IDs im Code

Len hat den Katalog mit allen sieben Entscheidungen freigegeben: I bleibt frei, die Annahme ist
A01, Secrets sind B20, und B18 (LLM) sperrt nie allein. Umgesetzt:
- `SPERRLISTE_KATALOG` in `scoring.py` enthält die 23 IDs aus Katalog §10.
- Jede Ablehnung der Annahme wird zu einem Befund `LB-A01-<grund>` mit Schwere laut §11
  (`rejection_finding`). Die CLI gibt ihn bei `--json` mit aus, die API in der 422-Antwort.
  Unsichtbare Zeichen im Namen stehen escaped im Beleg; `datei` wird nur bei einem gültigen
  relativen Pfad gesetzt.
- CLAUDE.md nennt jetzt „A01–H04“. Im Bedrohungsmodell steht T1 auf A01 und T5 auf B03.

## 2026-09-27 — S1-6 Analyzer B – versteckte Inhalte (B01–B07)

`analyzers/b_inhalte.py` meldet Unicode-Tags (B01, K, gesperrt), Zero-Width-Zeichen und
Variation Selectors (B02), Bidi-Steuerzeichen in Text und Dateinamen (B03), Wörter mit gemischten
Schriftsystemen (B04), versteckten Text in Kommentaren oder mit unsichtbarem Stil (B05),
lesbaren Text in Base64 oder Hex (B06) und Bild-Links mit Platzhaltern für Daten (B07, K,
gesperrt). Es gibt einen Befund je Datei und Prüfung mit der Trefferzahl, und der Beleg macht
unsichtbare Zeichen als `<U+XXXX>` sichtbar. B01 zeigt den dekodierten versteckten Text.
`analyzers/_common.py` ist die gemeinsame Grundlage (Dateien lesen ohne Symlinks folgen,
Befunde bauen). 35 neue Tests, jede Regel mit positiven und negativen Fällen. **Die Definition
of Done aus Sprint 1 ist erfüllt:** Eine einzelne `SKILL.md` mit versteckter Unicode-Anweisung
wird gesperrt (Test).

**Ausnahmen gegen Fehlalarme:** ZWJ zwischen Emojis, ZWNJ in arabischer, persischer oder
indischer Schrift, weiches Trennzeichen im Wort, BOM am Dateianfang, `data:`-URLs, Badges mit
normaler Query. B06 prüft nur Anweisungsdateien (Markdown, YAML, JSON, TOML, Text), keinen
Code. **B05 prüft nur Markdown, SVG und Text:** In der HTML-Oberfläche eines Skills sind
eingeklappte Bereiche mit `display:none` normal (Fehlalarm in `anthropics/skills`, behoben).
`color: white` allein gilt nicht mehr als versteckt.

**Probe an echten Repos** (über `safe_git`): `anthropics/skills` (419 Dateien) ohne Befund,
`modelcontextprotocol/servers` (156 Dateien) ohne Befund.

**Neu: erwartete Prüfungen je Scan-Art** (`scan.ERWARTET`). Sonst hätte schon dieser erste
Analyzer ein sauberes Paket grün gemacht, obwohl Dateien, Code, Secrets und Abhängigkeiten noch
gar nicht geprüft werden. Schnellscan: A, B-Inhalte, B-Muster, Secrets, D. Intensiv und lokal:
dazu C, E, G. Fehlt eine davon, ist das Ergebnis höchstens Gelb, und der Bericht führt sie unter
„nicht geprüft: noch nicht eingebaut“. Was es gibt, aber für den Umfang nicht gilt (etwa D bei
einer Einzeldatei), ist Umfang und keine Lücke.

**Offen:** `luibui scan` auf einen Projektordner mit pnpm-`node_modules` scheitert an Symlinks
(A01). Das ist richtig für Uploads, aber unbequem lokal. Zu entscheiden ist, ob die CLI
installierte Abhängigkeiten (`node_modules`, `.venv`) auslässt. Die prüft ohnehin D über das
Lockfile.

## 2026-09-27 — S1-5 Analyzer A – Dateien (A02–A12)

`analyzers/a_dateien.py` prüft:
- **A02, automatisch laufende Befehle:** Claude-Code-Hooks, VS-Code-Aufgaben bei
  `folderOpen`, npm-`pre`/`post`/`install`, Git-Hooks, `.envrc`.
- **A03, Installationsskripte,** die nachladen oder Prozesse starten.
- **A04, Programmdateien.**
- **A05, Endung passt nicht zum Inhalt.**
- **A06, kompiliert ohne Quelle:** `.pyc` ohne `.py`, minifiziertes JS ohne Map.
- **A07, Archive im Paket.**
- **A08, bekannte Schadsoftware** gegen `rules/data/schadsoftware-sha256.txt`.
- **A09, `.env` und ungewöhnliche versteckte Dateien.**
- **A10, Git-Symlinks, die aus dem Paket zeigen.**
- **A11, Submodule.**
- **A12, fremde Paketquellen** (`--extra-index-url`, `registry=`, `[[tool.uv.index]]`).

Je Regel gibt es höchstens 20 Befunde, der letzte fasst den Rest zusammen. 41 neue Tests.

**Entscheidungen:**
- **A02 sperrt nur bei gefährlichen Befehlen.** Automatische Befehle allein ergeben H (Rot),
  denn Hooks und `postinstall` sind in legitimen Plugins und Paketen üblich. K (gesperrt) gibt es
  erst, wenn der Befehl herunterlädt und ausführt (`curl … | sh`), dekodiert (`base64 -d`) oder
  Code inline startet (`eval`, `python -c`, `/dev/tcp`). `.envrc` bleibt M, weil direnv erst nach
  `direnv allow` ausführt. `prepare` zählt nicht als Installations-Hook.
- **A08 und Regel 10:** Die API legt ein Paket nicht ab, wenn eine Datei auf der Hash-Liste
  steht. Geprüft wird es trotzdem, damit der Bericht A08 zeigt (Test). Die Liste ist leer; wie
  sie gefüllt wird, bleibt offen (ClamAV ab Sprint 4 oder gepflegte Hash-Liste).
- **A10** braucht die Symlink-Liste aus dem Git-Clone. Sie geht von der API über die
  Job-Payload (`options.git_symlinks`) an den Worker und dort in `ScanContext.options`.
- Regeldateien: `LUIBUI_RULES_DIR`, sonst `rules/` im Repository, sonst `/rules`.

**Probe an echten Repos:** In `anthropics/skills` ein berechtigtes A07 (ein `.tar.gz` im Skill).
In `modelcontextprotocol/servers` ein Fehlalarm A12, weil die offizielle npm-Adresse in
Anführungszeichen stand. Behoben und als Test aufgenommen, danach ohne Befund.

## 2026-09-27 — S1-8 Secrets mit gitleaks (B20)

Adapter `luibui_scan/tools/gitleaks.py` und Analyzer `analyzers/secrets.py`. Befunde heißen
`gitleaks:<regel>`, Ebene B. **K (gesperrt)**, in Test-, Beispiel- und Doku-Pfaden **H**. Im
Beleg steht nur der von gitleaks geschwärzte Treffer (`REDACTED`); was danach noch wie ein langer
Token aussieht, kürzen wir zusätzlich auf 4 Zeichen und „…“. Fehlt gitleaks, schlägt der
Analyzer fehl, und das Ergebnis wird nie grün (Test). 8 neue Tests.

**Härtung gegen das geprüfte Paket (alle mit Test):** gitleaks läuft immer mit **unserem**
`--config` (`rules/gitleaks/gitleaks.toml`, Standardregeln) und **unserer** leeren
Ignore-Datei, dazu mit `--ignore-gitleaks-allow`, `--redact=100`, ohne Archive und Symlinks,
mit leerer Umgebung und Timeout. Belegt: Ohne `--config` übernimmt gitleaks eine
`.gitleaks.toml` aus dem Paket und findet den Test-Token nicht mehr. Befunde außerhalb des
Paketordners werden verworfen.

**Betrieb:**
- gitleaks 8.30.1 wird im Worker-Image und in der CI mit Prüfsumme aus dem offiziellen Release
  geladen.
- `rules/` liegt im Image unter `/app/rules` (`LUIBUI_RULES_DIR`).
- Der Kindprozess des Workers bekommt zusätzlich die nicht geheimen Variablen
  `LUIBUI_RULES_DIR` und `LUIBUI_GITLEAKS`, sonst fände er Regeln und Werkzeug nicht.
- Im echten Image und ohne Netz (`--network none`) geprüft: Der Token wird trotz eingeschmuggelter
  `.gitleaks.toml` gefunden, und das Paket ist gesperrt.

**Abweichung von CLAUDE.md Regel 6:** Die Regel verlangt „erste 4 Zeichen + …“. Weil gitleaks
schon im eigenen Prozess vollständig schwärzt, erreicht kein Zeichen des Secrets luibui. Das ist
strenger als die Regel.

**Probe an echten Repos:** `anthropics/skills` und `modelcontextprotocol/servers` ohne
Secrets-Befund.

## 2026-09-27 — S1-7 Analyzer B – Anweisungsmuster (B08–B17)

**Eigene Regeln:** elf YAML-Regeln unter `rules/b-muster/`, mindestens eine für jede
Prüfung B08–B17, auf Deutsch und Englisch. Jede Regel hat mindestens zwei positive und zwei
negative Testfälle in der Datei; die CI prüft sie und die Namenskonvention.
**ATR:** 157 Regeln aus `v4.0.0` (Commit `464548b`), übernommen mit `scripts/vendor_atr.py`.
Engine: `luibui_scan/textrules.py`, Analyzer `analyzers/b_muster.py`. 191 neue Tests.

**Entscheidungen:**
- **Nur eigene Regeln sperren.** ATR-Treffer werden höchstens H (Rot). Viele ATR-Regeln sind
  maschinell erzeugt, deshalb darf eine fremde Regel allein kein Paket sperren. Die ATR-Kategorie
  ergibt die Prüfkatalog-ID (Zuordnung in `textrules.ATR_KATALOG`).
- **ATR-Auswahl in drei Stufen:**
  1. Nur Reifegrad `stable`/`experimental`, nur Regex auf Textfeldern (615 von 785 fallen hier
     weg).
  2. Die mitgelieferten Testfälle müssen mit unserer Engine bestehen (8 fallen weg).
  3. **Kein einziger Treffer im gutartigen Vergleichsbestand**: `anthropics/skills`,
     `modelcontextprotocol/servers`, `modelcontextprotocol/python-sdk`, zusammen alle
     Textdateien (5 fallen weg).

  Ohne Stufe 3 bekam `anthropics/skills` Rot mit Dutzenden Treffern von `ATR-2026-00061`. Alle
  Ausschlüsse stehen mit Grund in `rules/external/atr/QUELLE.md`.
- **Zitate werden herabgestuft:** Steht ein Treffer in Inline-Code, einem Code-Block oder in
  Anführungszeichen, wird K/H zu M, mit Hinweis „als Beispiel zitiert“. Doku über Angriffe wird so
  nicht gesperrt, aber zur Prüfung vorgelegt.
- **Geprüft werden nur Anweisungstexte:** Markdown, Text, Prompt-Dateien, YAML, JSON, TOML und
  Dateien ohne Endung. Code ist Ebene C. Lockfiles sind Daten für Ebene D.
- **ReDoS:** Jede Regex läuft über das Modul `regex` mit 0,5 s Timeout. Große Texte werden in
  überlappenden Blöcken zu 256 KB durchsucht. **Ein Timeout ist kein stilles „kein Treffer“**:
  Der Analyzer schlägt fehl, und das Ergebnis wird nie grün (Test).
- Neue Abhängigkeiten: `pyyaml` (MIT) und `regex` (Apache-2.0), dazu Typ-Stubs für die
  Entwicklung. `THIRD_PARTY_NOTICES.md` nennt ATR und gitleaks.

**Probe an echten Repos:** `anthropics/skills` ist Gelb mit zwei berechtigten M-Hinweisen (ein
zitiertes „disregard the previous instruction“ in einer Migrationsanleitung, ein Archiv im
Paket). `modelcontextprotocol/servers` ist ohne Befund.

**Grenze der Kalibrierung:** Der Vergleichsbestand umfasst drei Repos. S3-6 (Benchmark) erweitert
ihn und misst Erkennungs- und Fehlalarmrate.

## 2026-09-27 — S1-9 Analyzer D – Abhängigkeiten (D01–D05)

Die Ebene D besteht aus zwei Analyzern, damit eine fehlende OSV-Datenbank die übrigen Prüfungen
nicht verdeckt:
- **`d_abhaengigkeiten`:**
  - D03, Typosquatting: Abstand 1 zu verbreiteten Paketen, bei langen Namen 2, mit vertauschten
    Nachbarbuchstaben. Grundlage sind die eigenen Listen `rules/data/beliebte-pakete-{pypi,npm}.txt`.
  - D04, kein Lockfile oder keine festen Versionen.
  - D05, Git ohne Commit, `http://`, Pfade außerhalb, Direkt-Downloads.

  Manifeste (`requirements*.txt`, `pyproject.toml`, `package.json`) werden nur als Daten gelesen.
- **`d_osv`:** osv-scanner 2.6.0 **nur offline**, für D01 (bekannte Schadpakete, `osv:MAL-…`, K,
  gesperrt) und D02 (Schwachstellen; CVSS ≥ 9 → H, ≥ 7 → M, sonst N, unbekannt M). Die Quelle
  `https://osv.dev/<ID>` steht in jedem Befund (CC-BY-Pflicht der OSV-Daten).
- Beide laufen nur beim Paket und bei der Auswahl; bei Einzeldateien erscheinen sie als
  „nicht geprüft“.

31 neue Tests. Die OSV-Tests bauen eine eigene Mini-Datenbank und laden nichts herunter.

**Härtung osv-scanner:**
- **`--no-call-analysis=all`:** Laut Hilfe „will run build scripts“, das wäre ein Verstoß gegen
  Regel 1.
- `--offline --offline-vulnerabilities --no-resolve`, leere Umgebung, temporäres HOME außerhalb
  des Pakets, Timeout.
- In der Binärdatei stecken Validierer, die gefundene Secrets live bei Anbietern prüfen würden.
  Auch deshalb läuft das Werkzeug nur offline.
- Die Datenbank liegt **unter `<dir>/osv-scalibr/<Ökosystem>/all.zip`**, nicht wie dokumentiert
  unter `osv-scanner/`. Belegt im Quellcode von osv-scalibr 0.5.2.

**Betrieb:**
- osv-scanner ist mit Prüfsumme in Worker-Image und CI.
- Die Datenbank erwartet der Worker unter `/rules/osv` (Volume `luibui-rules`).
  **Sie ist noch nicht da:** Das Laden kommt von Googles Speicher, und die Frage „US-CDN“ ist
  offen. Bis dahin schlägt `d_osv` fehl, und Prüfungen sind höchstens Gelb.
- Der Kindprozess bekommt `LUIBUI_OSV_SCANNER` und `LUIBUI_OSV_DB`.

**Probe an echten Repos und Folgen:**
- `python-sdk` hatte 1.676 Dateien. Die CLI prüft lokale Ordner deshalb jetzt mit den
  Repository-Grenzen (10.000 Dateien, 200 MB) statt mit denen einer Upload-Auswahl.
- Fehlalarm D03: `httpx2` (legitimer Fork von Pydantic) galt als Typosquat von `httpx`. Er steht
  jetzt samt `httpcore2` in der Liste.
- gitleaks-Treffer in Beispiel- und Testpfaden (`.env.example`, `tests/`) sind jetzt **M statt H**.
  Dort stehen fast immer Platzhalter.
- A09 kennt jetzt auch `.git-blame-ignore-revs`, `.overrides`, `.readthedocs.yaml`, `.mailmap`.
- Ergebnis: `anthropics/skills` gelb (berechtigtes D04: `requirements.txt` ohne Versionen),
  `servers` ohne Befund, `python-sdk` gelb (Platzhalter-Secrets in Tests).
- **Nebenbei geklärt:** Hinweise zu fehlgeschlagenen und zu noch nicht eingebauten Prüfungen
  erscheinen jetzt beide, nicht nur der erste.

**Sprint 1, Analyzer:** A, B-Inhalte, B-Muster, Secrets und D sind fertig. Die Scan-Art
„schnell“ hat damit alle vorgesehenen Prüfungen, sobald die OSV-Datenbank da ist. Intensiv und
lokal warten auf C, E und G aus Sprint 2.

## 2026-09-27 — S0-12 Nachtrag: Worker-Kindprozess ohne Netz (Bedrohungsmodell T13)

Auf mittwald hatte der Worker Internet, weil mittwald keine Compose-Netze übernimmt. **Gelöst im
Kindprozess selbst:** Wenn `LUIBUI_NETZ_ISOLIEREN=1` gesetzt ist (Standard im Worker-Image), tritt
der Kindprozess vor jeder Arbeit in einen eigenen User- und Netz-Namensraum ein
(`os.unshare(CLONE_NEWUSER | CLONE_NEWNET)`) und bildet nur seine eigene UID/GID ab. Danach gibt es
nur noch die Loopback-Schnittstelle. Alle Scanner (gitleaks, osv-scanner) erben das.

**Auf dem Server geprüft** (im laufenden Worker-Container per SSH, vor dem Einbau):
- Vorher gelingt eine Verbindung zu 1.1.1.1:443.
- Danach scheitert sie mit errno 101 (Netz nicht erreichbar), auch aus einem Unterprozess.
- Lesen und Schreiben im Scratch funktioniert mit der UID-Abbildung weiter.

**Scheitert geschlossen:** Ist die Isolation verlangt und nicht möglich, läuft der Job nicht
(„Netzisolation nicht möglich“), statt ungeschützt zu prüfen. Der Test akzeptiert genau zwei
Ausgänge: nur Loopback oder Ablehnung.

**Lokal:** Dockers Standard-Seccomp-Profil verbietet `unshare()` bei `cap_drop: ALL` (geprüft).
Compose setzt deshalb `LUIBUI_NETZ_ISOLIEREN: "0"`, denn lokal hängt der Worker ohnehin nur im
internen Netz.

**Noch offen:** Der Elternprozess des Workers hat weiter Netz. Er braucht es für die Datenbank,
fasst aber keine Paketinhalte an. Die Annahme (`ANNAHME_OFFEN`) kann aufgehen, sobald zusätzlich
`X-Forwarded-For` geklärt ist.

## 2026-09-27 — S1-9 Nachtrag: OSV-Datenbank im Betrieb

Len hat den Download der OSV-Datenbank von osv.devs Speicher (Google Cloud Storage) freigegeben.
`apps/worker/luibui_worker/osvdb.py` lädt `all.zip` für PyPI, npm, Go und crates.io (zusammen
etwa 255 MB, npm allein 207 MB) nach `/rules/osv/osv-scalibr/<Ökosystem>/`, höchstens einmal
täglich und nur **im Elternprozess zwischen zwei Jobs**. Der prüfende Kindprozess bleibt ohne Netz.
Die neue Datei ersetzt die alte erst, wenn sie vollständig ist und sich als ZIP mit Einträgen
öffnen lässt. Obergrenze 1 GB je Datei, nur `https://`. Das Image legt `/rules/osv` für Nutzer
10001 an. 4 neue Tests.

**Echter Lauf** (Datenbank mit diesem Code geladen, 25 s): Die drei Vergleichs-Repos zeigen
jetzt echte, bekannte Schwachstellen, etwa `pillow 10.0.0` (CVSS 9,8 → H) in
`anthropics/skills`, `anyio` und `gitpython` in `modelcontextprotocol/servers`. Rot ist dort
berechtigt.

**Doppelte Befunde behoben:** OSV führt dieselbe Lücke unter mehreren Kennungen (`PYSEC-…`,
`GHSA-…`). Befunde werden jetzt nach den Gruppen von osv-scanner zusammengefasst: einer je Lücke,
bevorzugt mit `GHSA`-Kennung, die übrigen stehen als Alias im Beleg (Test).

**Außerdem:** `ENTWICKLERREGELN.md` (das Regelwerk von wanalyse) war mit `git add -A` in `ddc35de`
ins luibui-Repo geraten und ist wieder entfernt (`813072d`); die Datei liegt weiter auf der
Platte. Commits nennen ab jetzt ihre Dateien ausdrücklich. Eine gitleaks-Prüfung der ganzen
Git-Historie fand keine echten Secrets, nur zwei Platzhalter (leeres `POSTGRES_PASSWORD` in
`.env.example`, erfundener Test-Schlüssel).

## 2026-09-27 — Entwicklerregeln für luibui

Len hat das Regelwerk von wanalyse als `ENTWICKLERREGELN.md` in den luibui-Ordner gelegt, zum Anpassen.
Die Datei ist jetzt die luibui-Fassung. Die Struktur ist geblieben (Teil A–G, Anhang), der Inhalt auf
luibui übertragen:
- **Rangfolge:** Sicherheitsregeln aus CLAUDE.md vor dieser Datei, diese vor dem Chat. Len kann im Chat
  alles außer den Sicherheitsregeln ändern, die Änderung wird dann nachgetragen.
- Aus „Crawler“ wird **Teil D Engine und Regeln**, aus dem Schätzmodell **Teil E Ehrlichkeit der
  Bewertung** (kein Grün bei Unvollständigkeit, Kalibrierung, keine Schwelle senken).
- **Design-Tokens** aus `docs/design/`, alle Kontraste gerechnet. `#9EA3AD` (2,3:1) ist als Textfarbe
  ausgeschlossen.
- **Arbeitsweise aus den Erfahrungen dieser Woche:** Praxistest an echten Repos, Dateien einzeln
  committen, alle Prüfungen vor dem Commit, Werkzeugoptionen im Quellcode belegen.
- Am Ende steht ein **Umsetzungsstand**: was schon so läuft und was nicht (Client-IP, ADRs, Git-Hook,
  Fehlerformat, `/api/v1`, Drittdienste-Verzeichnis, Modulgröße, CI).

CLAUDE.md verweist jetzt auf die Datei. Die frühere wanalyse-Fassung steht weiter in der Git-Historie
(`ddc35de`).

## 2026-09-27 — Repo öffentlich, CI läuft, `02d85be` ausgerollt

Len hat das Repo auf **öffentlich** gestellt. Damit sind die GitHub-Actions-Minuten frei, und die CI
läuft wieder. Der erste echte Lauf seit S1-7 ist komplett grün: Python ohne übersprungene Tests (also
mit gitleaks und osv-scanner), Web und alle drei Images. CLAUDE.md sagt jetzt „öffentlich“.

`02d85be` ist ausgerollt, die Annahme bleibt geschlossen. **Im Produktions-Worker geprüft:**
- Netz-Isolation greift, der Kindprozess sieht nur `lo`.
- Die OSV-Datenbank lädt beim Start (255 MB in 13 s).
- Ein entschärftes Testpaket wird ohne Netz vollständig geprüft und gesperrt (B01, gitleaks,
  OSV/pillow).
- Für den Schnellscan fehlt keine vorgesehene Prüfung mehr; ein sauberes Paket kann dort grün werden.

RAM steht in `docs/infra-kapazitaet.md`.

**Folge der Öffentlichkeit:** Die frühere wanalyse-Fassung von `ENTWICKLERREGELN.md` steht in der
öffentlichen Historie (`ddc35de`). Sie enthält keine Secrets, aber Interna von wanalyse. Entfernen
ginge nur mit Umschreiben der Historie und Force-Push, und das nur auf Lens Wort.
`docs/infra-kapazitaet.md` nennt Projekt- und Container-IDs und den Namen des SSH-Schlüssels. Das sind
keine Geheimnisse, aber Hinweise für Angreifer.

## 2026-09-27 — S1-1 Nachtrag: Client-IP hinter dem Proxy, Löschlauf für Schnellscans

**Client-IP:** uvicorn läuft mit `--proxy-headers --forwarded-allow-ips` (`FORWARDED_ALLOW_IPS`). Auf
mittwald vertraut die API `X-Forwarded-For` nur aus dem Cluster-Netz `100.121.0.0/16`: Dort liegen der
Ingress (gesehen: `100.121.49.66`, `100.121.23.66`) und unsere Container (API `.161`, Web `.160`, Worker
`.162`). uvicorn liest die Kette von rechts und nimmt die erste nicht vertrauenswürdige Adresse, eine
gefälschte linke Hälfte zählt also nicht (Test). **Restrisiko:** Ein anderer Pod im Cluster-Netz könnte
eine IP vortäuschen. Damit ließe sich nur die Begrenzung je IP umgehen, an Anmeldung und Rechten ändert
das nichts. Lokal ist der Standard `127.0.0.1`.

**Zugriffslog aus:** Mit echten Client-IPs wären die Zugriffslogs personenbezogen (ENTWICKLERREGELN A11).
Deshalb gilt standardmäßig `--no-access-log`. `LUIBUI_ACCESS_LOG=1` schaltet es für eine kurze Prüfung
ein.

**Löschlauf:** Der Elternprozess des Workers löscht zwischen zwei Jobs höchstens stündlich abgelaufene
Schnellscans samt Befunden (Test). Einen eigenen Cronjob braucht es damit nicht.

## 2026-09-27 — Lücken aus dem Regel-Abgleich (Teil 1)

- **Git-Hook** `.githooks/pre-commit` ohne neue Abhängigkeit: ruff, Format, mypy und die Tests ohne
  Datenbank, bei Web-Änderungen `pnpm lint`. Aktivieren je Klon mit `git config core.hooksPath .githooks`
  (hier gesetzt).
- **CI prüft jetzt das eigene Repo:** gitleaks über die ganze Historie (`fetch-depth: 0`, bekannte
  Platzhalter in `.gitleaksignore`) und osv-scanner über `uv.lock` und `apps/web/pnpm-lock.yaml`.
- **Eigene Lücke behoben:** `postcss 8.4.31` (über Next.js) hatte vier bekannte Schwachstellen bis
  CVSS 7,5. Ein pnpm-Override hebt es auf `8.5.28`; Lint, Tests und Build laufen. Die Python-Abhängigkeiten
  waren ohne Befund.
- **`docs/drittdienste.md`** angelegt: mittwald, GitHub, osv.dev (nur Download), Git-Hosts.
- Bei beiden Voraussetzungen fürs Freischalten ist der Nachweis erbracht: Der Worker hat kein Netz,
  und die API sieht die echte Client-IP (geprüft mit kurz eingeschaltetem Zugriffslog, danach wieder
  aus). `ANNAHME_OFFEN` bleibt aus, bis Len entscheidet.

## 2026-09-27 — Lücken aus dem Regel-Abgleich (Teil 2)

- **Fehlerformat vereinheitlicht** (`luibui_api/errors.py`): Jede Antwort mit Fehler lautet
  `{"detail": {"code", "text", …}}`. Eigene Codes dort, wo Clients verzweigen: `totp_erforderlich`,
  `anmeldung_falsch`, `nicht_freigeschaltet`, `speicher_voll`, `zu_viele_versuche`,
  `zu_viele_schnellscans`, `warteschlange_voll`, `email_vergeben`, `name_vergeben`,
  `herkunft_ungueltig`, `browser_anmeldung_noetig` und die Ablehnungsgründe der Annahme. Alle übrigen
  bekommen einen Code nach Statuscode. **Validierungsfehler nennen nur die Felder**; FastAPI schickte
  vorher den eingegebenen Wert zurück, bei `passwort` also das Passwort (Test).
- **Alle Routen unter `/api/v1/`**, außer `/health`. Oberfläche und CLI bauen darauf.
- **`a_dateien.py` aufgeteilt:** `_a_ausfuehrung.py` (A02, A03), `_a_herkunft.py` (A10–A12), der Rest
  bleibt. Hilfsfunktionen (`read_text`, `read_json`, `file_name`, `rules_dir`) liegen in `_common.py`.
  Verhalten unverändert, alle Tests grün.
- Der Umsetzungsstand in `ENTWICKLERREGELN.md` ist nachgeführt. Offen bleiben ADRs, `docs/vvt.md`, die
  Oberfläche nach A5/A6/F6 (Sprint 2) und der AV-Vertrag mit mittwald.

## 2026-09-27 — S1-12 Kapazitätsmessung und Definition of Done Sprint 1

S1-12 ist gemessen, die Ergebnisse und die Empfehlung stehen in `docs/infra-kapazitaet.md`: klein 3,8 s,
mittel 20 s, groß 52 s, Speicher unkritisch, CPU-gebunden durch `b_muster`. Empfehlung: kein vServer vor
Sprint 4/6.

**Definition of Done Sprint 1 (Sprintplanung), Punkt für Punkt:**
- [x] Präparierte Archive (Bombe, `../`, Symlink, verschlüsselt) und Dateiauswahlen mit manipulierten
  Pfaden werden erkannt und verworfen — `test_intake.py`, `test_scans.py` (API), `test_safe_git.py`.
- [x] Eine einzelne `SKILL.md` mit versteckten Unicode-Anweisungen wird als Einzeldatei geprüft und
  gesperrt — `test_sprint1_dod_single_skill_file_with_hidden_instruction_is_locked`, zusätzlich im
  Produktions-Worker belegt.
- [x] Jede Regel in `rules/` hat mindestens einen positiven und einen negativen Testfall — eigene Regeln
  mindestens zwei je Richtung, übernommene ATR-Regeln bestehen ihre eigenen Testfälle
  (`test_analyzer_b_muster.py`).
- [x] `luibui scan corpus/benign/*` liefert keine K/H-Befunde — fünf Pakete, `test_corpus.py`.
- [x] Scratch ist nach jedem Scan leer — Worker-Tests und im Produktions-Worker geprüft.
- [ ] **Entscheidung vServer getroffen** — Empfehlung liegt vor (kein vServer vor Sprint 4/6), die
  Entscheidung trifft Len.

**Tasks Sprint 1:** S1-1 bis S1-12 sind umgesetzt. Zusätzlich vorgezogen: S2-6 (Anmeldung), S2-7
(Ablage), Teile von S2-13 (Schnellscan-API, ohne Oberfläche) und S3-1 (gutartiger Korpus). Offen aus
Sprint 1: nur die Server-Entscheidung.

## 2026-09-27 — Sprint 2 begonnen: Oberflächen für luibui.com und app.luibui.com

**Umgesetzt und ausgerollt** (`e38d316`, `6d1b3af`, `13e8b1c`):
- **Host-Weiche** (`apps/web/middleware.ts`): `app.*` → Entwicklerbereich (`app/entwickler`), sonst
  öffentliche Seite (`app/oeffentlich`). Die internen Präfixe sind von außen 404.
- **API-Proxy** (`next.config.ts`): Auf `app.*` wird `/api/v1/*` intern an `http://api:8000`
  weitergeleitet, damit das Session-Cookie host-only bleibt (Regel 11). Auf `luibui.com` sind nur die
  Schnellscan-Routen durchgelassen. Next.js puffert standardmäßig nur 10 MB; mit
  `middlewareClientMaxBodySize: "61mb"` kommen Uploads bis zum API-Limit durch (19 MB getestet, 70 MB
  → 413).
- **Entwicklerbereich (S2-8, S2-9):** Anmelden (mit TOTP), Registrieren, Übersicht mit letzter Ampel je
  Projekt, Projekt anlegen, Upload (Datei, Dateien, Ordner mit relativen Pfaden, ZIP, Text, Git),
  Prüfungsliste, Bericht mit Ampeln, Note, Befunden nach Schwere, Belegen und kopierbarem Fix-Prompt,
  Aktualisierung alle 2 s, solange die Prüfung läuft, und Konto mit API-Tokens und Abmelden. Neu in der
  API dafür: `GET /api/v1/projects/{id}/scans` und `letzte_pruefung` in der Projektliste.
- **Öffentliche Seite (S2-11, Teil von S2-13):** Startseite mit Schnellscan, Ergebnisseite mit
  „ohne Gewähr“, „So prüfen wir“. Links zum Anmelden und Registrieren gehen auf `app.<host>`.
- **Gestaltung:** Tokens aus `docs/design` im Tailwind-Theme, Schriften lokal (Fontsource, OFL),
  Ampel immer mit Wort und Form, Fokusring, Skip-Link, `prefers-reduced-motion`.
- **Sicherheit:** Paketinhalt nur als Text (React escaped). Geprüft mit `<img onerror>` und
  `<script>` im Beleg: im HTML nur escaped, in den Next-Daten als `<`. CSP in Produktion
  (`script-src 'self' 'unsafe-inline'`, Nonces später). Cookie `luibui_session` ohne `__Host-` nur
  lokal über http, weil Browser `__Host-` ohne `Secure` verwerfen.

**Geprüft:** lokal im kompletten Compose-Stack 13 Schritte von Ende zu Ende (Registrieren über
den Proxy, Upload, Worker, Berichtsseite mit „Gesperrt“, CSRF-Sperre, Schnellscan). In Produktion:
beide Hosts, Weiche, Proxy, Sperre der API-Routen auf `luibui.com`, CSP, keine Google-Verweise,
Weiterleitungen. Die Client-IP kommt auch über den Proxy richtig an: Next.js reicht
`X-Forwarded-For` durch, der Web-Container liegt im vertrauenswürdigen Netz.

**Offen:**
- **Impressum und Datenschutzerklärung fehlen.** Für eine öffentliche deutsche Seite sind sie Pflicht,
  der Inhalt kommt von Len.
- Die Annahme ist weiter zu (Len).
- Aus Sprint 2 fehlen noch: Einzelprüfungen per Drag & Drop auf der Übersicht, 2FA-Einrichtung in der
  Oberfläche, Speicherverbrauch, Datenexport und Konto löschen (S2-10), Downloads CSV/JSON/SARIF
  (S2-12), Schnellscan per Datei (S2-13), die Analyzer C, E, G (S2-1 bis S2-5).

## 2026-09-27 – S2-11: Startseite ohne Quellcode- und Katalog-Links, mit Zahlen und Prüfumfang

**Was:** Auf Lens Anweisung sind „Quellcode“ und „Prüfkatalog“ aus dem Menü von luibui.com entfernt, dazu
der GitHub-Link auf „So prüfen wir“. Das Repository soll wieder privat werden; die Seite verlinkt GitHub
nirgends mehr (nur der Platzhalter im Git-Feld nennt `github.com/besitzer/skill`). Die Startseite zeigt
nach dem Hero den Block „Mehr als jeder dritte KI-Skill hat eine Sicherheitslücke.“ mit drei Zahlen und
Quellen (Snyk „ToxicSkills“ 2026; Endor Labs 2026) und eine knappe Übersicht „Was luibui prüft“: vier
Paketarten mit je drei Beispielen, nur Prüfungen, die heute laufen. Der vollständige Katalog wird bewusst
nicht öffentlich gezeigt.

**Warum Wortlaut leicht angepasst:** 13,4 % sind „mehr als jeder achte“ (jeder achte wären 12,5 %). Endor
Labs misst, dass 82 % der MCP-Implementierungen Dateizugriffe nutzen, die für Path Traversal anfällig sind,
nicht dass 82 % nachweislich angreifbar sind; der Text sagt das so.

**Offen:**
- Im Footer steht weiter „Quellcode unter AGPL-3.0“. Wird das Repository privat, verlangt AGPL-3.0 §13
  trotzdem, Nutzern des Netzdienstes den Quellcode anzubieten. Len entscheidet: Lizenz wechseln (solange
  Len alleiniger Urheber ist, möglich) oder Quellcode auf Anfrage bereitstellen.
- Teil C des Scanner-Abdeckungs-Prompts (öffentliche Seite `/pruefkatalog` mit voller Matrix) widerspricht
  der neuen Vorgabe und wird nicht umgesetzt, solange Len es nicht anders sagt.

## 2026-09-27 – Scanner-Abdeckung, Teil A

**Was:** `docs/scanner-abdeckung.md` gleicht Lens Scanner-Matrix (48 Zeilen) mit dem Code ab. Ergebnis:
2 umgesetzt, 23 teilweise, 16 fehlen, 5 nur geplant (Sprint 2), 2 Konflikt. Nicht committet, weil das
Repository öffentlich ist und die Datei die Lücken der Prüfung genau benennt; Len entscheidet.

**Direkt behoben:** Die Startseite nannte bei MCP-Servern „Startbefehle in der MCP-Konfiguration“.
`.mcp.json` wird heute aber nicht ausgewertet (AGT-06). Ersetzt durch „Unsichtbare Zeichen in
Tool-Beschreibungen“ (B01/B02 laufen über alle Textdateien). Ausgerollt.

**Offen (Len):** OK für Teil B; Entscheidungen zu verschachtelten Archiven, tar/7z/rar, „jedes K sperrt“
in der Matrix gegen ● im Katalog, AGT-06 mit Netz gegen Worker ohne Netz.

## 2026-09-27 – Scanner-Matrix Teil B

**Was:** Lens Scanner-Matrix umgesetzt, soweit ihre Zeilen in Sprint 1/2 oder P1 liegen. Die
Konflikte hat Len zur Entscheidung übergeben; sie stehen im Prüfkatalog §13.
- Annahme: tar/tar.gz/bz2/xz über `intake/safe_tar.py` mit den ZIP-Regeln; 7z/RAR bleiben
  abgelehnt (Lizenz). Paketformate im Paket (`.whl`, `.dxt`, `.mcpb`, `.vsix`, `.xpi`, `.egg`,
  `.nupkg`) werden eine Ebene tief entpackt, mit dem Rest der Paket-Limits.
- Inventar erkennt Pickle, safetensors, GGUF, HDF5, TFLite, deb, rpm und Python-Bytecode am Inhalt.
- Neue Prüfungen: A13–A16, A18–A21, B21, C14, C15, E08, E09, G07, G08; A02/A03/A04/B06/B08–B17
  erweitert. A16 und B20 sperren jetzt.
- Neue Analyzer `e_konfig` (im Schnellscan erwartet) und `c_konfig`. `c_code`, `e_mcp`,
  `g_dsgvo` bleiben für den Intensivscan erwartet, bis S2-1 bis S2-5 fertig sind.
- Korpus: `corpus/generate.py` schreibt je Matrixzeile ein entschärftes Beispiel und ein gutartiges
  Gegenstück; Pickle-Beispiele verweisen nur auf `corpus/_dummy.py`.

**Warum so:** Keine neue Abhängigkeit (picklescan, oletools, pdfid, exiftool, python-magic): Alles
liest nur Bytes oder Text, kein Dokument- oder Bildparser wird angegriffen. Pickle wird nur mit
`pickletools.genops` gelesen, nie geladen.

**Geprüft:** Engine-Tests grün (u. a. 58 Korpus-Fälle). Die neuen Regeln gegen anthropics/skills,
modelcontextprotocol/servers und python-sdk: keine neuen K/H-Befunde; drei Fehlalarme in einem
Zwischenstand (Skript-Muster zu weit, `conftest.py` mit `subprocess`) vor dem Commit behoben.

**Offen:**
- MAL-01: Hash-Liste ist leer, YARA/ClamAV erst S4-10.
- `docs/scanner-abdeckung.md` und `docs/luibui_Scanner-Matrix.md` liegen nur lokal, weil das
  Repository öffentlich ist und beide die Lücken der Prüfung genau benennen (Len).

## 2026-09-27 – Ausgerollt: Scanner-Matrix Teil B und neues Design der Startseite

**Was:** `f9d4f64` in Produktion. luibui.com im Stil des Entwurfs aus `docs/design/Startseite`
(Kopf mit Logo, Hero mit Chips, Zahlenblock hell ohne Quellen, KI-Kacheln, Schritte, Ampel- und
Entwicklerbereichs-Karte, vierspaltiger Fuß). Inhalte des Entwurfs, die es noch nicht gibt
(Register, Suche, Spenden, Terminal, weitere Menüpunkte), sind bewusst nicht übernommen.
„So prüfen wir“ und die Beispiele auf der Startseite nennen die neuen Prüfungen.

**Geprüft:** CI grün, Health ok, Logs ohne Fehler, Screenshots bei 1440 px und 375 px (keine
horizontale Scrollbreite, per DevTools-Emulation gemessen).

## 2026-09-27 – Lizenzwechsel: proprietär statt AGPL-3.0

**Was:** Auf Lens Entscheidung steht luibui ab sofort unter einer proprietären Lizenz („Alle Rechte
vorbehalten“, `LICENSE`). Angepasst: Paketangaben (`LicenseRef-Proprietary`, Web `UNLICENSED`),
README, `rules/README.md`, Engine-README, CONTRIBUTING (Beiträge nur nach Absprache, Rechte gehen an
den Rechteinhaber), Konzept §1 und §13, Sprintplanung, `docs/scanner-tools.md`, CLAUDE.md. Im Footer
von luibui.com fällt „Quellcode unter AGPL-3.0“ weg, aus „Offene … Prüfstelle“ wird „Nicht-kommerzielle
Prüfstelle“. Der Entwurf in `docs/design/` bleibt als Entwurf unverändert.

**Warum möglich:** Len ist laut Git-Historie einziger Urheber (alle Commits). Fremde Werke (ATR-Regeln,
MIT) behalten ihre Lizenz und stehen in `THIRD_PARTY_NOTICES.md`.

**Grenzen:** Wer den öffentlichen Stand bis heute geklont hat, darf ihn weiter unter AGPL-3.0 nutzen;
das lässt sich nicht zurücknehmen. Neue Stände sind proprietär.

**Offen (Len):**
- Repository auf GitHub privat stellen (Settings → General → Danger Zone → Change visibility).
- Container-Images auf ghcr.io privat stellen. Sie enthalten den Python-Quellcode; öffentlich wären
  sie Weitergabe. Danach braucht mittwald Zugangsdaten für ghcr.io (Registry im Projekt anlegen, Token
  mit `read:packages`), sonst schlägt der nächste Deploy beim Image-Pull fehl.
- Private Repositories haben begrenzte kostenlose Actions-Minuten (Free: 2.000 min/Monat). Die CI
  braucht je Lauf einige Minuten über mehrere Jobs; bei vielen Pushes pro Tag kann das Kontingent
  knapp werden. Nichts wird gebucht.
- Nutzungsbedingungen für die CLI `luibui` (wird an Nutzer ausgeliefert) mit dem Anwalt klären.

## 2026-09-27 – S4-10 (vorgezogen): Liste bekannter Schadsoftware (A08, MAL-01)

**Was:** Die Hash-Liste ist gefüllt. Quelle ist der vollständige SHA-256-Export von MalwareBazaar
(abuse.ch, Schweiz; 1.144.573 Hashes am 27.09.2026), freigegeben von Len. Der Elternprozess des Workers
lädt ihn höchstens einmal am Tag (`luibui_worker/malwaredb.py`) und schreibt ihn als sortierte
32-Byte-Hashes nach `/rules/malware/sha256.bin` (37 MB). Eine neue Datei ersetzt die alte nur, wenn sie
vollständig ist und mindestens 100.000 Einträge hat. Die Handliste `rules/data/schadsoftware-sha256.txt`
bleibt für Ergänzungen.

**Nachschlagen:** `luibui_scan/malware.py` bildet die Datei per `mmap` ab und sucht binär. Gemessen:
Laden 0,1 s, 10.000 Abfragen 0,04 s, rund 53 MB Prozessspeicher statt geschätzt über 150 MB für ein
Python-Set. Umwandeln im Worker-Elternprozess: 3,3 s, Spitze 294 MB (zwischen zwei Jobs, Limit 1,5 GB).

**A08 als eigener Analyzer** (`a_schadsoftware`, in allen Scan-Arten erwartet): Fehlt die Liste, ist sie
beschädigt oder älter als 7 Tage, meldet der Bericht A08 als fehlgeschlagen, und das Paket wird nicht
Grün. Die übrigen A-Prüfungen laufen weiter. Ohne `LUIBUI_MALWARE_DB` (lokale CLI) gilt nur die Handliste.

**API:** Liest dieselbe Datei über das Volume `luibui-rules` (in Compose nur lesend) und legt Treffer nie
ab (Regel 10). Bisher sah die API nicht einmal die Handliste, weil `rules/` nicht im Image lag; jetzt wird
sie mitkopiert.

**Tests:** Handliste und Datenbank je positiv und negativ, Austausch der Datei, fehlende, beschädigte,
zu kurze und veraltete Liste, Update mit Kaputt-Download, zu großem Download und Export ohne Textdatei.
Alle 1.005 Python-Tests grün mit Postgres. `test_timeout_kills_the_whole_process_group` scheitert in
dieser Sandbox auch ohne die Änderung (Umgebung, nicht Code).

**Offen:**
- Deploy: Die Stack-Datei gibt der API das Volume `luibui-rules`. Erst nach dem Deploy (und dem ersten
  Download des Workers) wirkt die Liste in Produktion.
- Die CLI hat die große Liste nicht; ein `luibui update`-Befehl oder ein Download beim Scan folgt später.
- ClamAV und YARA-X (Rest von S4-10) bleiben in Sprint 4.

## 2026-09-27 – S3-9: Beispielbericht auf der Startseite, Lizenz und Schadsoftware-Liste ausgerollt

**Was:**
- Branch `claude/exciting-heisenberg-c29a9j` per Fast-Forward nach `main` (Lizenzwechsel auf
  „Alle Rechte vorbehalten“, MalwareBazaar-Liste für A08). Das Repository ist wieder privat.
- Startseite: Abschnitt „So sieht ein luibui-Prüfbericht aus“ direkt unter den Zahlen. Neue
  Komponente `components/report/ReportView` mit aufklappbaren Befunden (`aria-expanded`), die jetzt
  auch Entwicklerbereich und Schnellscan-Ergebnis nutzen; `showDsgvo={false}` auf der Startseite.
  Fixture `apps/web/content/beispielbericht.json`, Datum = Build-Datum. CSV-Download
  `/beispielbericht.csv` (statisch, Formel-Schutz), PDF-Knopf deaktiviert bis S3-11.
- Chip im Hero „Offen“ → „Nicht-kommerziell“ (Lizenzwechsel).

**Abweichungen vom Auftrag, bewusst:** Regel-IDs folgen dem Prüfkatalog statt der Vorlage
(`LB-A02-npm-install-skript` statt „A09“, `LB-C12-pfad-ohne-grenze` statt „C03“, `osv:BEISPIEL-2026-0001`).
Der niedrige Befund ist `LB-A09-versteckte-dateien`, weil ein fehlendes Lockfile (D04) laut
Katalog M ist und die Note dann 20 statt 24 wäre. Der Knopf heißt „Eigenes Repository prüfen –
Schnellscan“, weil der Schnellscan noch keine Dateien annimmt (S2-13).

**Geprüft:** 1.017 Python-Tests mit Datenbank, gitleaks und OSV; Web-Tests (Schema, Bewertung
gegen `scoring.py`, `<script>` im Beleg als Text, keine DSGVO-Elemente mit `showDsgvo={false}`,
CSV-Formeln); Lighthouse Barrierefreiheit 100; 375 px ohne seitliches Scrollen.

**Ausrollen ohne CI:** GitHub Actions startet im privaten Repository nicht („recent account
payments have failed or your spending limit needs to be increased“). Die Images wurden deshalb
lokal aus einem sauberen `git archive` von `22744ec` gebaut und nach ghcr.io gepusht, nachdem
alle CI-Prüfungen lokal grün waren. Worker lädt die Liste (1.144.645 Hashes), Health ok.

**Offen (Len):** GitHub-Abrechnung klären, sonst läuft keine CI.

## 2026-09-27 – Annahme geöffnet, Ausrollen mit Docker Desktop

**Was:** Auf Lens Entscheidung ist die Annahme offen (`ANNAHME_OFFEN=true`, jetzt Variable im
Stack): Registrierung, Upload und Schnellscan funktionieren für alle. Impressum und
Datenschutzerklärung fehlen weiterhin; Len trägt das Risiko bewusst.
`scripts/release.sh` ersetzt die blockierte GitHub-CI: Prüfungen wie in der CI (1.018
Python-Tests mit Datenbank, Web-Lint, -Tests und -Build), Images aus `git archive HEAD` für
linux/amd64 mit Docker Desktop, Push nach ghcr.io mit dem gh-Token, `mw stack deploy`, Warten auf
Health. Der Schalter behält beim nächsten Lauf seinen Wert, außer er wird gesetzt.

**Geprüft:** Ausgerollt `398197d`, Health ok, Registrierung antwortet mit Eingabeprüfung statt
„nicht freigeschaltet“.

**Offen:** Impressum und Datenschutzerklärung (Len); GitHub-Abrechnung.

## 2026-09-27 – Impressum und Datenschutzerklärung

**Was:** `/impressum` und `/datenschutz` auf luibui.com und app.luibui.com (gemeinsame Komponenten
`components/recht/`), verlinkt in beiden Fußzeilen und im Registrierungsformular. Vorlage: die
Rechtstexte von websecureaudit.de (gleicher Betreiber), angepasst an das, was luibui tatsächlich
tut. Neue Weiterleitung `hallo@luibui.com` → `info@websecureaudit.de` bei mittwald (kein Postfach).

**Offen (Len):** Den AV-Vertrag mit mittwald bestätigen (die Erklärung nennt mittwald als
Auftragsverarbeiter). Ob ein zweiter schneller Kontaktweg neben der E-Mail nötig ist (websecureaudit
hat ein Anfrageformular, luibui noch nicht). Rechtliche Prüfung der Texte (DoD Sprint 3).
Konto löschen und Datenexport im Portal (S2-10); bis dahin per E-Mail, so steht es in der Erklärung.

## 2026-09-27 – Kontaktformular, Rechtstexte abgeschlossen

**Was:** `/kontakt` auf beiden Hosts als zweiter Kontaktweg im Impressum. `POST /api/v1/kontakt`
schickt die Nachricht per SMTP (Postfach `noreply@luibui.com` bei mittwald, `mail.agenturserver.de:587`,
STARTTLS) an `hallo@luibui.com` (Weiterleitung an `info@websecureaudit.de`), Absender als
Reply-To, nichts wird gespeichert. Fünf Nachrichten pro IP und Stunde (nur Arbeitsspeicher),
Honeypot-Feld. `SMTP_PASSWORD` ist Stack-Variable; das Passwort wurde lokal erzeugt, nie
angezeigt und nach dem Ausrollen lokal gelöscht, `scripts/release.sh` übernimmt es aus dem Stack.

**Len, 27.09.2026:** AV-Vertrag mit mittwald gilt, die Rechtstexte sind geprüft. Die
Datenschutzerklärung nennt den Vertrag jetzt ausdrücklich.

**Geprüft:** 1.025 Python-Tests; Live-Testnachricht über luibui.com angenommen (202).

**Beobachtung:** Nach jedem Ausrollen antworten luibui.com und app.luibui.com einige Sekunden
bis Minuten mit 503/504 von nginx, weil mittwald die Container ohne Überlappung austauscht.

## 2026-09-27 – Upload mit Ablagefläche (Rückmeldung Len)

**Was:** Das Dateifeld im Projekt sah wie normaler Text aus, Drag & Drop fehlte. Neue Komponente
`components/app/Ablage.tsx`: Ablagefläche für Dateien, Ordner (mit relativen Pfaden) und Archive,
sichtbarer Auswahlknopf, Liste der Auswahl mit Anzahl und Größe, „Auswahl leeren“. Ein einzelnes
Archiv wird immer entpackt geprüft, auch unter „Datei(en)“.

**Geprüft:** Im lokalen Compose-Stack per Browser von Ende zu Ende (Registrieren, Projekt, Datei
per Knopf, ZIP per Drag & Drop, Bericht). Ausgerollt `999b0b3`.

**Offen:** Drag & Drop direkt auf der Übersicht für Einzelprüfungen (DoD Sprint 2).

## 2026-09-27 – Einzelprüfung per Drag & Drop auf der Übersicht, Formulare nur per POST

**Was:** Auf der Übersicht von app.luibui.com startet eine hineingezogene Datei (oder Ordner,
Archiv) sofort eine gründliche Prüfung ohne Projekt. `POST /api/v1/scans`: Eigentümer ist der
Nutzer, die Dateien werden nicht gespeichert, der Bericht bleibt bis zum Löschen
(`GET`/`DELETE /api/v1/scans`, fremde Prüfungen 404, laufende oder Projekt-Prüfungen 409). Der
Bericht trägt „Einzeldatei-Prüfung“. Damit ist der DoD-Punkt aus Sprint 2 erfüllt.

**Sicherheitsfund dabei:** Ein Formular, das abgeschickt wird, bevor React geladen ist, ging als
GET raus und schrieb E-Mail und Passwort in die Adresszeile (Browserverlauf, Proxy-Logs). Alle
Formulare haben jetzt `method="post"`, ein Test hält das fest.

**Geprüft:** 1.030 Python-Tests (5 neue für Einzelprüfungen, inkl. Nutzer-B-Isolation), Web-Tests,
im lokalen Stack per Browser von Ende zu Ende. Ausgerollt `68f3b90`.

## 2026-09-27 – S3-15: E-Mail-Bestätigung, Guthaben und PayPal

**Was (Entscheidung Len):** Schnellscan bleibt kostenlos. Nach bestätigter E-Mail sind 1 Projekt
und 3 Prüfungen gratis, jede weitere Prüfung kostet 1 Guthaben, ein zweites Projekt braucht einen
Kauf. Pakete 10 Prüfungen 4,90 €, 25 Prüfungen 9,90 €, Kleinunternehmer nach § 19 UStG wie
websecureaudit. Bei 402 öffnet die Oberfläche ein Aufladen-Fenster mit beiden Paketen und den zwei
Erklärungen nach § 356 Abs. 5 BGB; nach der Zahlung bestätigt die Rückkehrseite die Bestellung auf
dem Server und lädt die Ausgangsseite neu.

**Wie:** Bestätigungslink per Mail (SHA-256, 24 h, einmalig, 3 Mails pro Stunde). Guthaben als
Buchungsliste (`credit_entries`), Abbuchung unter Zeilensperre im selben Commit wie die Prüfung;
abgelehnte Eingaben kosten nichts, im Worker gescheiterte Prüfungen werden genau einmal
zurückgebucht. PayPal Orders v2 nur serverseitig (kein PayPal-Skript im Browser), Erfassung wird
gegen Betrag und Währung geprüft und genau einmal gutgeschrieben, Belegnummer aus einer Sequenz,
Webhook nur mit Signaturprüfung. Ohne PayPal-Zugangsdaten sind die Grenzen aus. Rechtstexte nach
den Vorlagen von websecureaudit: Nutzungsbedingungen, Widerrufsbelehrung, Datenschutz (PayPal,
Bestätigungslink, 10 Jahre Belege), Impressum (Einzelunternehmen, § 19 UStG). „Nicht-kommerziell“
ist von der Seite und aus CLAUDE.md/Konzept entfernt.

**Geprüft:** 1.045 Python-Tests (15 neu, u. a. Nutzer B kommt nicht an Käufe von A, falscher Betrag
schreibt nichts gut, doppelte Bestätigung schreibt einmal gut, Rücksprung nur auf app-Pfade,
Webhook ohne Signatur wirkungslos). Im lokalen Stack per Browser: Fenster erscheint bei der ersten
Prüfung ohne Guthaben, Kauf ohne echte Zugangsdaten scheitert mit Meldung.

**Offen (Len):**
- PayPal-Zugangsdaten der websecureaudit-App in `~/.config/luibui/paypal.env` ablegen
  (`PAYPAL_CLIENT_ID`, `PAYPAL_SECRET`, `PAYPAL_MODUS=live`), optional Webhook
  `https://api.luibui.com/api/v1/paypal/webhook` in der App anlegen und `PAYPAL_WEBHOOK_ID` ergänzen.
- **MalwareBazaar-Lizenz:** abuse.ch erlaubt die kostenlose Nutzung nur nicht-kommerziell. Vor dem
  Einschalten der Zahlungen klären, ob luibui dafür eine kommerzielle Lizenz braucht.
- Bestehende Konten müssen ihre E-Mail einmal bestätigen (Knopf auf der Übersicht).

## 2026-09-28 – macOS-Begleitdateien nicht mehr als getarnte Dateien (Rückmeldung Len)

**Was:** Ein auf dem Mac gepacktes ZIP (`marketing-skill.zip`, 376 Dateien unter `__MACOSX/`)
bekam 20× „Dateiendung passt nicht zum Inhalt“ (Hoch), Ampel Rot, Note 0. Die Dateien sind
AppleDouble-Begleitdateien (`._name`, Kennung `00 05 16 07`), die der Finder beim Komprimieren
anlegt: Dateiattribute, kein ausführbarer Inhalt, von keinem KI-Client geladen. Das Inventar
erkennt den Typ jetzt als `appledouble`. Stimmen Name (`._…`) und Kennung, entfällt A05 und
statt „Ungewöhnliche versteckte Dateien“ gibt es einen Hinweis `LB-A09-macos-metadaten` (I, kein
Abzug) mit dem `zip`-Befehl ohne Begleitdateien. Passt nur eins von beiden (z. B. ELF unter
`._SKILL.md`), bleibt A05 Hoch. `.codex/` (OpenAI Codex) gilt als bekannter versteckter Ordner.

**Geprüft:** 817 Engine-Tests (3 neu), ruff, mypy. Das ZIP von Len: vorher Rot/0, jetzt Gelb/94.

**Offen:** Übrig bleibt `ATR-2026-00443` (Word-Fragment Concatenation, M) auf einer SEO-Zeile
„`/seo-tips` not `/seo_tips`“ in `url-design-guide.md` – sehr wahrscheinlich Fehlalarm der
externen Regel, getrennt ansehen.
