# Infrastruktur und Kapazität

Fortgeschrieben nach jedem Deploy (CLAUDE.md, Abschnitt Infrastruktur).

## Aktueller Stand auf mittwald

| | |
|---|---|
| Projekt | `p-yw5cv5` (luibui), Server `s-r0ud3w`, geteilt mit weiteren Projekten |
| Stack | `default` (`b8d0a6a8-83ef-4aba-b785-0b450c0ac551`), Definition in `infra/mittwald-stack.yml` |
| Images | `ghcr.io/herrlen/luibui/{api,worker,web}:sha-<commit>`, Registry-Zugang `herrlen` (nur `read:packages`, **läuft am 2026-10-26 ab**) |
| Postgres-Passwort | nur in der Stack-Konfiguration bei mittwald, keine lokale Kopie |

| Container | ID | Limit RAM | Limit CPU | Port |
|---|---|---|---|---|
| postgres | `c-s7jsux` | 768m | – | 5432 (nur im Projekt) |
| api | `c-due8b4` | 512m | – | 8000 |
| worker | `c-w7jjv1` | 1536m | 1.5 | – |
| web | `c-k9k9jp` | 384m | – | 3000 |
| **Summe** | | **3200m** | | |

| Host | Ziel |
|---|---|
| `luibui.com` | web:3000 |
| `app.luibui.com` | web:3000 (Host-Routing ab Sprint 2) |
| `api.luibui.com` | api:8000 |
| `www.luibui.com`, `luibui.de`, `www.luibui.de` | 301 → `https://luibui.com/` |
| `p-yw5cv5.project.space` | unverändert (default) |

TLS: Let's Encrypt über mittwald, automatisch.

## Deploys

### 2026-09-26, 20:55 — erster Deploy (S0-12), `ec78e49`

**Geprüft von außen:**
- `https://api.luibui.com/health` → 200, `{"status":"ok","database":"ok"}`
- `https://luibui.com/` und `https://app.luibui.com/` → 200, `/healthz` → 200
- `/docs` und `/openapi.json` der API → 404 (in Produktion abgeschaltet)
- `luibui.de`, `www.luibui.de`, `www.luibui.com` → **301** auf `https://luibui.com/`
- Zertifikat `api.luibui.com`: Let's Encrypt, gültig bis 2026-12-25

**Logs:** API: Migration gelaufen, Uvicorn läuft. Worker: startete einige Male neu, bis Postgres
bereit war (mittwald kennt kein `depends_on`), danach `worker … ready`.

**RAM-Verbrauch auf dem Server** (cgroup `memory.current` / `memory.peak`, gemessen 2026-09-26,
21:20, leerer Stack, keine Prüfung aktiv):

| Container | aktuell | Spitze seit Start | Limit (wirksam) |
|---|---|---|---|
| postgres | 52 MiB | 98 MiB | 732 MiB |
| api | 75 MiB | 75 MiB | 488 MiB |
| worker | 52 MiB | 62 MiB | 1464 MiB |
| web | 87 MiB | 87 MiB | 366 MiB |
| **Summe** | **266 MiB** | | **3050 MiB** |

**Nach dem Ausrollen von `ca71338` (2026-09-27, 07:22, Annahme geschlossen, keine Prüfung aktiv):**
api 72 MiB, worker 60 MiB, web 136 MiB, postgres 55 MiB, zusammen 323 MiB. Das Web wächst mit der
Next.js-Laufzeit, die API trotz Anmeldung und Verschlüsselung nicht. Migration `0002` ist auf dem
Server gelaufen (`alembic_version` = 0002). Die API sieht als Client nur Ingress-Adressen aus
`100.121.0.0/16`; ohne `X-Forwarded-For` greift keine Begrenzung je IP.

**Nach dem Ausrollen von `02d85be` (2026-09-27, 10:35, Analyzer, gitleaks, osv-scanner, Netz-Isolation,
Annahme geschlossen):** api 81 MiB (Spitze 132), worker 315 MiB (Spitze 469, nach OSV-Download von 255 MB
und einem Testscan), web 121 MiB, postgres 54 MiB (Spitze 98). Der Worker lädt die OSV-Datenbank beim Start
in 13 s nach `/rules/osv`. **Im Produktions-Worker geprüft:** Der Kindprozess sieht nur `lo`; ein
entschärftes Testpaket (Unicode-Tags, Test-Token, `pillow 10.0.0`) wird ohne Netz vollständig geprüft
und gesperrt, der Scratch ist danach leer.

