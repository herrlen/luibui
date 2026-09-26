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

**RAM-Verbrauch auf dem Server: nicht gemessen.** Die mittwald-API und `mw` liefern keine
Container-Messwerte, und `mw container exec` braucht einen SSH-Schlüssel im mittwald-Konto, der
nicht hinterlegt ist. Ablesbar in mStudio (Container → Auslastung).

**Lokal gemessen (Colima, leerer Stack, keine Prüfung aktiv), als Anhaltspunkt:**

| Container | RAM |
|---|---|
| worker | 50 MiB |
| api | 62 MiB |
| web | 35 MiB |
| postgres | 34 MiB |

Die Limits sind also bisher kaum ausgeschöpft. Aussagekräftig wird die Messung erst mit echten
Prüfungen und Scannern (S1-12).

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

**Nicht geprüft:** ob der Worker auf dem Volume `luibui-scratch` schreiben darf (lokal gehört
`/scratch` dem Nutzer 10001; ob mittwald die Rechte aus dem Image übernimmt, ist offen). Der Worker
startet ohne Fehler, liest `/scratch` also. Der erste echte Job in Sprint 1 zeigt es; bis dahin
kommt eine Schreibprobe beim Start des Workers dazu.

## Ausrollen

```sh
# vom Repository-Wurzelverzeichnis, MITTWALD_API_TOKEN gesetzt
E=$(mktemp) && chmod 600 "$E"
printf 'POSTGRES_PASSWORD=%s\nIMAGE_TAG=sha-%s\n' "<Passwort aus der Stack-Konfiguration>" "<commit>" > "$E"
mw stack deploy -s b8d0a6a8-83ef-4aba-b785-0b450c0ac551 -c infra/mittwald-stack.yml --env-file "$E"
rm -f "$E"
```

⚠ `mw stack deploy` ersetzt die gesamte Stack-Definition. Das Postgres-Passwort muss dasselbe
bleiben, sonst kommt die API nicht mehr an die bestehende Datenbank. Es steht in der
Stack-Konfiguration (`mw container get c-s7jsux -o json`, Feld `environment`), nirgends sonst.
