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

**Nachtrag, ATR-2026-00443:** Der übrige Gelb-Befund (Mittel) auf „Underscores join words.“ in
einer SEO-Anleitung war ein Fehlalarm: Die dritte Bedingung der Regel (`join` + `words`) trifft
normale Prosa. Nach der Regel aus S1-7 (Fehlalarm im gutartigen Bestand → nicht übernommen) ist sie
entfernt. `scripts/vendor_atr.py` kalibriert jetzt zusätzlich gegen `corpus/benign/`, neues
Korpuspaket `seo-skill` mit genau solchen Formulierungen, neuer Test: keine übernommene ATR-Regel
schlägt im gutartigen Korpus an (vor dem Entfernen rot, danach grün). Das ZIP von Len: Note 100,
Ampel Gelb nur wegen „Prüfung unvollständig“ (C, E, G noch nicht eingebaut).

**Geprüft:** 819 Engine-Tests, ruff, mypy.

**Ausrollen:** noch nicht. Aus der Cloud-Sitzung fehlt das Schreibrecht auf ghcr.io; Len rollt am
Mac mit `scripts/release.sh` aus.

## 2026-09-28 – S2-12: Bericht als CSV, JSON und SARIF herunterladen

**Was:** Unter jedem fertigen Bericht auf app.luibui.com stehen drei Downloads:
`/pruefungen/<id>/bericht.csv`, `.json` und `.sarif`. Die Route holt den Bericht über
`GET /api/v1/scans/<id>` mit dem Sitzungs-Cookie, die Eigentümerprüfung bleibt also allein in der
API: fremde, unbekannte oder noch laufende Prüfungen geben 404, ohne Anmeldung 401, API nicht
erreichbar 503. CSV nutzt den
vorhandenen Baustein (`lib/csv.ts`: BOM, Semikolon, Formel-Schutz). SARIF 2.1.0 (`lib/sarif.ts`):
eine Regel pro `rule_id`, K/H → `error`, M → `warning`, N/I → `note`, `security-severity` für
GitHub, relative URIs, Zeile nur wenn bekannt, nur `message.text` (nie Markdown), Beleg und
Fix-Prompt als Eigenschaften. Schnellscans tragen „ohne Gewähr“ in jedem Format (CSV-Spalte
`scan_art`, JSON und SARIF als erster Hinweis). Dateiname aus Paketname und Datum, nur sichere
Zeichen; `Content-Disposition: attachment`, `nosniff`, `no-store`. Die öffentliche
Schnellscan-Seite zeigt die Links nicht, dort gibt es diese Routen nicht.

**Geprüft:** 19 Web-Tests (6 neu: SARIF-Aufbau, Schwere → Level, relative URIs ohne Markdown,
„ohne Gewähr“ in allen drei Formaten, nicht beim Intensivscan, sichere Dateinamen), ESLint, `tsc`,
`next build` (die drei Routen erscheinen als dynamische Routen).

**Offen:** Teilen eines Berichts per Link mit Zufalls-Token (zweiter Teil von S2-12, braucht eine
Tabelle und eine öffentliche Route, eigener Commit). SARIF-Import in GitHub Code Scanning (DoD
Sprint 2) von Hand prüfen, sobald ausgerollt; Actions laufen im privaten Repo derzeit nicht.
## 2026-09-28 – Befundkarte: Namen in Backticks als Code-Schrift

**Was:** Die Engine-Texte markieren Dateinamen und Befehle mit Backticks (`.md`, `__MACOSX/`). Die
Befundkarte zeigte sie wörtlich. Jetzt erscheint Text zwischen Backticks in Code-Schrift, in
Erklärung und Behebung. Weiter nur React-Text, kein Markdown, kein HTML; ein Test prüft, dass `<b>`
im Code-Teil escaped bleibt und ein einzelner Backtick unverändert stehen bleibt.

**Geprüft:** Web 14 Tests, eslint, tsc.

## 2026-09-28 – Logo und Überschriften in der Fließtextschrift (Wunsch Len)

**Was:** Logo und Überschriften stehen nicht mehr in Bricolage Grotesque, sondern in IBM Plex Sans
wie der Fließtext, auf beiden Oberflächen (der Kopf mit dem Logo ist gemeinsam). `--font-display`
zeigt auf Plex Sans, Plex Sans 700 wird für die fetten Überschriften mitgeladen, die
Bricolage-Abhängigkeit ist entfernt. Die enge Laufweite (bis −0,035 em) war auf Bricolage
abgestimmt und ließ Plex zusammenkleben; bei `font-display` jetzt einheitlich −0,01 em.

**Geprüft:** Web 20 Tests, eslint, tsc, `next build`, Startseite im lokalen Build per Screenshot.

## 2026-09-28 – Bestätigungslink direkt beim Prüfen anfordern (Rückmeldung Len)

**Was:** Konten von vor S3-15 haben nie eine Bestätigungsmail bekommen (sie geht nur bei der
Registrierung raus). Beim Prüfen stand trotzdem „Den Link haben wir dir geschickt“, ohne Weg, ihn
anzufordern; der Knopf lag nur auf der Übersicht. Jetzt erscheint bei `email_unbestaetigt` im
Upload und in der Einzelprüfung der Knopf „Bestätigungslink senden“ direkt unter der Meldung, und
die Texte in API und Übersicht behaupten keinen Versand mehr. SMTP-Anmeldung aus dem
Produktions-Container geprüft: funktioniert.

**Geprüft:** Web 20 Tests, eslint, tsc; API ruff, Tests ohne Datenbank.

## 2026-09-28 – S2-1: Analyzer C – Code, und im Bericht „Was geprüft wurde“ (Rückmeldung Len)

**Anlass:** Len fragte nach dem marketing-skill-ZIP (62 Python-Skripte, Note 100), ob wirklich
jede Datei auf Gefahren im Code geprüft wurde. Antwort: nein, Ebene C fehlte, und der Bericht
zeigte nicht, welche Prüfung welche Dateien erreicht.

**Was:**
- `analyzers/c_code.py`: Opengrep 1.30.0 nur mit eigenen Regeln (`rules/opengrep/`, C01–C12
  für Python, JavaScript/TypeScript und Shell, 25 Regeln, jede mit positivem und negativem
  Testfall, `opengrep scan --test`) und Bandit 1.9.4 für Python (C01, C02, C11, C13; Lärm wie
  `assert`, `import subprocess`, `subprocess` ohne Shell ausgelassen, Schwere vom Katalog
  gedeckelt). Nur Intensivscan und CLI, nicht im Schnellscan.
- Härtung: `--disable-nosem`/`--ignore-nosec`, keine `.semgrepignore`/`.gitignore`/`.bandit`
  aus dem Paket, Bandits Standard-Ausnahmen (`.git`, `.tox` …) aufgehoben, eigene leere
  Konfiguration, leere Umgebung, eigenes temporäres HOME, eigene Prozessgruppe (Timeout beendet
  auch `opengrep-core`), `--jobs 1`, `--max-memory 900`, Zeitlimits 150 s / 90 s (Job: 300 s).
  Belege mit Token-Maskierung (`masked` in `_common`, auch für B20).
- Sperrlisten-Regeln bewusst eng: C04 nur echte Geheimnis-Speicher (kein `.env`), C05 nur
  Zugangsdaten/Zwischenablage/Bildschirm → Netz, C07 ohne PATH-Zeilen in `~/.bashrc` aus
  Shell-Installern und ohne MCP-Einträge in Agent-Konfigurationen, `crontab -l` zählt nicht.
- Worker-Image: Opengrep mit Prüfsumme, einmal beim Bauen nach `/opt/opengrep-cache` entpackt
  (sonst 240 MB pro Job), `LUIBUI_OPENGREP`/`LUIBUI_OPENGREP_CACHE` an den Kindprozess.
  CI installiert Opengrep. `THIRD_PARTY_NOTICES.md` ergänzt (auch osv-scanner fehlte).
- Bericht: neues optionales Feld `abdeckung` (Schema), je Dateiart Anzahl, gelaufene und offene
  Prüfungen mit Grund, abgeleitet aus tatsächlich gelaufenen Analyzern (fehlgeschlagen oder
  übersprungen erscheint nie als geprüft). Einordnung nur nach Endung, weil die Werkzeuge so
  auswählen. Anzeige „Was geprüft wurde“ im Web, in der CLI und im Beispielbericht.
- Korpus: COD-01 (Python liest `~/.aws/credentials`) und COD-03 (JS `eval(atob(…))`).