mittwald liest `768m` als 768 **Megabyte** (10⁶), nicht Mebibyte; die wirksamen Limits sind
deshalb rund 5 % kleiner als lokal. Aussagekräftig wird die Messung erst mit echten Prüfungen und
Scannern (S1-12).

Gemessen per `mw container exec` mit dem SSH-Schlüssel `luibui-betrieb-20260926`
(`~/.ssh/luibui_mittwald_ed25519`, läuft 2027-09-26 ab):

```sh
MITTWALD_SSH_IDENTITY_FILE=~/.ssh/luibui_mittwald_ed25519 \
  mw container exec <container> -p p-yw5cv5 'cat /sys/fs/cgroup/memory.current'
```

## Unterschiede zur lokalen Umgebung

mittwald übernimmt aus einer Compose-Datei nur `image`, `command`, `entrypoint`, `environment`,
`ports`, `volumes`, `restartPolicy` und `deploy.resources.limits` (geprüft im Quellcode von `mw`
und im API-Schema `ContainerServiceDeclareRequest`). Was `infra/docker-compose.yml` lokal
zusätzlich erzwingt, fehlt auf dem Server:

| Lokal | mittwald | Folge |
|---|---|---|
| Worker nur im internen Netz, kein Internet | alle Container im Projekt erreichen sich, Worker-Elternprozess hat Internet | **gelöst seit 2026-09-27:** Der prüfende Kindprozess läuft in eigenem Netz-Namensraum (`LUIBUI_NETZ_ISOLIEREN=1`), geprüft auf dem Server |
| `read_only`, `cap_drop: ALL`, `no-new-privileges` | nicht verfügbar | Container laufen weiter als Nicht-Root (`USER` im Image) |
| `depends_on` mit Healthcheck | nicht verfügbar | API und Worker starten neu, bis Postgres bereit ist |
| `tmpfs`, `pids_limit`, `stop_grace_period` | nicht verfügbar | – |
| `:ro` bei Volumes | Format nur `<volume>:<mountpoint>` | `luibui-rules` ist im Worker beschreibbar |

**Per SSH geprüft (21:20):** Der Worker läuft als Nutzer 10001 und darf auf `/scratch` schreiben
(mittwald übernimmt den Eigentümer aus dem Image, setzt aber Modus 755 statt 700). **Der Worker
erreicht das Internet** (Verbindung zu 1.1.1.1:443 gelingt), lokal nicht.

## Ausrollen

```sh
# vom Repository-Wurzelverzeichnis, MITTWALD_API_TOKEN gesetzt
E=$(mktemp) && chmod 600 "$E"
printf 'POSTGRES_PASSWORD=%s\nMASTER_KEY=%s\nIMAGE_TAG=sha-%s\n' \
  "<Passwort aus der Stack-Konfiguration>" "<MASTER_KEY aus der Stack-Konfiguration>" "<commit>" > "$E"
mw stack deploy -s b8d0a6a8-83ef-4aba-b785-0b450c0ac551 -c infra/mittwald-stack.yml --env-file "$E"
rm -f "$E"
```

⚠ `mw stack deploy` ersetzt die gesamte Stack-Definition. Das Postgres-Passwort muss dasselbe
bleiben, sonst kommt die API nicht mehr an die bestehende Datenbank. Es steht in der
Stack-Konfiguration, nirgends sonst. `mw container get` gibt es nicht (CLI 1.21); die Werte stehen in
`mw stack list -p p-yw5cv5 -o json` unter `.[0].services[].deployedState.envs`. **Nie anzeigen**,
sondern direkt per `jq` in die Env-Datei schreiben:

