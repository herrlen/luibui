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