**Kalibrierung:** `claude-skills-main` (779 Code-Dateien): Opengrep 1 Treffer auf der Sperrliste
(`skillopt-sleep` schreibt tatsächlich in die Crontab des Nutzers, offen dokumentiert; nach
Katalog C07 korrekt), Bandit 69 Hinweise, davon 14 × C01 H (`shell=True` mit Variablen), Rest N.
marketing-skill: 5 × N (`urlopen`, XML-Parser), Note 95. Mit Ködern (SSH-Schlüssel lesen und
versenden) im Worker-Container ohne Netz: C04 + C05 K, gesperrt. Speicherspitze Container 375 MB,
Dauer 47 s bei 1,5 CPU.

**Geprüft:** alle Python-Tests mit Opengrep (u. a. Umgehungsversuche mit `nosem`, `.semgrepignore`,
`node_modules/`, `.git/`, `.bandit`, Timeout räumt Prozessgruppe und HOME ab), Web-Tests, ruff,
mypy, eslint.

**Offen:**
- Entscheidung Len: Soll offen dokumentierte Persistenz (Beispiel `skillopt-sleep`) weiter
  sperren, oder reicht dafür Hoch? Der Katalog sagt K + Sperrliste.
- Opengrep-Regeln für weitere Sprachen (Go, Rust, PowerShell …) und C12 für JavaScript-MCP-Server;
  diese Dateien zeigt der Bericht jetzt als „für diese Programmiersprache noch nicht“.
- Anweisungen an die KI in Kommentaren und Strings von Code-Dateien werden nur erkannt, wenn sie
  kodiert oder unsichtbar sind.
- S2-2 (Cisco skill-scanner) bleibt offen.

## 2026-09-29 – S2-3: Analyzer E – MCP (ohne Cisco mcp-scanner)

**Entscheidungen Len (29.09.):** Offen dokumentierte Persistenz sperrt weiter (C07 bleibt K auf der
Sperrliste). E – MCP als eigene Umsetzung, ohne Cisco mcp-scanner (der bräuchte einen laufenden
Server oder eine selbst erzeugte Tool-Liste, bei litellm und MCP-SDK als Abhängigkeiten).

**Was:**
- `analyzers/_e_tools.py`: Tools statisch lesen, nichts importieren oder starten. Python über
  `ast` (FastMCP/SDK `@x.tool`, `@tool`, `Tool(name=…, description=…, inputSchema=…)`, Namen aus
  Konstanten und Enums, Parameter aus `Field(description=…)` und `inputSchema`), JavaScript/
  TypeScript über Muster (`server.tool("…", "…")`, jedes Objekt mit `description` und direkt
  folgendem `inputSchema`, Name aus `registerTool("…")`, `name:`, `const name =`, zod
  `.describe()`).
- `analyzers/e_mcp.py`: E01 alle B-Regeln (eigene und ATR) plus unsichtbare Zeichen (gleiche
  Ausnahmen wie B02 für Emoji und Schriften) auf Name, Beschreibung und Parameter; B16-Treffer
  werden E02 (Shadowing). E03 für Python: Handler führt Befehle aus oder ändert Dateien, Name und
  Beschreibung sagen es nicht (H). E04 HTTP/SSE ohne jede Anmeldung im Paket, Schlüssel aus der
  URL (H). E05 CORS `*` (M). E06 Token des Nutzers an Dritte durchgereicht (H). E04–E06 nur in
  Paketen mit MCP-Merkmalen. Nur Intensivscan und CLI.
- Bericht „Was geprüft wurde“: bei MCP-Servern, Plugins und gemischten Paketen die MCP-Prüfung je
  Code-Art, bei JavaScript/TypeScript „Beschreibung passt zum Code: bisher nur für Python“.
- Korpus AGT-08 (Tool-Beschreibung mit `<IMPORTANT>` und `~/.ssh/id_rsa`) samt harmloser Fassung.
- Konzept, Prüfkatalog, Sprintplanung und `scanner-tools.md` nachgezogen.

**Kalibrierung:** offizielle Referenz-Server `modelcontextprotocol/servers` (everything, fetch,
filesystem, git, memory, sequentialthinking, time; 58 Tools erkannt, Namen korrekt): kein
E01/E02/E03. Nur `everything` (Demo): SSE und Streamable HTTP ohne Anmeldung (E04) und CORS `*`
(E05, im Code selbst mit „use with caution“ kommentiert) – zutreffend. Harmloser Korpus: keine
Befunde.

**Geprüft:** 1.008 Python-Tests (22 neu für E, 1 für die Abdeckung), ruff, mypy.

**Offen:**
- E03 für JavaScript/TypeScript (Handler-Code den Tools zuordnen), E06 Klartext-Speicherung von
  Tokens, Prompts und Resources (Beschreibungen) noch nicht geprüft.
- Nur wörtlicher Text wird gelesen; zur Laufzeit zusammengesetzte Beschreibungen bleiben
  unbekannt. Ein LLM-Abgleich Beschreibung ↔ Code ist für Sprint 3 geplant.

## 2026-09-29 – S2-4: Analyzer G – DSGVO und Rechte

**Entscheidungen Len (29.09.):** Endpunkt im Code ohne bekanntes Land → nur Hinweis (I), sonst wäre
fast jedes Paket mit API-Aufrufen gelb. US-Endpunkt → Mittel („DPF prüfen“), mit Rechtsgrundlage im
Manifest nur Hinweis.

**Was:**
- `analyzers/g_dsgvo.py`, Achse dsgvo, nur Intensivscan und CLI. Endpunkte: URLs in einzeiligen
  Code-Strings von Dateien mit Netzwerkbibliothek (Python über `ast`, ohne Docstrings; JS/TS ohne
  Kommentare), `curl`/`wget` in Shell-Skripten, SDK-Importe (`openai` → api.openai.com usw.).
  Ausgelassen: localhost, private Netze, `*.example`/`.invalid`/`.test`, mehrzeilige Texte
  (Beispiel-HTML), Schema- und Namensraum-URLs, Link-Ziele wie github.com.
- G02 über `rules/data/laender.yaml` (EWR, Angemessenheitsbeschlüsse, USA als „teilweise“, 39
  Hosts mit festem Verarbeitungsort, SDK-Zuordnung). Drittland ohne Beschluss → H, mit Garantien
  laut Manifest → I (Selbstauskunft).
- Mit `luibui.json`: G01 Schema (`jsonschema`, Kopie des Schemas im Paket, Test gegen `spec/`)
  und Pakettyp gegen die Erkennung; G03 undeklarierte Endpunkte (Platzhalter `*.` unterstützt);
  G04 Shell, Netzwerk, Dateien schreiben, Umgebungsvariablen, Zugangsdaten; G05 Datenkategorien
  (Zugangsdaten, „keine“ trotz Endpunkten); G06 Selbstauskunft als Hinweis.
- Bericht „Was geprüft wurde“: „DSGVO: Endpunkte und Drittländer“ und „Abgleich mit luibui.json“
  (ohne Manifest mit Grund).
- Damit sind alle vorgesehenen Prüfungen eingebaut; ein vollständiger Scan ohne Befunde kann Grün
  werden. CLI-Tests setzen die Scanner jetzt ausdrücklich unerreichbar, damit sie mit und ohne
  installierte Werkzeuge dasselbe prüfen.

**Kalibrierung:** harmloser Korpus (4 Pakete mit Manifest): nur G06-Hinweis. MCP-Referenzserver:
nur `everything` (raw.githubusercontent.com, USA → M). marketing-skill: erst 4 Scheinendpunkte aus
Beispiel-HTML und XML-Namensräumen, nach Nachschärfung keine.

**Geprüft:** 1.041 Python-Tests mit Opengrep (26 neu für G, 1 für die Abdeckung), ruff, mypy.

**Offen:**
- Len: `rules/data/laender.yaml` fachlich freigeben (Stand der Angemessenheitsbeschlüsse, Brasilien).
- Endpunkte aus Konfigurationsdateien (`.env.example`, YAML) und zur Laufzeit zusammengesetzte URLs
  werden nicht erkannt; andere Programmiersprachen noch nicht.

## 2026-09-29 – Lücken der Ebenen B, C, E und G geschlossen (Auftrag Len: „alles, was nicht erkannt wird, soweit es Sinn macht“)

**Was:**
- **C, weitere Sprachen (S2-1):** Go, Ruby, PHP, Rust, Java, Kotlin, C# mit Grundmustern in
  Zeichenketten (C03, C04, C07, C10) und je Sprache Shell- und eval-Aufrufe (C01, C02, C08);
  PowerShell und Batch als Regex-Regeln (Download-Cradle, `-EncodedCommand`, Aufgabenplanung,
  Run-Schlüssel, TCPClient-Shell). Skripte ohne Endung werden über das Shebang geprüft.
  Text-Regeln ohne Konstanten-Weitergabe (sonst doppelte Treffer an späteren Verwendungen).