```sh
E=$(mktemp) && chmod 600 "$E"
{
  S=$(mw stack list -p p-yw5cv5 -o json)
  printf 'POSTGRES_PASSWORD=%s\n' "$(echo "$S" | jq -r '.[0].services[] | select(.serviceName=="postgres") | .deployedState.envs.POSTGRES_PASSWORD')"
  printf 'MASTER_KEY=%s\n' "$(echo "$S" | jq -r '.[0].services[] | select(.serviceName=="api") | .deployedState.envs.MASTER_KEY')"
  printf 'IMAGE_TAG=sha-%s\n' "$(git rev-parse HEAD)"
} > "$E"
awk -F= '{ print $1 " (" length(substr($0, index($0,"=")+1)) " Zeichen)" }' "$E"   # nur Längen
mw stack deploy -s b8d0a6a8-83ef-4aba-b785-0b450c0ac551 -c infra/mittwald-stack.yml --env-file "$E"
rm -f "$E"
```

`MASTER_KEY` wurde am 2026-09-27 beim ersten Ausrollen erzeugt und steht seitdem nur in der
Stack-Konfiguration des API-Containers.

⚠ Dasselbe gilt ab S2-7 für `MASTER_KEY` (API-Container): Er verschlüsselt die Schlüssel aller
Projekt-Dateien. Wird er beim Ausrollen weggelassen oder ersetzt, sind alle gespeicherten Dateien
unlesbar. Beim ersten Ausrollen mit `openssl rand -base64 32` erzeugen, danach immer aus der
Stack-Konfiguration übernehmen. **Zusätzlich an einem zweiten Ort sichern (Len):** Ohne ihn hilft
auch ein Datenbank-Backup nicht.

## S1-12 Kapazitätsmessung (2026-09-27)

Gemessen im Produktions-Worker (`c-w7jjv1`, Stand `16e47c6`) wie ein echter Job: sichere Annahme,
Kindprozess mit Netz-Isolation, alle Analyzer aus Sprint 1, OSV-Datenbank vorhanden, Scan-Art
„intensiv“. Limits des Containers: 1,5 CPU (2 Kerne sichtbar), 1.464 MiB RAM.

| Paket | Dateien | Größe | Dauer | CPU | größter Prozess | cgroup-Spitze |
|---|---|---|---|---|---|---|
| klein: eine `SKILL.md` | 1 | 1 KB | 3,8 s | 2,5 s | 57 MB | 239 MB |
| mittel: `anthropics/skills` | 419 | 10,5 MB | 20,1 s | 19,5 s | 144 MB | 360 MB |
| groß: `modelcontextprotocol/python-sdk` | 1.676 | 14,4 MB | 52,1 s | 50,9 s | 147 MB | 383 MB |

**Befund:**
- **Arbeitsspeicher ist unkritisch.** Die Spitze des ganzen Containers (inklusive Seiten-Cache und
  Elternprozess) liegt bei rund einem Viertel des Limits. Der größte einzelne Prozess braucht unter
  150 MB.
- **Die Prüfung ist CPU-gebunden** (Dauer ≈ CPU-Zeit). Lokal gemessen verbraucht **`b_muster` rund 85 %**
  der Zeit: 168 Regex-Regeln über alle Anweisungstexte (beim großen Repo 811 Dateien, 6,5 MB). Die
  Kosten verteilen sich breit; die zehn teuersten Regeln machen 28 % aus.
- **Durchsatz:** eine Prüfung gleichzeitig (Konzept §8), also etwa 180 mittelgroße oder 70 große
  Pakete pro Stunde.
- **Schnellscan** (Ziel < 30 s, Limit 60 s): typische Skill-Pakete liegen deutlich darunter. Ein sehr
  großes Repo wie `python-sdk` kommt mit 52 s nah an das Limit.

**Empfehlung zur Server-Frage (DoD Sprint 1):** **Für Sprint 1–3 und die Beta genügt der heutige
mittwald-Container, kein vServer.** Ein eigener Server wird nötig:
- für ClamAV (Sprint 4, rund 1,2 GB RAM zusätzlich), spätestens aber
- für die Sandbox (Sprint 6, eigener Server laut CLAUDE.md Regel 1).

Vorher lohnt die Optimierung von `b_muster` (Parallelisierung auf die verfügbaren Kerne, bringt höchstens
Faktor 1,5; Vorfilter je Regel) im Benchmark S3-6. Die endgültige Entscheidung trifft Len.

## Nach Deploy `f9d4f64` (27.09.2026, Scanner-Matrix Teil B und neues Design)

