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
| Worker nur im internen Netz, kein Internet | alle Container im Projekt erreichen sich, Worker hat Internet | **muss vor Sprint 1 gelöst werden**, bevor der Worker Uploads verarbeitet (Bedrohungsmodell T13, offene Frage 2) |
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
Stack-Konfiguration (`mw container get c-s7jsux -o json`, Feld `environment`), nirgends sonst.

⚠ Dasselbe gilt ab S2-7 für `MASTER_KEY` (API-Container): Er verschlüsselt die Schlüssel aller
Projekt-Dateien. Wird er beim Ausrollen weggelassen oder ersetzt, sind alle gespeicherten Dateien
unlesbar. Beim ersten Ausrollen mit `openssl rand -base64 32` erzeugen, danach immer aus der
Stack-Konfiguration übernehmen. **Zusätzlich an einem zweiten Ort sichern (Len):** Ohne ihn hilft
auch ein Datenbank-Backup nicht.