- **B in Code (S2-14):** Kommentare und Python-Docstrings werden mit B08–B17 geprüft, nur K- und
  H-Regeln. Kalibrierung an ca. 800 Code-Dateien (claude-skills-main, MCP-Referenzserver,
  marketing-skill): 3 Treffer, alle B15 (M) auf normaler Programmlogik → deshalb nur K/H.
- **E (S2-3):** Prompts und Resources (Python-Dekoratoren, `registerPrompt`/`registerResource`)
  werden gelesen und geprüft; E03 für JS/TS über den Handler im selben Aufruf; E06 Tokens, die ohne
  Schlüsselspeicher in Dateien geschrieben werden (`token.json`, `TOKEN_PATH` …), ohne Testdateien.
- **G (S2-4):** Endpunkte aus Konfiguration (`.env*`, YAML, TOML, JSON, INI, nur Ziel-Schlüssel,
  keine Projektlinks) und aus den weiteren Sprachen, wenn sie einen Netzwerk-Client nutzen.
- **Bericht:** neue Dateiart „Weitere Programmiersprachen“, „Anweisungen an die KI in Kommentaren
  und Docstrings“ als geprüft, MCP-Abgleich auch für JS/TS, Endpunkte auch für Konfiguration.

**Bewusst nicht:** zur Laufzeit zusammengesetzte Texte und URLs (statisch nicht bestimmbar, LLM-
Abgleich in Sprint 3); Datenfluss und Pfadprüfung (C05, C06, C12) für die weiteren Sprachen;
MCP-Server in Go/Rust; Hilfsfunktionen von JS-Handlern in anderen Dateien.

**Kalibrierung:** Keine neuen K/H-Befunde durch die Erweiterungen auf claude-skills-main (779 Code-
Dateien), MCP-Referenzservern und marketing-skill. Aufgefallen, aber älter: B08/B09/B14/ATR-00030
treffen in claude-skills-main einige Markdown-Stellen, die harmlos wirken (z. B. „Command:
/cs:ai-act-readiness“ als B08 K). Eigene Kalibrierung der B-Regeln gegen diesen Bestand offen.

**Geprüft:** 1.081 Python-Tests ohne Datenbank, 43 Opengrep-Regeltests, ruff, mypy.

## 2026-09-29 – S1-7: B08, B09, B14 an echten Skills kalibriert, ATR-2026-00030 entfernt

**Anlass:** In claude-skills-main (Markdown) trafen 12 Stellen mit K/H, alle harmlos, zwei davon
sperrend.

**Was:**
- B08: `<system>` zählt nur am Zeilenanfang oder als schließendes `</system>`; ChatML-Marker
  brauchen den senkrechten Strich (`<|system|>`). Vorher sperrte der Platzhalter in
  „Command: /cs:ai-act-readiness <system>“.
- B09: „Do not tell the user whether/if/how/which/to …“ ist eine Beratungsgrenze, kein
  Verschweigen („Do not tell the user whether to apply — that is a personal investment
  decision“). „Do not tell the user that …“ bleibt K.
- B14: Redewendungen „safety net“, „safety wheels“, „safety alignment/training“ ausgenommen;
  „skip the security checks“ bleibt H.
- ATR-2026-00030 (Cross-Agent Attack) nach dem Verfahren aus S1-7 entfernt: trifft „acting on
  behalf of an organization“. 155 statt 156 ATR-Regeln.
- Neues harmloses Korpuspaket `corpus/benign/beratungs-skill` mit sinngemäß umformulierten
  Fundstellen; die Korpustests halten sie dauerhaft ruhig. Regeltests je Regel ergänzt.

**Ergebnis:** claude-skills-main, MCP-Referenzserver, marketing-skill: 0 K/H aus den B-Regeln
(vorher 12). Es bleiben 27 M, überwiegend zitierte Beispiele in Sicherheitsdokumentation.

**Geprüft:** 993 Python-Tests, Regeltests B08–B17.

## 2026-09-29 – S2-5: Korrelation und Fingerprints

**Was:**
- `korrelation.py`: Verweise aus Anleitungen, die ein Agent liest (SKILL.md, AGENTS.md, CLAUDE.md,
  GEMINI.md, Cursor/Windsurf/Cline-Regeln, Markdown in `commands/`, `agents/`, `prompts/`,
  `rules/`), über Markdown-Links, Pfade in Backticks, Befehle (`python`, `bash`, `node`, `uv run`,
  `pwsh -File` …) und `./x`, mit Platzhaltern wie `${CLAUDE_PLUGIN_ROOT}/` oder `{baseDir}/`.
  Ketten über verlinktes Markdown bis Tiefe 3; nie außerhalb des Pakets.
- Hochgestuft wird nur Code, auf den verwiesen wird, und nur Befunde der Ebenen A, C, E (M→H,
  H→K), mit Hinweis auf die verweisende Zeile, `hochgestuft_von` und `verweise` (Fingerprints der
  Befunde in der verweisenden Datei). Nicht bei Einzeldateien und im Schnellscan.
- Jeder Befund bekommt einen Fingerprint aus Regel, Datei und Beleg (ohne Zeile, damit er über
  Versionen stabil bleibt); Grundlage für den Befund-Status (S3-7). Der Worker speichert beides.
- Befundkarte: „hochgestuft von …“.

**Kalibrierung:** Erster Entwurf stufte in claude-skills-main 112 Befunde hoch, 76 davon
Werkzeugrechte (E08) in Agent-Definitionen und viele bewusst herabgestufte Zitate in Markdown.
Beschränkt auf Code und Ebenen A/C/E: 6 (zweimal `shell=True` mit variablem Befehl in Skripten,
die eine SKILL.md ausführen lässt, H→K; zweimal `torch.load`, zweimal CORS `*`, M→H).
marketing-skill: 0.

**Geprüft:** 1.008 Python-Tests (15 neu), 23 Web-Tests, ruff, mypy, eslint.

## 2026-09-29 – Sprint 2: Definition of Done Punkt für Punkt geprüft

**Ergebnis Aufgaben** (Einzelheiten in der Sprintplanung): S2-6 und S2-11 erfüllt; S2-7, S2-8,
S2-9, S2-10, S2-12, S2-13 weitgehend, mit offenen Teilen. Größte Lücken: Konto (Profil ändern,
2FA einrichten, Speicherverbrauch, **Datenexport, Konto löschen**), Teilen per Link, Schnellscan
mit Datei bis 2 MB, offene K/H auf der Übersicht, Passwort vergessen.

**Ergebnis DoD:** 8 von 10 erfüllt. Offen: SARIF-Import in ein echtes GitHub-Repository
(Schema-Prüfung bestanden) und das Öffnen der CSV in Excel/LibreOffice von Hand.

**Heute dazu gebaut:**
- `apps/api/tests/test_isolation.py`: alle API-Routen mit Ressourcen-ID aus dem OpenAPI-Schema,
  Nutzer B bekommt für jede Ressource von A ein 404; neue Parameter lassen den Test scheitern,
  bis sie aufgenommen sind.
- SARIF: jedes Ergebnis hat einen Ort (paketweite Befunde an `luibui.json`, Zeile 1), weil GitHub
  Ergebnisse ohne Ort ablehnt; gegen das OASIS-Schema 2.1.0 geprüft (0 Fehler).
- Tests für CSV mit `+`, `-`, CR und für Markdown-Bild-Links und `javascript:`-Links als Text.
- Belege aller Analyzer werden zentral in der Pipeline maskiert (Regel 6); vorher nur bei C und
  Secrets. Maskiert werden Folgen ab 20 Zeichen mit Ziffer und Buchstabe (Schlüssel, Tokens),
  lange Bezeichner bleiben lesbar.

**Live geprüft:** keine externen Ressourcen (CSP `default-src 'self'`), Session-Cookie
`__Host-luibui_session` ohne Domain, `luibui.com/api` erreicht die API nicht, Schnellscan 5 s mit
„ohne Gewähr“.

## 2026-09-29 – S2-6/S2-10: Passwort vergessen, Datenexport, Konto löschen

**Was:**
- **Passwort vergessen (S2-6):** `POST /auth/passwort-vergessen` antwortet immer gleich (keine
  Prüfung, ob eine Adresse registriert ist), höchstens 3 Anforderungen pro Stunde je Adresse und IP;
  Link 60 Minuten, einmal, nur SHA-256 gespeichert. `POST /auth/passwort-neu` setzt das Passwort,
  beendet alle Sitzungen; die Zwei-Faktor-Anmeldung bleibt. Migration `0004`: `email_tokens.zweck`
  (`bestaetigung`/`passwort`) – vorher hätte ein Link beider Arten für beides gegolten. Seiten
  `/passwort-vergessen`, `/passwort-neu`, Link auf der Anmeldeseite.