Leerlauf direkt nach dem Start (cgroup `memory.current`): api 75 MiB, worker 57 MiB, web 147 MiB.
Keine neuen Werkzeuge im Worker; die neuen Prüfungen sind Python-Code im selben Prozess. Eine
Messung unter Last folgt mit dem nächsten echten Intensivscan (Annahme ist noch zu).

## Nach Deploy `22744ec` (27.09.2026, Schadsoftware-Liste und Beispielbericht)

Nach dem Start mit geladener MalwareBazaar-Liste (1.144.645 Hashes, 36,6 MB auf `luibui-rules`):
api 77 MiB, worker 122 MiB, web 119 MiB.

## Nach Deploy `a438e87` (28.09.2026, macOS-Metadaten, ATR-Kalibrierung, Berichts-Downloads)

Kurz nach dem Start, cgroup `memory.current`: api 80 MiB, worker 54 MiB, web 113 MiB. Logs ohne
Fehler. Der Worker liegt unter dem Wert vom 27.09. (122 MiB), vermutlich weil er seit dem Start keine
Prüfung mit geladener Schadsoftware-Liste gelaufen hat.

## Nach Deploy `f9028be` (28.09.2026, Schrift für Logo und Überschriften)

Nur `web` neu gestartet (api und worker unverändert seit `a438e87`). cgroup `memory.current`:
api 86 MiB, worker 61 MiB, web 44 MiB. Logs ohne Fehler.

## Nach Deploy `823315f` (28.09.2026, Bestätigungslink beim Prüfen)

cgroup `memory.current`: api 76 MiB, worker 49 MiB, web 106 MiB. Logs ohne Fehler.

## Nach Deploy `b0d0f06` (28.09.2026, S2-1 Code-Analyse mit Opengrep und Bandit)

cgroup nach einem Selbsttest im Worker (Mini-Paket mit Köder, alle 10 Prüfungen, keine
fehlgeschlagen): api 69 MiB (Spitze 122), worker 96 MiB (Spitze 358), web 75 MiB. Im lokalen
Container-Test mit dem marketing-skill-Paket (234 Dateien, 63 Python) lag die Spitze bei 375 MiB,
Dauer 47 s bei 1,5 CPU. Opengrep läuft mit `--jobs 1` und `--max-memory 900`; das Worker-Limit
von 1536 MiB reicht. Das Image ist um den Opengrep-Cache größer (ca. 290 MB).

## Nach Deploy `3ab909e` (29.09.2026, S2-3 MCP-Analyzer)

cgroup nach einem Selbsttest im Worker (vergiftetes MCP-Tool, alle Prüfungen, keine
fehlgeschlagen): api 79 MiB (Spitze 133), worker 450 MiB (Spitze 656), web 156 MiB (Spitze 169).
Der höhere Worker-Wert ist überwiegend Seiten-Cache (`memory.current` zählt gelesene Dateien mit:
Opengrep-Cache 240 MB, Schadsoftware-Liste), der bei Bedarf freigegeben wird; der Python-Prozess
selbst lag beim Test vom 28.09. bei rund 270 MB. Im Web-Log stehen Zeilen „Server Reference ID did
not match the expected format“: abgewiesene Anfragen mit ungültigem `Next-Action`-Header
(automatisierte Proben), kein Fehler der Anwendung.

## Nach Deploy `6211216` (29.09.2026, S2-4 DSGVO-Analyzer)

Logs ohne Fehler. cgroup nach einem Selbsttest (harmloses Paket mit Manifest, erstmals Grün/Grün,
Note 100): api 69 MiB (Spitze 121), worker 88 MiB (Spitze 673, überwiegend Seiten-Cache), web
84 MiB (Spitze 169).

## Nach Deploy `1188de2` (29.09.2026, Erweiterungen B/C/E/G)

Logs ohne Fehler. cgroup nach einem Selbsttest (PowerShell, Go, .env, Code-Kommentar): api 73 MiB (Spitze 125); worker 460 MiB (Spitze 671); web 90 MiB (Spitze 169).

## Nach Deploy `ffd5852` (29.09.2026, Kalibrierung B08/B09/B14)

Logs ohne Fehler. cgroup: api 101 MiB (Spitze 125); worker 69 MiB (Spitze 69); web 88 MiB (Spitze 169).

