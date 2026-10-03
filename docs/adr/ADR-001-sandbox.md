# ADR-001: Sandbox für dynamische Prüfung (Sprint 6)

Status: **teilweise entschieden** (2026-10-03): Isolation mit nsjail, zuerst Node und MCP (Len). Offen: der Server.

## Kontext

Bisher führt luibui nie Code aus Uploads aus (CLAUDE.md Regel 1). Statische Prüfung übersieht
Verhalten, das erst zur Laufzeit entsteht: nachgeladener Code, verschleierte Befehle, Zugriffe auf
Zugangsdaten, Verbindungsversuche, Zeitbomben. Sprint 6 (S6-1 bis S6-6) führt deshalb Install-
Skripte und MCP-Server in einer Sandbox aus. Die Ausnahme von Regel 1 gilt nur dort, und nur auf
einem **eigenen Server** ohne Geheimnisse (Konzept §16, Risiko „Sandbox-Ausbruch“).

## Entscheidung (vorgeschlagen)

1. **Eigener Server**, getrennt vom mittwald-Projekt `p-yw5cv5`: ein mittwald vServer
   (Konzept: 40–80 € im Monat), Linux, nur für die Sandbox. Kein `MASTER_KEY`, keine
   Datenbank, keine Zugangsdaten zu anderen Diensten, keine Projekt-Dateien außer dem einen Paket
   des laufenden Auftrags. Buchung macht Len.
2. **Isolation mit nsjail** (Len, 2026-10-03): eigene Namespaces für Nutzer, Prozesse, Mounts,
   Netz und IPC, ein seccomp-Filter, cgroup-Limits, nur lesender Root aus einem minimalen Image,
   beschreibbar nur ein tmpfs. Der Vorschlag war gVisor (eigener Kernel im Nutzerraum); nsjail ist
   leichter, teilt aber den Host-Kernel – deshalb zählen der eigene Server ohne Geheimnisse (SB1)
   und ein strenger seccomp-Filter umso mehr. Das Systemaufruf-Protokoll (S6-3) kommt von
   `strace -f` innerhalb des Jails.
3. **Kein Netz nach außen.** Der Container bekommt ein eigenes Netz ohne Route ins Internet;
   darin laufen ein Schein-DNS (antwortet jeder Anfrage mit einer Sinkhole-Adresse) und ein
   Sinkhole, das jeden TCP/UDP-Verbindungsversuch mit Ziel, Port und den ersten Bytes
   protokolliert (S6-3). So sehen wir, wohin ein Paket will, ohne dass etwas ankommt.
4. **Köder** (S6-4): pro Lauf frisch erzeugte, eindeutige Schein-Zugangsdaten in `~/.aws/credentials`,
   `~/.ssh/id_ed25519`, `.env`, `~/.config/gh/hosts.yml` und Umgebungsvariablen. Befund, wenn
   (a) eine Köder-Datei gelesen wird, die das Manifest nicht als Recht erklärt, oder (b) ein
   Köder-Wert in einem Verbindungsversuch, einem DNS-Namen oder einer geschriebenen Datei
   auftaucht (dann K, Sperrliste „Diebstahl von Zugangsdaten“).
5. **Ablauf je Paket** (S6-2, S6-5): zuerst nur Node und MCP (Len): `npm install` mit Skripten aus
   mitgelieferten Dateien ohne Netz, danach MCP-Server starten (Node oder angegebener Befehl), `initialize`,
   `tools/list`, jedes Tool einmal mit Testdaten aufrufen. Das Ganze zweimal: mit echter Uhr und
   mit vorgedrehter Uhr (`faketime`, +400 Tage) gegen Zeitbomben. Limits pro Lauf: 2 CPU,
   1 GB RAM, 256 Prozesse, 200 MB Schreibfläche, 120 s.