- **Datenexport (S2-10, Art. 15/20):** `POST /konto/export` mit Passwort (und Code bei 2FA), nur mit
  Sitzung: ZIP mit `konto.json` (Konto, Sitzungen, Tokens ohne Schlüssel, Guthaben, Käufe, eigenes
  Protokoll), Einzelprüfungen, je Projekt `projekt.json`, `pruefungen.json` mit allen Berichten und
  die gespeicherten Dateien entschlüsselt. Temporär im Scratch, nach dem Senden gelöscht.
- **Konto löschen (S2-10, Art. 17):** `POST /konto/loeschen` mit Passwort, Code und „LÖSCHEN“:
  löscht Konto, Projekte, Versionen, Prüfungen, Befunde, Tokens, Sitzungen und die Dateien auf dem
  Volume (nach dem Commit). Kaufbelege bleiben 10 Jahre ohne Kontoverbindung. Audit-Eintrag
  `konto.geloescht` ohne Akteur.
- Kontoseite: „Deine Daten“ und „Konto löschen“. Datenschutzerklärung angepasst (Passwort-Link,
  Selbstbedienung für Auskunft, Übertragbarkeit, Löschung).

**Geprüft:** 141 API-Tests mit Datenbank (9 neu: Export vollständig und ohne Geheimnisse, 2FA und nur
mit Sitzung, Löschen samt Dateien und ohne Folgen für andere Nutzer, Belege bleiben, Reset gleich
antwortend, einmalig, Sitzungen beendet, Links nicht austauschbar, 2FA bleibt, Begrenzung),
Migrationsabgleich, 24 Web-Tests, eslint, ruff, mypy.

## 2026-09-29 – Fehlerfenster nach einem Neustart der API geschlossen

**Befund:** Nach jedem Ausrollen hingen Anfragen über die Weboberfläche bis zu zwei Minuten und
endeten mit 500. Gemessen mit einem gezielten API-Neustart und einer Anfrage pro Sekunde: rund
25 Sekunden lang liefert das Cluster-DNS für `api` noch die Adresse des beendeten Containers; eine
Verbindung dorthin bekommt keine Antwort, und Linux gibt erst nach etwa 127 Sekunden auf.

**Was:** `apps/web/lib/api-verbindung.ts` mit einem Agenten für die Weiterleitung `/api/v1`
(`http-proxy` in Next.js übergibt `agent: false`, Node legt dann eine Instanz der Klasse des
globalen Agenten an): höchstens 2 Sekunden je Verbindungsversuch, danach neu nachschlagen, bis zu
30 Sekunden lang, ohne Keep-Alive. Vor dem Verbindungsaufbau ist nichts gesendet, der Wiederversuch
ist also auch für Uploads sicher. Eingebunden in `instrumentation.ts`. Serverseitige Lesezugriffe
(`apiGet`) wiederholen bei Verbindungsfehlern ebenfalls bis zu 30 Sekunden.

**Geprüft:** 3 Tests (tote Adresse, dann richtige; Aufgeben nach der Frist; `agent: false`), lokal
mit gebautem Server: Anfrage ohne laufende API, Ersatz-API nach 3 s → Antwort nach 3,2 s statt 500.

**Nebenbefund:** Die Weiterleitung von Next.js hat eine Frist von 30 Sekunden ohne Daten
(`proxyTimeout`). Ein Datenexport, der länger zum Zusammenstellen braucht, würde so abbrechen.
Bei 500 MB Kontingent vorstellbar; offen.

## 2026-09-29 – S2-10: Datenexport als Datenstrom

**Was:** Das Export-ZIP wird beim Erzeugen gesendet (`StreamingResponse`, `zipfile` in einen nicht
zurückspulbaren Puffer), statt erst vollständig als Datei im Scratch zu entstehen. Alle Angaben aus
der Datenbank werden vorher gelesen, beim Senden wird nur noch entschlüsselt und gepackt.
Speicherbedarf je Block (1 MiB), keine Datei auf der Platte, und die 30-Sekunden-Frist der
Weiterleitung greift nicht mehr, weil laufend Daten fließen.

**Geprüft:** neuer Test mit 3 MB nicht komprimierbarer Datei: Antwort ohne `Content-Length`,
ZIP unversehrt (`testzip`), Inhalt gleich, keine Export-Datei im Scratch. 142 API-Tests.

## 2026-09-29 – S2-12: Bericht per Link teilen

**Was:** `POST /api/v1/scans/{id}/teilen` erzeugt für eine fertige Prüfung einen Link mit
256-Bit-Zufallstoken (nur SHA-256 in `scans.share_token_hash`, Spalte gab es schon); ein neuer
Link ersetzt den alten, `DELETE …/teilen` beendet das Teilen, Löschen der Prüfung oder des
Projekts ebenso. `GET /api/v1/geteilt/{token}` ohne Anmeldung liefert nur den Bericht und das
Prüfdatum, keine Kontodaten. Öffentliche Seite `luibui.com/bericht/<token>` (noindex), im
Entwicklerbereich „Bericht teilen“ unter den Downloads; der Link wird nur einmal angezeigt.
`geteilt` im Prüfungsstatus und im Datenexport. Isolationstest nimmt die öffentliche Route
ausdrücklich aus (der Link ist die Berechtigung). Datenschutzerklärung ergänzt.

**Geprüft:** 4 API-Tests (nur fertige Prüfungen, anonymer Abruf ohne Kontodaten, nur Hash
gespeichert, neuer Link ersetzt alten, Beenden, Link stirbt mit dem Projekt, kaputte Tokens → 404),
Isolationstest deckt die neuen Routen mit `scan_id` ab, 2 Web-Tests.

## 2026-09-29 – S2-13: Schnellscan mit Datei, Knopf zum Intensivscan

**Was:** `POST /api/v1/quickscans` nimmt neben der Git-URL (JSON) auch genau eine Datei als
Formular (`datei`) bis 2 MB; ZIP und tar werden über `intake/` entpackt, alles andere als
Einzeldatei geprüft. Eine zu große Datei gibt 413 `zu_gross` und zählt nicht gegen das
Rate-Limit; Git und Datei teilen sich Limit und Warteschlangen-Grenze. Gespeichert wird wie
bisher nur der Bericht (7 Tage). Auf luibui.com schaltet das Formular zwischen „Öffentliches
Repository“ und „Eine Datei oder ein ZIP bis 2 MB“ um, die Größe wird schon im Browser geprüft.
Die Ergebnisseite hat den Abschnitt „Gründlich prüfen“ mit „Intensivscan starten“ (zur
Registrierung auf app.luibui.com).

**Geprüft:** 5 neue API-Tests (Datei wird geprüft und nicht abgelegt, Archiv wird entpackt,
über 2 MB → 413 ohne Zählung, gemeinsames Limit, fehlende Datei → 422), 18 Tests in
`test_git_scans.py`, Web-Lint, 29 Web-Tests, Build.

**Nachtrag nach dem Ausrollen:** Live gab eine 2,2-MB-Datei 500 statt 413. Die API antwortete
vor dem Lesen des Bodys, die Weiterleitung von Next.js schrieb noch und scheiterte mit `EPIPE`.
Jetzt liest die API zu große Bodys bis 16 MB ab und verwirft sie, erst dann kommt 413; darüber
bleibt der sofortige Abbruch (die Oberfläche prüft die Größe schon im Browser). Dasselbe Muster
betrifft die Upload-Grenze der Projekt-Routen (`_check_size`); offen.

## 2026-09-29 – S1-1: zu große Uploads erst ablesen, dann abweisen

**Was:** Die Korrektur aus S2-13 gilt jetzt für alle Uploads. `uploads.ablesen()` liest einen
zu großen Body bis 80 MB und höchstens 15 s lang und verwirft ihn, dann kommt 413. Grund: Hinter
der Weiterleitung von Next.js wird eine Antwort, die kommt, während noch gesendet wird, zu
`EPIPE` und damit zu 500. Angekündigte Bodys über 80 MB werden sofort abgewiesen; Next.js
schneidet ohnehin bei 61 MB ab. Die Oberfläche begrenzt Projekt-Uploads schon im Browser auf 50 MB.

**Geprüft:** lokal über den `http-proxy` von Next.js mit 2,2 MB und 70 MB: 413, kein Proxy-Fehler;
Gegenprobe ohne Korrektur: `EPIPE`. 151 API-Tests.

## 2026-09-29 – S2-8: offene kritische und hohe Befunde auf der Übersicht