## Nach Deploy `20571bb` (29.09.2026, S2-5 Korrelation)

Logs ohne Fehler. cgroup nach Selbsttest: api 78 MiB (Spitze 130); worker 455 MiB (Spitze 651); web 73 MiB (Spitze 74).

## Nach Deploy `e04d68f` (29.09.2026, DoD Sprint 2, Maskierung)

Logs ohne Fehler. cgroup: api 86 MiB (Spitze 133; erste Messung lief während des Neustarts); worker 45 MiB (Spitze 45); web 43 MiB (Spitze 44).

## Nach Deploy `2361e48` (29.09.2026, Passwort vergessen, Datenexport, Konto löschen)

Migration 0004 gelaufen. API und Worker ohne Fehler. **Beobachtung:** Der Web-Proxy erreichte die
API noch rund zwei Minuten nach ihrem Neustart unter der alten Adresse nicht (`connect ETIMEDOUT
100.121.38.184:8000`, Anfragen bekamen 500), danach normal. Nach jedem Ausrollen droht so ein kurzes
Fenster mit Fehlern; Ursache vermutlich ein zwischengespeicherter DNS-Eintrag für `api`. cgroup: api 88 MiB (Spitze 135); worker 51 MiB (Spitze 51); web 115 MiB (Spitze 116).

## Nach Deploy `66d4217` (29.09.2026, Wiederversuch zur API nach Neustart)

Gemessen mit gezieltem API-Neustart und einer Anfrage pro Sekunde über die Weboberfläche:
100 von 100 erfolgreich (vorher: 1 × 500, 3 × hängend bis zur Linux-Frist von rund 127 s).
Anfragen im Fenster warten jetzt höchstens rund 21 s. Logs ohne Fehler. cgroup: api 157 MiB (Spitze 187); worker 93 MiB (Spitze 368); web 101 MiB (Spitze 102).

## Nach Deploy `adb0704` (29.09.2026, Datenexport als Datenstrom)

Logs ohne Fehler. cgroup: api 80 MiB (Spitze 126); worker 50 MiB (Spitze 50); web 121 MiB (Spitze 134).

## Nach Deploy `cdc6ad9` (29.09.2026, Bericht per Link teilen)

Logs ohne Fehler. cgroup: api 88 MiB (Spitze 132); worker 46 MiB (Spitze 46); web 122 MiB (Spitze 122).

## Nach Deploy `c4dee0f` (29.09.2026, Schnellscan mit Datei bis 2 MB)

Live geprüft: Datei-Schnellscan fertig in rund 5 s, 2,2 MB → 413. Logs seit der Korrektur ohne
Fehler (die zwei `EPIPE` stammen aus dem Test vor `c4dee0f`, siehe `docs/log.md`).
cgroup: api 89 MiB (Spitze 135); worker 45 MiB (Spitze 45); web 130 MiB (Spitze 130).

## Nach Deploy `d7682aa` und `d528216` (29.09.2026, Upload-Grenze hinter der Weiterleitung, offene K/H auf der Übersicht)

Live: Schnellscan mit 2,2 MB und 20 MB → 413 statt 500; Übersicht ohne Anmeldung → Weiterleitung
zur Anmeldung, `offene-befunde` → 401. Logs ohne Fehler.
cgroup nach `d528216`: api 88 MiB (Spitze 133); worker 45 MiB (Spitze 45); web 70 MiB (Spitze 71).

## Nach Deploy `3570512` (29.09.2026, Quelle beim Anlegen, Versionsliste)

Health ok, `versions` ohne Anmeldung → 401, Logs ohne Fehler.
cgroup: api 88 MiB (Spitze 131); worker 48 MiB (Spitze 48); web 161 MiB (Spitze 169).

## Nach Deploy `7eda75d` (29.09.2026, Explorer-Layout, PDF-Bericht)

PDF im laufenden API-Container erzeugt (Schriften im Image), PDF-Route ohne Anmeldung → 401,
neue Seiten `/projekte` und `/pruefungen` leiten ohne Anmeldung weiter. Logs ohne Fehler.
cgroup: api 94 MiB (Spitze 131, ReportLab kaum spürbar); worker 53 MiB (Spitze 53); web 75 MiB (Spitze 90).