6. **Anbindung:** Der Worker auf mittwald schickt das bereits geprüfte Archiv per HTTPS an den
   Sandbox-Server (Bearer-Token nur für diesen Zweck, Server akzeptiert nur die Worker-Adresse)
   und bekommt ein JSON-Protokoll zurück (Systemaufrufe zusammengefasst, Dateizugriffe,
   Verbindungsversuche, Köder-Treffer, Ausgaben gekürzt). Die Umwandlung in Befunde mit
   Nachweisgrad `in_sandbox_beobachtet` und die Bewertung bleiben im Worker (`scoring.py`). Der
   Sandbox-Server bewertet nichts und speichert nichts über den Lauf hinaus.
7. **Nur Intensivprüfung**, nur bestätigte Konten, eine Sandbox gleichzeitig. Fällt der Server
   aus, wird die Prüfung ohne Sandbox fertig und der Bericht nennt die Sandbox als „nicht
   geprüft“.

## Bedrohungsmodell (eigenes, ergänzt `threat-model.md`)

| ID | Bedrohung | Gegenmaßnahme |
|---|---|---|
| SB1 | Ausbruch aus dem Jail auf den Host | nsjail mit seccomp-Filter, kein privilegierter Container, keine Host-Mounts außer dem Paket (nur lesend), unprivilegierter Nutzer, Host ohne Geheimnisse, Host wird regelmäßig neu aufgesetzt |
| SB2 | Missbrauch als Angriffsplattform (Scans, Spam, Mining) | kein Netz nach außen (nur Sinkhole), CPU- und Zeitlimit |
| SB3 | Seitenkanal zwischen Läufen | ein Lauf gleichzeitig, frischer Container und frische Schreibfläche je Lauf |
| SB4 | Erkennen der Sandbox und Stillhalten | realistische Köder und Umgebung, vorgedrehte Uhr; Restrisiko wird im Bericht benannt („nicht beobachtet“ heißt nicht „harmlos“) |
| SB5 | Gefälschtes Protokoll an den Worker | Protokoll ist Daten, wird gegen ein Schema geprüft, Größenlimit; der Sandbox-Server kann nur Befunde hinzufügen, nie Grün erzeugen |
| SB6 | Zugriff auf den Sandbox-Server von außen | Firewall: nur SSH (Schlüssel) und der Auftrags-Endpunkt für die Worker-Adresse |
| SB7 | Ressourcenerschöpfung | Limits je Lauf, Warteschlange im Worker, Abbruch nach 120 s |

## Alternativen

- **gVisor (`runsc`):** eigener Kernel im Nutzerraum, stärkere Trennung vom Host-Kernel, etwas
  langsamer. Vorgeschlagen, nicht gewählt (Len: nsjail). Lässt sich später unter nsjail ergänzen,
  falls der Bedarf steigt.
- **Firecracker-MicroVMs:** stärkste Isolation, braucht aber KVM (auf einem vServer meist nicht
  verfügbar) und deutlich mehr Betriebsaufwand.
- **Sandbox im heutigen mittwald-Container:** ausgeschlossen (Regel 1, Server geteilt mit
  anderen Projekten).

## Was ohne den Server schon geht

- Protokoll-Schema, Umwandlung in Befunde (S6-6), Köder-Erzeugung (S6-4) und die Anbindung im
  Worker mit einem Schein-Sandbox-Server in den Tests.
- Die eigentliche Ausführung (S6-1 bis S6-3, S6-5) braucht den Server; lokal nur mit den
  entschärften Korpus-Paketen.

## Server (offen)

Stand 2026-10-03 im mittwald-Konto: **kein vServer.** Es gibt den Space-Server `s-r0ud3w`
(2 geteilte vCPU, 8 GB RAM), auf dem luibui und sieben weitere Projekte laufen, und ein Projekt ohne
eigenen Server. Ein neues Projekt auf `s-r0ud3w` wäre dieselbe Maschine mit demselben Kernel wie
die anderen Projekte; mittwald-Container laufen zudem unprivilegiert, nsjail braucht aber
Namespaces und cgroups. Das erfüllt weder Regel 1 („eigener Server“) noch SB1. Nötig ist ein
eigener vServer (bei mittwald oder einem anderen Anbieter in der EU), den Len bucht.

## Offene Fragen an Len

1. Eigenen vServer buchen (Größe: 2–4 vCPU, 4–8 GB RAM, 40 GB reichen für Node und MCP)?