**Was:** `GET /api/v1/projects` liefert je Projekt `offen_k` und `offen_h`: kritische und hohe
Befunde der letzten *fertigen* Prüfung, ohne die als behoben, akzeptiert oder bestritten
markierten (`finding_status`, per Fingerprint). Die Liste ist danach sortiert (erst kritisch,
dann hoch, dann nach Alter). Neu `GET /api/v1/projects/offene-befunde`: alle offenen K/H-Befunde
über alle Projekte, kritische zuerst, höchstens 50. Die Übersicht zeigt oben „Offene kritische und
hohe Befunde“ (10 sichtbar, Link zum Bericht) und in jeder Projektzeile „1 kritisch · 2 hoch offen“.
Schwere mit Farbe, Form und Wort.

**Geprüft:** 3 API-Tests (Sortierung und Zählung, markierte Befunde und eine wartende neuere
Prüfung zählen nicht, Nutzer B sieht nichts von A), 157 API-Tests, Web-Lint, 29 Web-Tests.
Die Übersicht selbst ist nur per Typprüfung und Lint geprüft, nicht mit echten Daten angesehen.

**Offen in S2-8:** Quelle beim Anlegen wählen, Versionsliste.

## 2026-09-29 – S2-8: Quelle beim Anlegen, Versionsliste, Versionen löschen (S2-7)

**Was:** Beim Anlegen eines Projekts wird die Quelle gewählt (Datei(en), Ordner, Archiv, Text,
Git); bei Git ist die Adresse Pflicht (API: 422 ohne Adresse). Das Upload-Feld auf der
Projektseite ist danach vorgewählt, bei Git mit der gespeicherten Adresse. Ältere Projekte haben
die Quelle „zip“ (bisheriger Standard) und zeigen deshalb „Archiv“ vorgewählt.
Neu `GET /api/v1/projects/{id}/versions` (neueste zuerst, mit Dateizahl, Größe, Commit und der
letzten Prüfung dieser Version) und `DELETE /api/v1/projects/{id}/versions/{version_id}`: löscht
die Version und ihre verschlüsselten Dateien (nach dem Commit), die Prüfungen und Berichte
bleiben (`scans.version_id` wird NULL), Audit `version.geloescht`. Die Projektseite zeigt die
Versionen mit Ampel, Note und „Löschen“.

**Isolationstest:** setzt jetzt alle Pfad-Parameter ein, nicht nur den ersten (die neue Route hat
zwei); `version_id` ergänzt.

**Geprüft:** 4 neue API-Tests (Liste und Zuordnung, Löschen entfernt Dateien und lässt den
Bericht, Version nur über das eigene Projekt erreichbar, Git braucht Adresse), 158 API-Tests,
Web-Lint, 29 Web-Tests. Die Seiten selbst nur per Typprüfung und Lint geprüft.

S2-8 ist damit vollständig.

## 2026-09-29 – S2-8: Entwicklerbereich als Explorer, Breadcrumbs, Projekte löschen

**Was (Wunsch von Len, Vorbild: sein Projekt wanalyse):** app.luibui.com ist jetzt in Spalten
aufgeteilt. Links eine dunkle Leiste mit den Bereichen (Übersicht, Projekte, Einzelprüfungen,
Konto; unten E-Mail, Abmelden, Rechtliches), daneben die Einträge des Bereichs (Projekte mit
Ampelpunkt und Zahl offener K/H-Befunde, „+ Neues Projekt“, Einzelprüfungen; im Konto die
Abschnitte), rechts der Inhalt. Auf dem Handy wird die Leiste zur waagerechten Navigation, die
mittlere Spalte entfällt. Statt „← Übersicht“ steht oben ein Breadcrumb
(`components/app/Brotkrumen.tsx`, letzte Stufe mit `aria-current="page"`). Die Seiten liegen in
zwei Routengruppen: `(bereich)` mit dem neuen Layout, `(einstieg)` (Anmelden, Registrieren,
Rechtliches) mit dem bisherigen Kopf; die URLs bleiben gleich.
Neue Seiten `/projekte` (Anlegen und Liste) und `/pruefungen` (alle Einzelprüfungen). Die
Übersicht zeigt zuerst Projekte und „Schnell prüfen“, dann offene K/H-Befunde, dann die letzten
fünf Einzelprüfungen. Projekte lassen sich auf der Projektseite löschen (Name eintippen; die
API-Route gab es schon, die Oberfläche fehlte).

**Geprüft:** lokal mit API, Vorschau-Datenbank und echten Engine-Berichten angesehen (Übersicht,
Projekt, Bericht, Handybreite 390 px); 2 neue Web-Tests (Breadcrumb verlinkt und escaped),
31 Web-Tests, Lint, Build.

## 2026-09-29 – S3-11 (vorgezogen): Prüfbericht als PDF, Standard und Detail

**Was (Wunsch von Len):** Neben CSV, JSON und SARIF gibt es im Bericht „PDF“ und „PDF mit Details“.
`GET /api/v1/scans/{id}/bericht.pdf?umfang=standard|detail` (Eigentümer-Prüfung wie überall,
fremde Prüfung 404, unfertige 409). Standard: Deckblatt mit Gesamt-, Sicherheits- und DSGVO-Ampel
(Wort und Farbe), Note, Freigabe, Umfang, Scan-Art, Datum, Hinweisen, dazu eine Zeile pro Befund.
Detail: jeder Befund aufgeklappt wie im Web (Erklärung, Beleg, Fix, Fix-Prompt, Bezug), dazu
„Was geprüft wurde“. Auf jeder Seite Kopf und Haftungsausschluss, beim Schnellscan „ohne Gewähr“
im Kopf jeder Seite.

**Entscheidung (Len):** ReportLab 5.0.1 (BSD) statt WeasyPrint: klein, wenig RAM, keine
Systembibliotheken. Neue Abhängigkeiten: reportlab, pillow (HPND), charset-normalizer (MIT).
Schriften IBM Plex Sans/Mono als TTF aus dem offiziellen IBM-Release (OFL 1.1, `OFL.txt` liegt
bei) in `apps/api/luibui_api/pdf_schriften/`; nichts wird zur Laufzeit geladen.

**Sicherheit:** Jeder Text aus dem Bericht wird für die Absatz-Auszeichnung von ReportLab
escaped. Unsichtbare Zeichen (Steuerzeichen, Nullbreite, Richtungswechsel) und Zeichen ohne
Glyphe erscheinen als `[U+XXXX]`, damit ein Beleg im PDF nichts verstecken kann. Geprüft mit
`<script>`, `</para>`, `<font>`, `&amp;`, U+200B, U+202E, BEL.

**Abweichung von ENTWICKLERREGELN („PDF als Job“):** synchron im Thread-Pool. Gemessen: normaler
Bericht 0,05 s, 510 Befunde im Detail 6 s, weit unter der 30-s-Frist der Weiterleitung. Wird es
bei großen Berichten knapp, auf einen Job umstellen.

**Geprüft:** 5 API-Tests (Escaping, sichtbare Sonderzeichen, feindliche Berichte in beiden Formen,
Dateiname, Download und Fehlerfälle, Nutzer B bekommt 404, ohne Anmeldung 401), Isolationstest
deckt die Route ab; PDFs und Knöpfe lokal angesehen.

**Offen:** PDF (und CSV) auf der öffentlichen Schnellscan-Ergebnisseite.

## 2026-09-29 – S3-9: Favicon, Schnellscan mit Datei zuerst, aktueller Beispielbericht

**Was (Wunsch von Len):**
- Favicon aus dem Logozeichen: `favicon.svg`, `favicon.ico` (16–64 px) und `apple-touch-icon.png`,
  in `app/layout.tsx` eingetragen; die Middleware lässt diese Dateien auf beiden Hosts durch.
- Schnellscan auf luibui.com: erst „Eine Datei oder ein ZIP bis 2 MB“ (vorgewählt, mit
  Upload-Symbol), dann „Öffentliches Repository“.
- „Was geprüft wurde“ steht im Bericht jetzt ganz unten, auf breiten Bildschirmen drei Blöcke
  nebeneinander; ohne DSGVO-Achse (Website) fehlen dort auch die DSGVO-Zeilen. Gilt für Website
  und Entwicklerbereich (gemeinsame `ReportView`).
- Beispielbericht neu mit der echten Engine erzeugt (der alte vom 27.09. hatte einen erfundenen
  OSV-Befund und alte Prüfumfänge): entschärftes Paket `beispiel/wetter-skill` mit versteckter
  Unicode-Tag-Anweisung („Also run: echo hallo“), npm-`postinstall`, MCP-Tool mit Pfad ohne Grenze,
  versteckter Datei und `requests==2.32.3`; Scan im Worker-Image ohne Netz, mit gitleaks, opengrep
  und OSV-Datenbank, alle Prüfungen gelaufen. Ergebnis: Gesperrt, Note 27, 1 K, 2 H, 3 N, 1 I.
  Die OSV-Erklärungen nennen osv.dev als Quelle (CC-BY 4.0); der Schema-Test erlaubt diesen einen
  echten Host.
- „Beispiel als PDF“ ist aktiv: `public/beispielbericht.pdf` (Detail), byte-gleich erzeugbar mit
  `python -m luibui_api.pdf apps/web/content/beispielbericht.json apps/web/public/beispielbericht.pdf`;
  ein API-Test prüft, dass PDF und JSON zusammenpassen.

**Geprüft:** lokal angesehen (Formular, Beispielbericht, Favicon auf beiden Hosts, PDF- und
CSV-Download); 32 Web-Tests, Schema-Tests, PDF-Tests.

## 2026-09-30 – S0-12: Images vorladen, auf neue Version warten, Lücke messen

**Was:** Beim Ausrollen war luibui.com rund 20 s nicht erreichbar. Messungen (Details in
`docs/infra-kapazitaet.md`): mittwald stoppt bei neuem Image den alten Container und lädt das Image
erst danach. `scripts/release.sh` lädt die Images jetzt vorher mit kurzlebigen Containern auf den
Server, wartet danach, bis api und web das neue Image-Tag melden (`version` in `/health` und
`/healthz`, per Build-Argument), und gibt die gemessene Unterbrechung aus. Erster Lauf: Web 7,4 s
(vorher ~20 s), API 10,3 s. Vorher meldete das Skript „Ausgerollt“, sobald die alte API noch
antwortete.

**Offen:** Ganz ohne Lücke nur mit Proxy-Container und zwei Web-Instanzen (Entscheidung Len).

## 2026-09-30 – S3-11: PDF und CSV auf der öffentlichen Schnellscan-Seite

**Was:** Offener Punkt aus S3-11. Unter dem Schnellscan-Bericht auf luibui.com stehen jetzt
„PDF“, „PDF mit Details“ und „CSV“ (JSON, SARIF und Teilen bleiben im Entwicklerbereich).
- API: `GET /api/v1/quickscans/{id}/bericht.pdf` (standard/detail), ohne Anmeldung. Die zufällige
  Scan-ID ist der Schlüssel wie bei der Berichtsseite; dieselbe Prüfung wie dort
  (`_schnellscan`: nur Schnellscans ohne Eigentümer und nicht abgelaufen, sonst 404; nicht fertig
  409). Die PDF-Antwort teilen sich beide Routen (`pdf_antwort` in `routes/scans.py`); „ohne Gewähr“
  steht wie bisher im Kopf jeder Seite.
- Web: Weiterleitung nur für diese eine PDF-Route auf dem öffentlichen Host (`next.config.ts`),
  CSV unter `luibui.com/schnellscan/<id>/bericht.csv` (holt den Bericht ohne Cookie).
  `Bericht` bekommt `downloads="bereich" | "schnellscan"`.
- CSV ohne Befunde: bisher nur die Kopfzeile, damit fehlte auch „ohne Gewähr“ in `scan_art`
  (CLAUDE.md Regel 12). Jetzt eine Zeile mit dem Ergebnis und leeren Befund-Spalten; gilt auch für
  den Entwicklerbereich.

**Geprüft:** 2 neue API-Tests (PDF für jeden mit Link nach echtem Worker-Lauf, 409 vorher, 422 bei
falschem Umfang; Konto-Scans, abgelaufene und unbekannte IDs geben 404, auch angemeldet), der
Isolationstest deckt die neue Route automatisch ab; 4 neue Web-Tests (Knöpfe je Bereich, CSV ohne
Befunde). Lokal mit API, Worker und `next start`: PDF, PDF mit Details und CSV über den Host
luibui.com geladen, unbekannte ID 404, CSV-Route auf app.luibui.com 404, Seite angesehen.
Python 1237 Tests grün; `test_timeout_kills_the_whole_process_group` scheitert in der
Cloud-Sitzung auch ohne diese Änderung (Umgebung, als root), ruff/mypy/eslint/tsc sauber.

**Offen:** Ausrollen mit `scripts/release.sh` (Len, Docker Desktop).

## 2026-09-30 — S3-1 (gutartige Seite) und S3-2: Benchmark

**Was:** `python -m luibui_scan.benchmark` misst Erkennung und Fehlalarme und schreibt
`docs/benchmark.md`. `scripts/benchmark.sh` führt das im Worker-Image aus, weil nur dort alle
Scanner installiert sind; Engine und Regeln kommen aus dem Arbeitsbaum. Die OSV-Datenbank liegt im
Docker-Volume `luibui-benchmark-osv` und wird höchstens täglich mit dem Code des Workers erneuert.

- **Erkennung:** die 36 entschärften Nachbildungen aus `corpus/generate.py` (je Matrix-Zeile eine).
  Erkannt = erwartete Regel hat angeschlagen *und* die Gesamtampel ist nicht grün.
- **Fehlalarme:** ein gutartiges Paket mit mindestens einem K- oder H-Befund. `osv:`-Befunde zählen
  gesondert (eine bekannte Lücke in einer festgelegten Version ist ein Fakt). Nach Prüfung lässt
  sich eine Regel je Paket in `vergleich.json` unter `berechtigt` (mit Grund) ausnehmen; sie bleibt
  in der Tabelle sichtbar.
- **60 echte Pakete** (`corpus/vergleich.json`): 11 Skills aus `anthropics/skills`, 13 Plugins aus
  `anthropics/claude-plugins-official`, 10 Skills aus `obra/superpowers`, 8 Beispiele aus
  `modelcontextprotocol/python-sdk`, 7 Server aus `modelcontextprotocol/servers`,
  `microsoft/playwright-mcp`, 10 Server aus `awslabs/mcp`. Alle MIT oder Apache-2.0; sie werden beim
  Lauf geholt, nie ins Repo kopiert. Das Worker-Image hat kein git, deshalb holt `--holen` sie
  vorher auf dem Mac, über `safe_git` mit größeren Grenzen nur für diese feste Liste (60.000
  Dateien, 1 GB). Stand = jeweils aktueller Standardzweig, der Commit steht in der Tabelle.

**Erster Lauf** (Engine `f2da04b`, 12:45 min):
- Erkennung 36/36, Code-Ebene 4/4. Aussagekraft gering: eine Datei je Prüfung, vom selben Team wie
  die Regeln. Steht so auch in `docs/benchmark.md`.
- Fehlalarme eigener Korpus 0/34.
- **Fehlalarme echte Pakete 21/60 (35 %), Ziel ≤ 5 %.** Häufigste Ursachen, Stoff für S3-6:
  - `LB-E04-ohne-anmeldung` (H) bei 7 lokalen Beispielservern aus python-sdk und servers.
  - `LB-A02-claude-hooks` (H) bei 4 offiziellen Plugins, deren Hooks der eigentliche Zweck sind.
  - `LB-C04`/`LB-C07` (K) in Testdateien von awslabs (`tests/…/test_path_validation.py`), die
    genau diese Pfade als Negativbeispiele prüfen; `LB-C12` (K) dreimal in dynamodb.
  - `LB-B09-geheimhaltung` (K) in `pr-review-toolkit/agents/silent-failure-hunter.md`,
    `LB-B05`, `LB-B14`, `ATR-2026-02106` in Doku und Hook-Code.
  - `LB-E09-fremdes-paket` bei mitgelieferten `.mcp.json` mit `npx`/`uvx`.
  - `bandit:B602` (K) in `webapp-testing/scripts/with_server.py`, `LB-C01` in Tests von
    playwright-mcp und in `superpowers/brainstorming`, `LB-D03` in playwright-mcp.
- Fast alle übrigen echten Pakete sind gelb; die M-Befunde dahinter sind noch nicht ausgewertet.
- A08 (Schadsoftware-Hashliste) lief nicht, die Datenbank ist im Benchmark nicht geladen
  (Lizenzfrage MalwareBazaar offen).

**Offen:**
- Bösartige Seite von S3-1: 60 vollständige Pakete statt 36 Einzeldateien. Ein Versuch, sie hier
  auszuformulieren, wurde vom Sicherheitsfilter des Assistenten abgebrochen; das braucht einen
  anderen Weg (Len).
- S3-6: die Fehlalarme oben einzeln bewerten, Regeln anpassen oder begründet in `berechtigt`
  aufnehmen. Keine Schwelle senken, nur weil Rot schlecht aussieht (E3).
- „Läuft in CI": das Skript ist bereit, die CI startet derzeit nicht (GitHub-Abrechnung).

## 2026-09-30 — S3-6: erste Kalibrierung mit dem Benchmark

**Ausgang:** 21 von 60 echten Paketen mit K/H. Jede Ursache am Quelltext nachvollzogen
(Repos lokal über `--holen`), dann behoben. Begründungen stehen im Prüfkatalog §14.

**Regelfehler (je mit Negativtest aus dem echten Fall):**
- D03 verglich bei scoped npm-Paketen nur den Teil nach `/` (`@playwright/test` ≈ `jest`).
- B09 und B14 griffen bei beschreibenden Sätzen („… without user awareness is hiding problems“,
  „skip security group deletion“, „bypassPermissions is unnecessary“). Optionstabellen
  (`| --no-sandbox | … |`) gelten als zitiert (M).
- B05 meldete HTML-Kommentare in Code-Blöcken.
- ATR-Regeln liefen über Code-Kommentare und trafen Regex-Literale; dort gelten nur eigene Regeln.
- C12 zählte `Path(x)` als Dateizugriff, auch vor `.resolve()`/`.exists()`; jetzt nur echte
  Dateioperationen. `os.path.join(ordner, FESTER_NAME)` gilt als begrenzt. Opengrep-Regeltests
  im Worker-Image: 43/43.

**Entscheidungen Len (per Rückfrage):** C/E-Befunde in Testdateien höchstens M; Plugin-Hooks, die
nur eigene Skripte starten, M statt H, und `hooks.json` wird Quelle der Korrelation (das Skript
steigt eine Stufe, auch in Marketplace-Unterordnern über `${CLAUDE_PLUGIN_ROOT}`); E04 bei
Bindung nur an 127.0.0.1/localhost M statt H.

**Bewusst nicht geändert:** Bandit bleibt für Python die einzige C01-Quelle und wird nicht
gedeckelt. Fünf zutreffende Befunde an gutartigen Paketen stehen mit Grund unter `berechtigt` in
`corpus/vergleich.json` (webapp-testing `shell=True` für Serverbefehle, brainstorming `exec` mit
Nutzer-Umgebungsvariable, `everything` ohne Anmeldung auf allen Schnittstellen, zweimal
ungepinntes `uvx …@latest`). **Len bitte gegenlesen.** Der Benchmark zeigt jetzt beide Quoten.

**Ergebnis:** Fehlalarme echte Pakete 0/60, ohne Ausnahmen 5/60 (8 %); Erkennung unverändert
36/36; eigener Korpus 0/34. 1018 Engine-Tests grün. Viele echte Pakete bleiben rot, aber nur
wegen bekannter Lücken aus OSV (gesondert gezählt).

**Offen:** Die Erkennungsquote ist mit 36 Einzeldateien wenig aussagekräftig (S3-1 bösartige
Seite). Nicht ausgerollt: die Änderungen betreffen die Engine in Produktion, Ausrollen auf Lens Wort.

## 2026-10-01 – S3-10: Backup mit Restore-Test und Health-Alarm (Container `ops`)

**Ausgang:** Es gab kein eigenes Datenbank-Backup. mittwald sichert das Projekt jede Nacht um
01:39 (30 Tage, laut mittwald inklusive Volumes), aber eine Dateikopie einer laufenden PostgreSQL
ist nicht verlässlich, und niemand merkte, wenn etwas ausfällt. mittwald-Cronjobs brauchen eine
App-Installation, luibui hat keine.

**Entscheidungen Len (per Rückfrage, 01.10.):** eigener Container statt im Worker (der verarbeitet
feindliche Uploads); Verschlüsselung mit Schlüsselpaar, der private Schlüssel bleibt bei Len;
Alarm an Lens Adresse (als `ALARM_AN` im Stack, nicht im Repo; die Mails enthalten nur Status).

**Was:** neuer Dienst `apps/ops` (Image auf `postgres:17-trixie` mit pg_dump 17, Python, psycopg
und age aus Debian; keine weiteren Abhängigkeiten), 256 MB.
- 01:05 Berlin: Lese-Transaktion exportiert ihren Snapshot und zählt die Zeilen jeder Tabelle,
  `pg_dump --snapshot` sichert genau diesen Stand, Restore in `luibui_restore_test`, Zeilenzahlen
  müssen gleich sein, dann `age` an den öffentlichen Schlüssel, 14 Dateien in `luibui-backup`.
  Klartext nur in `/tmp` mit umask 077, im `finally` gelöscht.
- Alle 5 Minuten api, web (intern) und luibui.com: Alarm nach zwei Fehlschlägen, Entwarnung danach.
  Alarm auch bei fehlgeschlagenem Backup und wenn das letzte gute Backup älter als 26 h ist.
- Stack, `docker-compose.yml`, `release.sh` (baut, pusht und lädt `ops` vor; übernimmt
  `BACKUP_AGE_RECIPIENT`/`ALARM_AN` aus `~/.config/luibui/ops.env` oder dem laufenden Stack),
  CLAUDE.md (Repo-Struktur, mypy), `docs/restore.md` (Einrichten, Wiederherstellen, Restore-Tests),
  Bedrohungsmodell T38, Kapazität (Summe 3.456 MB).

**Geprüft:** 16 Tests (Einstellungen, nur echte age-Schlüssel, Alarm-Logik, Zeitplan mit
Sommer-/Winterzeit, Aufbewahrung; gegen PostgreSQL: Backup mit echtem age und Entschlüsseln,
abweichender Restore ergibt kein Backup, fehlgeschlagener Dump nennt den Schritt, Testdatenbank
immer entfernt). Ende-zu-Ende mit dem Image gegen PostgreSQL 17: Backup, Entschlüsseln mit dem
privaten Testschlüssel, Einspielen in eine frische Datenbank (alle Zeilen da), falscher Schlüssel
scheitert, kein Klartext in der Datei. Laufender Container: plant 01:05 Berlin, Alarm nach zwei
Fehlschlägen, sauberes Stoppen. Python 1290 Tests grün, ruff, mypy.

**Offen (Len):**
1. `age-keygen -o luibui-backup.key`, privaten Schlüssel sichern, öffentlichen Schlüssel und
   `ALARM_AN` in `~/.config/luibui/ops.env` (Anleitung in `docs/restore.md`).
2. `scripts/release.sh` ausrollen; danach RAM von `ops` hier und in `docs/infra-kapazitaet.md`.
3. Nach der ersten Nacht ein echtes Backup holen und lokal einspielen, in `docs/restore.md` eintragen.
4. `MASTER_KEY` und `POSTGRES_PASSWORD` zusätzlich außerhalb von mittwald sichern.

**Grenze:** `ops` läuft auf demselben Server; fällt der ganze Server aus, kommt keine Mail. Ein
externer Prüfer (nicht US) wäre der nächste Schritt.

## 2026-10-01 – S3-7: Befund-Status und Moderation von Einsprüchen

**Ausgang:** Tabelle `finding_status` (Projekt + Fingerprint) gab es seit S0-8, und die Übersicht
blendete erledigte Befunde schon aus. Es fehlte alles, womit man einen Status setzt.

**Entscheidungen Len (per Rückfrage, 01.10.):** Status ändert **weder Ampel noch Note**, er ist
nur Anzeige und zählt für „offene Befunde“. Erst „Fehlalarm, Regel angepasst“ wirkt, über die
geänderte Regel bei der nächsten Prüfung. Die Moderation sieht den Befund mit maskiertem Beleg,
jedes Öffnen wird protokolliert.

**Was:**
- Migration `0005`: `moderation` (`bestritten` = „vom Autor bestritten“, `fehlalarm` = „Fehlalarm,
  Regel angepasst“, Konzept §6), Notiz, wer, wann; Teilindex auf offene Einsprüche.
- API `routes/befunde.py`: `POST /api/v1/scans/{id}/befund-status` (offen, akzeptiert und
  bestritten nur mit Begründung, nur Befunde dieses Berichts, nur in Projekten, nicht wenn schon
  behoben). Der Scan wird als Dependency geladen, damit fremde Scans vor der Body-Prüfung 404
  liefern. `GET /api/v1/scans/{id}` liefert `befund_status` je Fingerprint. Neuer Status des
  Eigentümers setzt eine Moderationsentscheidung zurück.
- Moderation: `GET /api/v1/moderation/einsprueche[?entschieden=true]` (ohne Beleg),
  `GET …/{id}` (mit Beleg, Audit `moderation.angesehen`), `POST …/{id}/entscheidung` (Audit
  `moderation.entschieden`, `updated_at` = Einreichung bleibt). Nur `is_admin` mit Browser-Sitzung,
  sonst 404. `GET /auth/ich` meldet `moderation`.
- Worker `update_finding_status` nach jedem Bericht: was zurückkommt, ist wieder offen; was aus
  der vorigen Prüfung fehlt, ist behoben, aber nur bei gleichem Prüfumfang (eine Dateiauswahl sagt
  nichts über die übrigen Dateien) und nur, wenn keine neuere Prüfung schon fertig ist.
- Oberfläche: Status-Marke im Kopf jedes Befunds, Steuerung im aufgeklappten Befund
  (Akzeptieren …, Fehlalarm melden …, Wieder öffnen), Zähler „davon akzeptiert, bestritten oder
  behoben“; `/moderation` und `/moderation/<id>` mit Menüeintrag nur für Moderatoren. Begründungen
  und Notizen als Text. Datenexport enthält die Moderationsfelder. Bedrohungsmodell T36 ergänzt.

**Geprüft:** 8 API-Tests (inkl. Ampel/Note unverändert, Nutzer B, Token-Zugang zur Moderation
abgewiesen, nur bestrittene Befunde sichtbar, Audit ohne Begründungstext), 4 Worker-Tests
(behoben/wieder offen, engerer Umfang, verspätete ältere Prüfung, ohne Projekt), Isolationstest
deckt die neuen Routen ab, 4 Komponententests (Escaping der Begründung). Der bestehende
Formular-Test fand ein fehlendes `method="post"`. Python 1303 grün, ruff, mypy, Web 40 grün,
Lint, Build. **Nicht im Browser angesehen.**

**Ausgerollt** am 01.10., 21:43, zusammen mit S3-10 (`f0ed830`, Migration `0005` gelaufen, Backup-
Schlüssel und `ALARM_AN` gesetzt, ohne messbare Unterbrechung).

**Offen:**
1. Moderator einrichten (Len): `UPDATE users SET is_admin = true WHERE email = '…';` in der
   Produktionsdatenbank. Es gibt bewusst keine Oberfläche dafür.
2. Mail an den Autor bei einer Entscheidung: Sprint 5 (Benachrichtigungen, Konzept §4).
3. PDF/CSV/SARIF tragen den Status noch nicht.

## 2026-10-02 – S3-5: Verlauf und Vergleich zweier Prüfungen

**Was:**
- API `routes/verlauf.py`: `GET /api/v1/projects/{id}/verlauf` (die letzten 100 fertigen
  Prüfungen, älteste zuerst, Note, Ampel, Umfang, Befunde je Schwere; gezählt in PostgreSQL über
  `report->'befunde'`, ohne die Berichte zu laden) und `GET /api/v1/projects/{id}/vergleich`
  (ohne Angaben: letzte gegen vorige; mit `von`/`bis` zwei beliebige fertige Prüfungen des Projekts,
  immer älter → neuer). Neu, behoben, unverändert nach Fingerprint; `gleicher_umfang` warnt, wenn
  eine Dateiauswahl gegen das ganze Paket steht. Fremde Projekte, fremde oder unfertige Prüfungen 404.
- Projektseite: Abschnitt „Verlauf“ mit Notenlinie und gestapelten Balken je Schwere, eine
  gemeinsame Hover-/Fokus-Anzeige für beide, Tabelle als Alternative; ab der zweiten Prüfung. Je
  Prüfung ein Knopf „Vergleichen“ mit der davor, oben „Letzte Prüfung mit der vorigen vergleichen“.
- Vergleichsseite `/projekte/<id>/vergleich`: beide Prüfungen mit Ampel und Note, Notenänderung,
  Listen „Neu“, „Behoben“, „Unverändert“ (eingeklappt). Titel und Pfade als Text.
- Farben der Schweregrade im Diagramm: eine rote Tonleiter (kritisch dunkel → niedrig/info hell),
  mit dem Dataviz-Prüfskript als ordinale Reihe geprüft (monoton, Abstände, Kontrast 2,38:1 am
  hellen Ende, ein Farbton). Keine zweite Y-Achse: Note und Befunde sind zwei Diagramme.

**Fehler gefunden und behoben (live seit 01.10.):** Server-Seiten importierten `SCHWERE_STIL` aus
einer Client-Komponente und bekamen statt der Tabelle eine Client-Referenz; die Schwere-Abzeichen
auf `/moderation` und `/moderation/<id>` hatten deshalb keine Farbe. `SCHWERE_STIL` liegt jetzt in
`lib/schwere.ts`; ein neuer Test (`lib/client-grenze.test.ts`) verbietet Konstanten-Importe aus
`"use client"`-Modulen in Server-Komponenten und schlägt mit dem alten Stand an.

**Geprüft:** 4 API-Tests (Zählung je Schwere, leeres Projekt, neu/behoben/unverändert in beiden
Reihenfolgen, nur eigenes Projekt, unfertig, Nutzer B), Isolationstest; 3 Web-Tests. Lokal mit
API, Worker und Website: drei echte Prüfungen eines Projekts, Verlauf mit Hover angesehen,
Vergleich (Note +40, 1 behoben), Abzeichenfarbe im Browser gemessen. Python 1306, Web 43 Tests
grün, ruff, mypy, eslint.

## 2026-10-02 – S3-7: Befund-Status in PDF, CSV, JSON und SARIF

**Was:** Offener Punkt aus S3-7. Downloads aus dem Entwicklerbereich tragen jetzt den Status, den
der Eigentümer oder die Moderation gesetzt hat, mit denselben Wörtern wie die Oberfläche
(„Akzeptiert“, „Bestritten“, „Behoben“, „Fehlalarm, Regel angepasst“, „Vom Autor bestritten“).
- **PDF:** Zeile „Status: …“ unter dem Befund (Standard) bzw. mit Begründung (Detail), dazu ein
  Satz, dass der Status weder Ampel noch Note ändert. Begründung escaped wie jeder andere Text.
- **CSV:** zwei neue Spalten `status` und `status_begruendung`, Schutz gegen Formeln wie bei
  allen Zellen (auch im öffentlichen Beispiel, dort leer).
- **JSON:** `befund_status` je Fingerprint.
- **SARIF:** `suppressions` nach §3.35: akzeptiert oder bestätigter Fehlalarm = `accepted`,
  bestritten ohne Entscheidung = `underReview`, vom Autor bestritten = `rejected`; „behoben“ ohne
  Unterdrückung. GitHub Code Scanning blendet `accepted` aus.
- Schnellscan und geteilte Berichte bekommen nie einen Status.

**Geprüft:** 2 PDF-Tests (Beschriftung, Escaping der Begründung, beide Formen, Download mit
Status), 3 Export-Tests (CSV mit Formel in der Begründung, JSON, alle SARIF-Fälle, ohne Status
unverändert). Python 1308, Web 46 Tests grün, ruff, mypy, eslint.

## 2026-10-02 – S3-12: GGUF-Modelle und eingebettete Chat-Vorlagen (Matrix MOD-04)

**Was:** GGUF-Dateien (erkannt an `GGUF` am Dateianfang oder an der Endung) werden bis zum Ende der
Metadaten gelesen, Wert für Wert, nie die Gewichte: höchstens 64 MB Metadaten, 100.000 Einträge,
16 MB je Text, 10 Mio. Elemente je Feld, keine verschachtelten Felder, GGUF-Version 1 bis 3 (v1 mit
32-Bit-Längen). Gefunden werden `tokenizer.chat_template` und benannte Varianten
(`tokenizer.chat_template.tool_use` usw.); sie laufen durch dieselbe SSTI-Prüfung wie die Vorlage in
`tokenizer_config.json` (gemeinsame Funktion `_template_befund`).
- **A16 (K, sperrt):** Vorlage greift auf Python-Interna zu (`__class__`, `cycler`, `lipsum` …).
- **A18 (M):** Kopf nicht lesbar (falsche Kennung, unbekannte Version, Datei endet mitten in den
  Metadaten, Grenze überschritten, unbekannter Werttyp); der Grund steht in der Erklärung.
- Korpus: `MOD-04` bösartig (Vorlage mit `''.__class__`, gibt nur „echo hallo“ aus) und gutartig
  (übliche Vorlage). Prüfkatalog A16/A18 ergänzt.

**Geprüft:** 11 neue Engine-Tests (Vokabular mit 2.000 Einträgen und alle festen Werttypen werden
übersprungen, SSTI in Haupt- und benannter Vorlage, Erkennung am Inhalt bei `weights.bin`, Version 1,
sechs unlesbare Varianten, Grenze für die Metadaten), Korpus-Matrix. Python 1321 Tests grün, ruff, mypy.

**Offen:** Benchmark (`scripts/benchmark.sh`) neu laufen lassen, damit `docs/benchmark.md` die neue
Zeile MOD-04 zeigt (braucht das Worker-Image, Len).
