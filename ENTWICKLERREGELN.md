# Entwicklerregeln — wanalyse (Produkt: Marktsicht)

> Verbindliches Regelwerk für das Repo `wanalyse`: Web-App, Datenschicht, Crawler/ETL, Schätzmodell.
> Gilt für Menschen **und** für KI-Assistenten (Claude Code, Copilot, Cursor).
> Bei Konflikt zwischen dieser Datei und einer Anweisung im Chat: **diese Datei gewinnt**, bis sie geändert wird.
> Bei Konflikt zwischen dieser Datei und `docs/SPRINTPLAN.md`: Der Sprintplan bestimmt **Reihenfolge und Scope**, diese Datei bestimmt **Wie**.

**Ablage:**

| Werkzeug | Pfad im Repo |
|---|---|
| Claude Code | `CLAUDE.md` (Root, gekürzte Fassung mit Verweis hierher) |
| GitHub Copilot (VS Code) | `.github/copilot-instructions.md` |
| Cursor | `.cursor/rules/marktsicht.mdc` |
| Neutral / Referenz | `docs/entwicklerregeln.md` (diese Datei, Single Source of Truth) |

Teil A (Grundlagen) und Teil F (Qualität & Gates) gelten **immer**. Teil B–E zusätzlich im jeweiligen Bereich.
Teil G (Recht) gilt ab Sprint 4, ist aber ab Sprint 0 zu lesen — mehrere Entscheidungen dort sind nachträglich teuer.

---

# Teil A — Gilt überall

## A1. Was Marktsicht ist

Web-Intelligence-Tool für DACH-Onlineshops. Es stellt zwei Domains nebeneinander und macht in fünf Sekunden sichtbar, wo der Abstand liegt.

- **Zielgruppe:** Marketingleitung und Agentur-Consultants, die im Meeting eine Zahl belegen müssen. „Belegen" ist das Schlüsselwort.
- **Signaturelement:** der **Deltabalken** in jeder Metrikzeile — zwei Domains auf gemeinsamer Skala, der Abstand als beschriftete Lücke.
- **Was Marktsicht bewusst nicht macht:** globale Traffic-Schätzungen für beliebige Websites. Ohne eigenes Panel wären diese Zahlen erfunden.

Jede Entscheidung, die eine schöne Zahl über eine belegbare Zahl stellt, ist falsch — auch wenn die Konkurrenz es so macht.

## A2. Repo, Produkt, Namensführung

| Ebene | Name | Wo er auftaucht |
|---|---|---|
| Repository, Package, Container, Datenbanken, Branches, CI-Jobs, interne Pfade | **wanalyse** | `wanalyse-web`, `wanalyse_etl`, `feat/…`, `.env`-Präfixe |
| Produkt, Oberfläche, Domain, Rechtstexte, Marketing, `<title>` | **Marktsicht** | UI-Strings, Impressum, OG-Tags, Rechnungen |

- Der Produktname erscheint **nie** in Bezeichnern, der Repo-Name **nie** in der Oberfläche.
- Ein Umbenennen des Produkts darf keinen Code anfassen müssen: der Name steht in `lib/brand.ts` und in den Locale-Dateien, nirgends sonst.
- Assistenten ändern die Namensführung nicht „zur Vereinheitlichung".

## A3. Sprache & Begriffe

- Oberfläche und Rechtstexte **Deutsch**, Satzform statt Title Case. Code, Kommentare, Commits, Branch-Namen, Dateinamen **Englisch**.
- Buttons benennen die Handlung: „Vergleich speichern", nicht „Absenden".
- **Ein Wort behält seine Bedeutung durch den ganzen Flow.** Was „Verbinden" heißt, meldet danach „Verbunden" — nicht „Aktiv", nicht „Verknüpft".
- Verbindliches Begriffsregister in `docs/glossar.md`, Pflichtlektüre vor neuen Strings:

| Begriff | Bedeutung | Nicht verwenden |
|---|---|---|
| **Messwert** | stammt aus einem vom Nutzer verbundenen Konto | „echt", „real" |
| **Schätzwert** | Modellausgabe, immer als Spanne | „Prognose", „ca." |
| **Öffentlicher Wert** | direkt aus einer öffentlichen Quelle (CrUX, Radar, Tranco, Crawl) | „extern" |
| **Vergleich** | gespeichertes Domainpaar + Zeitraum | „Report", „Analyse" |
| **Serie A / Serie B** | eigene Domain / Wettbewerber | „wir/die" |
| **Rückstand** | Abstand zuungunsten von Serie A | „Verlust", „schlecht" |

- Keine Entschuldigungen in Fehlermeldungen, keine vagen Formulierungen, keine Ausrufezeichen, keine Emojis in der Oberfläche.
- Leere Zustände sind eine Aufforderung zum Handeln, keine Sackgasse.

## A4. Produktregeln — nicht verhandelbar

Diese Liste ist **kein vergessenes Backlog**. Fehlt etwas davon, ist das Absicht. Assistenten dürfen es **nicht** als Lücke „ergänzen".

- ❌ **Keine Zahl ohne Herkunft.** Jede Kennzahl in der UI trägt Quelle und Konfidenz — auch in Exporten, auch im PDF, auch im Tooltip-losen Kompaktmodus.
- ❌ **Nie eine Schätzung als Messwert darstellen.** Kein gemeinsames Styling, kein „für die Optik" weggelassenes Konfidenzlabel.
- ❌ **Keine erfundenen Zahlen zur Demonstration in Produktionscode.** Fixtures leben ausschließlich in `/data` und werden nur über `lib/data-source.ts` erreicht (A9). Ein Fallback auf Fixtures im Produktionspfad ist ein Merge-Blocker, kein Komfort.
- ❌ **Keine Punktwerte für Schätzungen.** Ausgabe immer als Spanne (E3).
- ❌ **Keine Benchmark-Aggregate unter k ≥ 20 Shops.** Darunter sind einzelne Betriebe rückrechenbar (G4).
- ❌ **Keine Hex-Werte im Komponentencode.** Nur Tokens (A5).
- ❌ **Kein Datenzugriff an `lib/data-source.ts` vorbei** (A9).
- ❌ **Keine personenbezogenen Daten in Logs, Traces oder Sentry-Events** (A11).
- ❌ **Kein Crawl gegen robots.txt** (Teil D).

Bei „nicht genug Daten" zeigt die UI **„nicht genug Daten"** — nicht eine Null, keinen Strich ohne Erklärung, keine hilfsweise interpolierte Zahl.

## A5. Design-Tokens — Single Source of Truth

Farben werden **nie** als Literal im Code geschrieben. Immer über Token (`var(--petrol)` bzw. das Tailwind-Theme). Tokens stehen ausschließlich in `app/tokens.css`.

| Token | Hex | Verwendung |
|---|---|---|
| `--ink` | `#0E1A24` | Nav-Rail, Fließtext, Tabellenzahlen |
| `--zinn` | `#EDF1F3` | Seitenhintergrund |
| `--surface` | `#FFFFFF` | Karten, Tabellen |
| `--petrol` | `#0B6E6E` | Primärfarbe, Serie A, Buttons |
| `--plum` | `#6B3FA0` | Serie B (Wettbewerber) |
| `--ocker` | `#C77A16` | Rückstand, Warnung |
| `--linie` | `#D3DBDF` | Trennlinien, Achsen |

**Gerechnete Kontrastwerte (WCAG 2.1, relative Luminanz):**

| Kombination | Ratio | Bewertung |
|---|---|---|
| `ink` auf `surface` | 17,6:1 | AAA |
| `ink` auf `zinn` | 15,5:1 | AAA |
| `plum` auf `surface` | 7,4:1 | AAA |
| `plum` auf `zinn` | 6,5:1 | AA |
| `petrol` auf `surface` | 6,1:1 | AA |
| `petrol` auf `zinn` | 5,3:1 | AA |
| **`ocker` auf `surface`** | **3,4:1** | **unter AA (Text), reicht nur für Umrisse/Icons ≥ 3:1** |
| **`ocker` auf `zinn`** | **3,0:1** | **unter AA, auf der Kante auch für Bedienelement-Umrisse** |
| `linie` auf `zinn` | 1,2:1 | reine Linienfarbe, **nie** Textfarbe |

➡️ **Regeln daraus:**

1. **`--ocker` ist keine Textfarbe.** Weder auf `zinn` noch auf `surface`. Für Rückstandszahlen und Warntexte gilt `--ocker-text: #9A5F0E` (4,6:1 auf `zinn`, 5,2:1 auf `surface`). Als Flächen-/Balkenfarbe bleibt `--ocker` unverändert.
2. **`--linie` nie als Textfarbe**, auch nicht für Achsenbeschriftung. Achsenlabels laufen in `--ink` bei reduzierter Größe, nicht in aufgehellter Farbe.
3. **Ändert sich ein Hintergrund-Token, sind alle Werte oben ungültig**, bis sie neu gerechnet sind. Eine Änderung von `--zinn` oder `--surface` ohne Neuberechnung ist ein Merge-Blocker.
4. Prüfung per `npm run check:contrast` (`scripts/contrast.ts`, rechnet alle Token-Paare durch, schlägt bei < 4,5:1 für als Text markierte Paare fehl). Gehört als Schritt in die CI (F7).

**Der Punkt, an dem der Sprintplan korrigiert wird:** Petrol und Plum sind bei Farbfehlsichtigkeit über den Farbton unterscheidbar, **in Graustufen aber nicht** — ihr Kontrast zueinander beträgt 1,2:1, ihre Luminanz ist praktisch identisch. Im Schwarzweißdruck und im Graustufen-PDF fallen Serie A und Serie B zusammen.

➡️ **Regel:** Serienzugehörigkeit wird **nie allein über Farbe** getragen. Jede Serie hat zusätzlich einen zweiten Kanal — feste Position (Serie A links/oben), direkte Beschriftung am Element, im Chart zusätzlich Linienart (durchgezogen / gestrichelt). Eine Legende, die nur Farbfelder zeigt, ist unvollständig. Getestet wird mit einem Graustufen-Snapshot des Deltabalkens und des Zeitreihen-Charts.

## A6. Typografie

- **Display: Bricolage Grotesque** — ausschließlich Seitentitel und große KPI-Zahlen. Nirgends sonst.
- **UI/Body: Inter**, `font-feature-settings: "tnum", "cv05"`. Ohne `tnum` stehen Tabellenzahlen nicht untereinander — das ist bei einem Vergleichstool kein Detail.
- **Daten/Mono: JetBrains Mono** — Achsenbeschriftung, Domains, IDs, API-Keys.
- **Typskala: 12 / 14 / 16 / 20 / 28 / 44.** Keine Zwischenwerte. Wer einen siebten Wert braucht, hat ein Layoutproblem, kein Typografieproblem.
- Alle drei Familien **selbst gehostet** als WOFF2 in `public/fonts`, `font-display: swap`, `next/font/local`. Google Fonts über CDN ist in Deutschland datenschutzrechtlich angreifbar und kostet einen Verbindungsaufbau im kritischen Pfad.
- Nur die tatsächlich genutzten Schnitte, auf `latin` + `latin-ext` subsetted. Jeder zusätzliche Schnitt braucht eine Begründung im PR (Budget: F1).
- Gegen den Sprung beim Font-Tausch `size-adjust`/`ascent-override` am Fallback setzen — CLS entsteht sonst genau im Tabellenkörper.

## A7. Layout

- **Responsive bis 375 px.** Nicht „mobil später" — die Vergleichstabelle ist ab Sprint 1 auf 375 px bedienbar.
- Dreispaltig auf Desktop (Nav-Rail, Unternavigation, Inhalt), auf schmalen Viewports kollabiert die Unternavigation, nicht der Inhalt.
- **Tabellen scrollen horizontal in ihrem eigenen Container**, das Dokument nie. Die erste Spalte (Metrikname) bleibt sichtbar.
- Touch-Ziele mindestens 44 × 44 px.
- Keine Modals für Kerninhalte. Kein Infinite Scroll ohne Endezustand.
- `prefers-reduced-motion` wird respektiert: Chart-Übergänge und Balkenanimationen entfallen dann vollständig, nicht nur verkürzt.

## A8. Herkunft und Konfidenz — die Kernregel

Jeder Wert, der die Datenschicht verlässt, trägt seine Herkunft **im Typ**, nicht in einer Konvention:

```ts
type Provenance =
  | { kind: 'measured'; source: 'ga4' | 'gsc' | 'shopify' | 'woocommerce' | 'ads'; connectedAt: string }
  | { kind: 'public';   source: 'crux' | 'radar' | 'tranco' | 'crawl' | 'serp'; observedAt: string }
  | { kind: 'estimated'; model: string; version: string; interval: [number, number]; mape: number }
  | { kind: 'insufficient'; reason: string };

type Metric<T> = { value: T | null; provenance: Provenance; asOf: string };
```

- **Es gibt keinen nackten `number` in der Metrik-API.** Ein Wert ohne Herkunft lässt sich nicht rendern — das ist Absicht und wird vom Typsystem erzwungen, nicht von Disziplin.
- `kind: 'estimated'` hat **immer** ein `interval`. Ein Punktwert ohne Spanne ist ein Typfehler.
- `kind: 'insufficient'` rendert als „nicht genug Daten" plus `reason`, nie als `0` und nie als leere Zelle.
- **Die visuelle Unterscheidung ist Pflicht und einheitlich:** gemessen = volltonige Fläche, öffentlich = volltonig mit Quellenkürzel, geschätzt = schraffierte Fläche + Spannenband + `ConfidenceBadge`. Ein `ConfidenceBadge` wegzulassen, „weil die Zeile sonst unruhig wird", ist ein A4-Verstoß.
- **Export erbt die Kennzeichnung.** CSV bekommt Spalten `provenance`, `source`, `as_of`, `interval_low`, `interval_high`; PDF bekommt Fußnoten mit Quelle und Stand. Ein Export ohne Herkunft ist die häufigste Art, aus einer ehrlichen Zahl eine unehrliche zu machen — er landet in einer Präsentation, wo der Kontext fehlt.
- `asOf` ist der Stand der Daten, nicht der Zeitpunkt der Abfrage. Beides zu verwechseln erzeugt frische Zahlen, die alt sind.

## A9. Datenzugriff — genau eine Schnittstelle

- **Alle Datenzugriffe laufen über `lib/data-source.ts`.** Komponenten kennen keine Fixtures, kein SQL, keine externen APIs, keinen `fetch` auf Drittdienste.
- Die Schnittstelle ist ab Sprint 1 stabil und wird in Sprint 4 nur **implementierungsseitig** getauscht — keine Signaturänderung, weil „die echte Quelle das anders liefert". Liefert die Quelle etwas anderes, wird im Adapter übersetzt.
- Genau drei Implementierungen: `fixtures` (nur `NODE_ENV !== 'production'`), `live`, `hybrid` (Messwerte live, Rest öffentlich). Auswahl über Umgebungsvariable, nie über Code-Zweig in einer Komponente.
- **Ein Aufruf, ein Netzwerkgang.** Kein N+1 über Metrikzeilen: Die Vergleichsansicht holt ihre Werte in einer Abfrage pro Domain und Zeitraum, nicht pro Zeile.
- Serverkomponenten holen Daten; Clientkomponenten bekommen sie als Props. Kein `useEffect`-Fetch für Erstdaten.

## A10. Datenmodell (Kern)

**Postgres** (Wahrheit über Nutzer und Konfiguration): `users` · `organizations` · `memberships` · `projects` · `comparisons` · `connections` (OAuth-Tokens) · `consents` · `plans` · `quota_usage` · `audit_log`

**ClickHouse** (Zeitreihen und Metriken): `metrics_daily` · `crawl_snapshots` · `serp_positions` · `estimates`

**Redis**: Cache, Rate-Limits, Job-Locks — **niemals** die einzige Kopie von etwas.

- **Kein personenbezogenes Datum in ClickHouse.** Dort stehen Domains, Metriken, Zeitstempel — keine E-Mails, keine Nutzer-IDs im Klartext, keine Kunden-IDs aus verbundenen Shops. Verknüpfung über opake `project_id`.
- **OAuth-Tokens verschlüsselt at rest** (`connections.access_token_enc`), Schlüssel aus der Umgebung, nie im Repo. Kein Token in einem Log, einer Fehlermeldung oder einem Tracing-Attribut (A11).
- Migrationen sind reversibel (`down()` implementiert und getestet, F7).
- ClickHouse-Tabellen sind **append-only mit `asOf`**. Werte werden nicht überschrieben — eine korrigierte Schätzung ist eine neue Zeile, sonst lässt sich ein Vergleich von letzter Woche nicht mehr reproduzieren.
- **Reproduzierbarkeit ist Pflicht:** Ein gespeicherter Vergleich muss die Zahlen zeigen können, die er zum Speicherzeitpunkt zeigte, inklusive Modellversion. Ein Kunde, der eine Zahl im Meeting belegt hat, darf sie eine Woche später nicht verändert vorfinden.
- Kontolöschung: dokumentiert im Löschkonzept (`docs/loeschkonzept.md`), nicht ad hoc entschieden.

## A11. Datenschutz & Recht (Kurzfassung, Details in Teil G)

- **Datensparsamkeit ist Feature, nicht Auflage.** Kein Feld erheben, das kein Nutzungsszenario hat.
- **Keine personenbezogenen Daten in Logs, Traces, Sentry-Events, Fehlermeldungen oder Analytics.** Das schließt ein: E-Mail-Adressen, OAuth-Tokens, Kunden-IDs und Bestelldaten aus verbundenen Shops, Suchanfragen aus der GSC-Integration, IP-Adressen über das technisch Nötige hinaus.
- Sentry läuft mit `beforeSend`-Scrubber und aktivem PII-Filter; der Scrubber hat einen Unit-Test mit realistischen Beispiel-Payloads. Ein Filter, den niemand testet, ist kein Filter.
- Jeder eingebundene Drittdienst steht in `docs/drittdienste.md`: Anbieter, Zweck, verarbeitete Daten, Rechtsgrundlage, Serverstandort, AV-Vertrag ja/nein. **Kein Eintrag → keine Einbindung.**
- Alles, was nicht technisch notwendig ist, lädt erst nach Einwilligung (§ 25 TDDDG). Reichweitenmessung bevorzugt serverseitig oder cookiefrei.
- **Keine Session-Recorder.** Die Oberfläche zeigt Wettbewerbsdaten und verbundene Shop-Zahlen; deren Mitschnitt ist ein eigener Verarbeitungsvorgang mit fremden Betroffenen.

> Operative Checkliste, keine Rechtsberatung. Juristische Prüfung bleibt Pflicht.

## A12. Sicherheit

- Keine Secrets im Repo. `.env` ignoriert, `.env.example` gepflegt, Secret-Scanning in CI.
- **Jede Domaineingabe ist Nutzereingabe.** Normalisieren (Punycode, Kleinschreibung, `www` entfernen), gegen eine Allowlist von Schemata prüfen, erst dann verwenden. Eine Domain aus dem Eingabefeld darf nie ungeprüft in eine Query, eine URL oder einen Shell-Aufruf gelangen.
- **SSRF ist hier die reale Gefahr, nicht XSS.** Der Crawler und die Domain-Vorschau folgen einer vom Nutzer bestimmten URL. Deshalb: private IP-Bereiche, `localhost`, `169.254.169.254` und Metadaten-Endpunkte blockieren — nach DNS-Auflösung, nicht nur anhand des Hostnamens; Redirects begrenzt folgen und jedes Ziel erneut prüfen; Antwortgröße und Timeout hart begrenzen.
- Autorisierung serverseitig bei jedem Endpoint über eine zentrale Policy-Schicht, nicht durch Ausblenden von Buttons. **Jede Query auf Projektdaten filtert auf `organization_id`** — Mandantentrennung ist eine Datenbankbedingung, keine UI-Eigenschaft.
- Keine ungeprüfte Ausgabe von Fremdinhalt: Was der Crawler von einer fremden Domain liest (Titel, Produktnamen, Theme-Namen), ist unvertrauenswürdig. Nie `dangerouslySetInnerHTML`, nie ungefiltert in ein `<a href>`, keine automatische Verlinkung gecrawlter URLs.
- Rate Limiting serverseitig pro Nutzer **und** pro IP **und** pro API-Key. `429` mit `Retry-After`, Clients mit exponentiellem Backoff.
- `npm audit` und Dependabot in CI.

## A13. Arbeitsweise für KI-Assistenten

1. **Prüfen, nicht annehmen.** Vor Änderungen den Ist-Zustand lesen (Dateien, Migrationen, `data-source.ts`, Tokens). Keine Bibliothek, kein API-Feld, kein Datenbankschema als vorhanden voraussetzen.
2. **Plan-Modus für alles Größere**, verbindlich für Sprint 4 und 6. Erst Plan zeigen, dann bauen.
3. **Kleine Diffs.** Eine Aufgabe = ein commit-fähiger Schritt.
4. **Keine ungefragten Zusatzfeatures**, besonders nichts aus der Verbotsliste A4. „Ich habe der Zeile gleich noch einen Punktwert gegeben, damit sie ruhiger aussieht" ist ein Fehler, kein Service.
5. **Keine neuen Abhängigkeiten ohne Rückfrage.** Begründung: was löst sie, was kostet sie, was ist die Alternative in Bordmitteln.
6. **Keine erfundenen Werte, auch nicht als Platzhalter.** Wo eine Zahl fehlt, steht `kind: 'insufficient'` mit Grund — nicht `42`, nicht `Math.random()`, nicht ein „realistisch aussehender" Wert.
7. **Unsicherheit benennen** statt plausibel klingend zu raten. Offene Punkte als `TODO(entscheidung):` markieren.
8. Nichts löschen und nichts umformatieren, was nicht Teil der Aufgabe ist.
9. Vor jedem neuen Sprint `/compact`, eine Session pro Sprint.

## A14. Git & Definition of Done

- Branches: `feat/…`, `fix/…`, `chore/…`, `docs/…`, `etl/…`
- Commits: Conventional Commits, englisch, Imperativ, **Sprintnummer im Scope**: `feat(s2): delta bar in metric rows`.
- `main` ist immer deploybar. Kein Direkt-Push auf `main`.
- Datenbank- und Modelländerungen bekommen einen ADR in `docs/adr/`, nummeriert, mit Datum und Alternativen.

**Definition of Done:** siehe PR-Checkliste in **F9**. Sie ist die einzige gültige Liste — nicht duplizieren.

---

# Teil B — Frontend (Next.js App Router / TypeScript / Tailwind)

- TypeScript **strict**, `noUncheckedIndexedAccess` aktiv. Kein `any` in eingechecktem Code; `unknown` plus Narrowing ist die Alternative. Kein `@ts-ignore` ohne `@ts-expect-error` mit Begründung.
- **Server Components sind der Standard.** `"use client"` nur, wo Interaktion es erzwingt, und so weit unten im Baum wie möglich. Eine Client-Komponente, die nur Daten durchreicht, ist ein Fehler.
- Keine Geschäftslogik in Komponenten: Komponente rendert, `lib/` rechnet, `server/` holt. Formatierung (Zahlen, Prozente, Zeiträume, Domains) ausschließlich über `lib/format.ts` — **deutsche Locale, `Intl.NumberFormat`**, nie handgebaute String-Ersetzung.
- **Der `DeltaBar` existiert genau einmal.** Zwei Implementierungen des Signature-Elements sind zwei Wahrheiten über das wichtigste Element des Produkts.
- Geteilte Primitive, jeweils **einmal** vorhanden und vor jeder Neuentwicklung zu prüfen:
  `Card` · `MetricRow` · `DeltaBar` · `DataTable` · `EmptyState` · `Skeleton` · `ConfidenceBadge` · `SourceTag` · `TimeRangePicker` · `DomainInput` · `Toast`
- **Charts:** ECharts, gekapselt in `components/charts/*`. Kein ECharts-Import außerhalb dieses Ordners, keine Chart-Optionen im Seitencode. Achsen, Farben und Schriften kommen aus den Tokens (A5), nicht aus ECharts-Defaults. Charts werden dynamisch importiert (`ssr: false`) und zählen gegen das JS-Budget (F1).
- **Tabellen:** TanStack Table, echte `<table>`-Semantik mit `<th scope>`, `<caption>` und Sortierzustand über `aria-sort`. Keine `div`-Raster mit Tabellenoptik.
- Jede Liste hat vier definierte Zustände: **Laden (Skeleton mit stabiler Höhe), leer, teilweise Daten, Fehler.** Kein Zustand ist optional, „teilweise Daten" ist der häufigste im Echtbetrieb — eine Domain verbunden, die andere nicht.
- **Kein Layout-Sprung beim Nachladen.** Skeletons haben die Maße des Endzustands; das ist die CLS-Hauptquelle bei einer Tabellenanwendung.
- Kein globaler State ohne Not: URL-Parameter tragen Domainpaar, Zeitraum und Land. Ein Vergleich muss per Link teilbar sein — das ist Feature und Zustandsspeicher zugleich.
- Keine `onclick`-Attribute, keine globalen Funktionen, keine Inline-Styles außer für dynamische Werte über CSS Custom Properties.

---

# Teil C — Backend, API & Datenschicht

- **API unter `/api/v1/…`**, Versionierung im Pfad. Breaking Changes → `v2`, kein stilles Umbauen. Der öffentliche API-Key-Zugang (Sprint 7) macht das verbindlich.
- JSON, Feldnamen `snake_case`, Zeitangaben **ISO 8601 UTC**. Die UI rechnet in `Europe/Berlin` um — die API tut es nie.
- Paginierung **cursorbasiert**, nie Offset.
- Einheitliches Fehlerformat:
  ```json
  { "error": { "code": "quota_exceeded", "message": "…", "fields": {} } }
  ```
  `code` ist maschinenlesbar und stabil; `message` ist deutsch und darf sich ändern. **Clients werten nie `message` aus.**
- Jede Eingabe wird am Rand mit **Zod** validiert — Request-Bodies, Query-Parameter, Umgebungsvariablen beim Start **und jede Antwort einer externen API**. Ein Feldtyp-Wechsel bei GA4 oder Cloudflare darf nie einen Renderfehler erzeugen, sondern führt zu `kind: 'insufficient'` mit Grund.
- **Kontingente werden serverseitig geprüft**, vor der teuren Operation, nicht danach. Überschreitung liefert `quota_exceeded` mit einer Meldung, die sagt was passiert ist und was zu tun ist.
- **Caching-Regel:** ClickHouse-Abfragen für Vergleichsansichten gehen über Redis mit einem Schlüssel aus `(domain_pair, range, country, source_version)`. Ändert sich die Modellversion, ändert sich der Schlüssel — Schätzungen aus zwei Modellversionen dürfen nie in derselben Ansicht stehen.
- Cache-Einträge tragen `asOf` mit; ein Treffer verändert nie den angezeigten Stand.
- Langlaufendes (Crawls, PDF-Export, Backfills) läuft als Job mit Statusabfrage, nie im Request. Jobs sind **idempotent** und wiederholbar.
- Migrationen: Postgres über eine Migrationsdatei pro Änderung, ClickHouse-Schemata versioniert in `etl/schema/`. `migrate:fresh` + `rollback` läuft in CI (F7).

---

# Teil D — Crawler & ETL

> Ein Crawler, der fremde Shops belastet, kostet das Produkt. Diese Regeln sind kein Stil, sondern Betriebsgrundlage.

**D1. Zugangsregeln — nicht verhandelbar**

- **robots.txt wird respektiert**, vor jedem Host geladen, gecacht, bei Ablauf neu geholt. Ein Disallow gilt, auch wenn die Daten interessant wären.
- Eigener User-Agent mit Produktnamen **und Kontakt-URL**: `MarktsichtBot/1.0 (+https://…/bot)`. Diese Seite existiert, nennt Zweck, Frequenz und eine Abmeldemöglichkeit.
- **Rate-Limit pro Host**, nicht global: höchstens eine Anfrage gleichzeitig pro Host, Mindestabstand, exponentielles Backoff bei `429`/`5xx`, Abbruch nach definierten Fehlversuchen mit Sperre für 24 Stunden.
- Crawl-Fenster außerhalb der Hauptlastzeiten des Zielshops, wo erkennbar.
- **Kein Umgehen von Bot-Schutz.** Keine rotierenden Wohn-IPs, keine gefälschten User-Agents, kein Captcha-Lösen, kein Headless-Browser, der sich als Mensch tarnt. Wo ein Shop nicht gecrawlt werden will, steht `kind: 'insufficient'` — nicht ein Umweg.
- Keine Anmeldung, kein Warenkorb, keine Checkout-Simulation. Nur öffentlich abrufbare Ressourcen.

**D2. Shop-Erkennung — das Alleinstellungsmerkmal**

- Shopify: `x-shopid`-Header, `cdn.shopify.com`-Assets, `/products.json`. WooCommerce: `/wp-json/wc/store/products`, `woocommerce-`-Klassen, Plugin-Assetpfade.
- **Jedes Erkennungsmerkmal ist einzeln gespeichert und einzeln bewertet** (`signal`, `confidence`, `observed_at`). Die Aussage „Shopify" ist eine Ableitung aus Signalen, nicht ein Feld — sonst lässt sich später nicht erklären, warum eine Erkennung falsch war.
- Erkennungsregeln liegen als Daten in `etl/detectors/*.yaml`, nicht als `if`-Kaskade im Code. Ein neues Theme-Muster ist eine Datenzeile plus Fixture-Test, kein Deploy-Risiko.
- **Jeder Detektor hat einen Fixture-Test** mit einer eingefrorenen echten Antwort (`etl/fixtures/`), damit eine Änderung an fremden Shopsystemen als Testfehler auffällt statt als stille Fehlklassifikation.
- Sortimentsgröße, Preisspanne und Änderungsraten sind **beobachtete Werte mit Stand**, keine Hochrechnungen (`kind: 'public'`).

**D3. Pipeline**

- Crawler → Queue → Objektspeicher (Parquet) → Transformation → ClickHouse → API. **Rohantworten bleiben roh**: Der Rohbestand wird nie überschrieben, Transformationen sind aus ihm reproduzierbar.
- Jeder Job ist idempotent und trägt eine `run_id`; ein Re-Run erzeugt keine Duplikate.
- **Datenqualitäts-Gates vor dem Laden:** Zeilenzahl gegenüber dem Vortag im erwarteten Korridor, Pflichtfelder vorhanden, Domains normalisiert, keine Duplikate pro `(domain, date)`. Reißt ein Gate, wird nicht geladen und ein Alarm ausgelöst — **kein Teilbestand in ClickHouse**, denn eine halb geladene Zeitreihe sieht in der UI aus wie ein Traffic-Einbruch beim Wettbewerber.
- Quellenregister `docs/datenquellen.md`: Quelle, Lizenz/Nutzungsbedingungen, Aktualisierungsfrequenz, Abdeckungsgrenzen, Kosten. **Bekannte Abdeckungsgrenzen gehören in die UI**, nicht nur in die Doku — CrUX deckt nur Origins ab einer Mindestpopularität ab; für kleinere Shops heißt das „nicht genug Daten", nicht „wenig Traffic".
- Kein Crawl-Ergebnis fremder Shops wird als öffentliche Rangliste veröffentlicht, ohne dass Teil G geprüft ist.

---

# Teil E — Schätzmodell & Ehrlichkeit

> Das Gegenstück zur „Deceptive Code Policy" — hier keine Store-Auflage, sondern die Geschäftsgrundlage. Marktsicht verkauft Belegbarkeit. Eine erfundene Zahl entwertet jede echte daneben.

**E1. Keine simulierte Substanz**

- Keine aufgefüllten Werte, keine geglätteten Lücken, keine interpolierten Tage, die als gemessen erscheinen. Eine Lücke in der Zeitreihe ist eine sichtbare Lücke.
- Keine „X Shops werden gerade analysiert"-Zahlen, die nicht stimmen. Keine erfundenen Nutzerzahlen, keine Beispieldaten in Marketing-Screenshots ohne Kennzeichnung.
- Fixtures aus Sprint 1–2 werden in Sprint 4 **entfernt oder hinter die Nicht-Produktionsschranke gestellt** — nicht als Fallback stehen gelassen.

**E2. Modelldisziplin**

- Modellversion ist Teil jeder Ausgabe (`model`, `version`) und Teil des Cache-Schlüssels (Teil C).
- **Trainingsdaten sind ausschließlich eingewilligte Ground-Truth-Daten** (Sprint 5) plus öffentliche Merkmale. Kein Training auf Daten, deren Einwilligung widerrufen wurde — Widerruf löst ein dokumentiertes Retraining aus.
- Feature-Set, Zielgröße und Trainingslauf sind in `docs/modell.md` versioniert; ein Modell, dessen Trainingslauf nicht reproduzierbar ist, geht nicht in Produktion.
- **Backtesting-Report ist Pflichtteil jedes Modell-Release:** MAPE nach Größenklasse und Branche, dokumentiert und **in der UI abrufbar**. Verschlechtert sich die MAPE einer Größenklasse gegenüber der Vorversion, wird das im PR benannt, nicht im Mittelwert versteckt.

**E3. Darstellung von Schätzungen**

- **Ausgabe immer als Spanne**, nie als Punktwert. Auch in Exporten, auch im Chart (Band statt Linie).
- Die Spanne ist ehrlich breit. Eine künstlich verengte Spanne, „weil das souveräner aussieht", ist der schwerste Verstoß in diesem Dokument.
- Wo das Modell unsicher ist — typischerweise kleine Shops —, steht die Warnung **an der Zahl**, nicht in einer Fußnote.
- **Unter der Datengrundlage zeigt die UI „nicht genug Daten"** statt einer Zahl. Diese Schwelle steht in der Konfiguration, ist getestet und wird nicht produktseitig „aufgeweicht", weil leere Zellen schlecht aussehen.
- Ein Deltabalken darf nie zwei Werte unterschiedlicher Herkunft ohne Kennzeichnung gegenüberstellen. Messwert gegen Schätzwert ist erlaubt — aber sichtbar als solcher, mit der Spanne des Schätzwerts im Balken.

---

# Teil F — Qualität & Quality Gates

> Regeln, die nicht automatisiert geprüft werden, werden nicht eingehalten.

## F1. Performance-Budget (verbindlich)

Referenz: mobil, gedrosseltes 4G, 375 px, Vergleichsansicht mit zwei Domains und sechs Metriken.

| Kennwert | Budget | Anmerkung |
|---|---|---|
| **Vergleichsansicht interaktiv** | **< 2,0 s** | die Zusage aus dem Sprintplan, gemessen als TTI |
| LCP | < 2,5 s | LCP-Kandidat ist der Seitentitel bzw. die erste KPI-Zahl |
| CLS | < 0,1 | Hauptrisiken: Font-Tausch und Tabellen-Skeletons |
| INP | < 200 ms | Zeitraumwechsel ist die kritische Interaktion |
| Lighthouse Performance (mobil) | ≥ 90 | |
| **Lighthouse Accessibility** | **≥ 95** | harte Grenze aus CLAUDE.md |
| JS initial (First Load, Vergleichsansicht) | < 180 KB gzip | ECharts nur dynamisch nachgeladen |
| Fonts gesamt | < 100 KB | drei Familien, nur genutzte Schnitte, subsetted |
| Serverantwortzeit `/api/v1/compare` (p95) | < 400 ms | mit warmem Cache |

Budget-Verstoß = **Merge gesperrt**, nicht „später optimieren".

## F2. Fehlerbehandlung

- Jeder Netzwerkaufruf hat einen Fehlerpfad mit **sichtbarer Rückmeldung**. Kein stiller Abbruch.
- **Keine leeren `catch`-Blöcke.** Minimum: Logging ohne personenbezogene Daten + Fallback-Zustand in der Oberfläche.
- **Ein Ausfall einer Quelle darf nie die ganze Ansicht killen.** Fällt GSC aus, während GA4 antwortet, zeigt die Ansicht die vorhandenen Zeilen und für die übrigen `kind: 'insufficient'` mit Grund. Teil-Verfügbarkeit ist der Normalfall, nicht der Ausnahmefall.
- Der Nutzer sieht nie einen rohen Fehlercode ohne Handlungsoption („Erneut versuchen", „Verbindung prüfen").
- Ein verlorener gespeicherter Vergleich ist ein schwerer Fehler. Eingaben überstehen Verbindungsabbruch und Neuladen.

## F3. Textbausteine an genau einer Stelle

- **Keine hartcodierten nutzersichtbaren Strings.** Alle über `locales/de.json`, Zugriff über den `t()`-Helfer.
- `aria-label` und Chart-Beschriftungen ebenfalls über Textbausteine, nie inline.
- Serverfehler kommen als stabiler `code` (Teil C); die Formulierung liegt in den Locales.
- Struktur folgt dem Glossar (A3): Wer einen Begriff ändert, ändert ihn an einer Stelle — sonst heißt derselbe Zustand an zwei Orten anders.

## F4. Dateigrößen & Zuständigkeit

| Artefakt | Grenze | Danach |
|---|---|---|
| React-Komponente | 200 Zeilen | in Teilkomponenten zerlegen |
| Route-Handler | 120 Zeilen | Logik in `server/` oder `lib/` |
| Chart-Konfiguration | 150 Zeilen | gemeinsame Basisoptionen extrahieren |
| Inline-CSS / `style`-Objekt | 30 Zeilen | eigene Datei bzw. Tailwind-Klassen |
| ETL-Job | 300 Zeilen | in Schritte aufteilen |

- Magic Numbers in benannte Konstanten (`MIN_BENCHMARK_K`, `MAX_CRAWL_REDIRECTS`, `CONFIDENCE_THRESHOLD`), nicht verstreut.

## F5. Geteilte Bausteine zuerst prüfen

Vor jeder neuen Komponente oder Utility nachsehen, ob es sie schon gibt. Diese existieren **genau einmal**:

`DeltaBar` · `ConfidenceBadge` · `SourceTag` · Zahlen-/Prozent-/Zeitraum-Formatter · Domain-Normalisierung · Zeitraum-Berechnung · Konfidenzintervall-Formatierung · Fehler-Toast

## F6. Barrierefreiheit — messbar

- Kontrast ≥ 4,5:1 für Text (Werte in A5), ≥ 3:1 für Bedienelement-Umrisse und Diagrammelemente.
- **Sichtbarer Fokusring überall**, nie `outline: none` ohne Ersatz. Die Nav-Rail ist vollständig per Tastatur bedienbar.
- Skip-Link zum Hauptinhalt, Überschriftenhierarchie ohne Sprünge.
- Jede asynchrone Änderung (Vergleich geladen, Zeitraum gewechselt, Export fertig) meldet sich über `aria-live`.
- Dialoge: Fokus-Falle, ESC schließt, Fokus kehrt zum Auslöser zurück.
- **Jedes Diagramm hat ein Textäquivalent**: der Deltabalken nennt beide Werte, die Einheit, den Abstand und die Herkunft („Serie A 12.400 Besuche gemessen, Serie B 18.900 bis 24.100 geschätzt, Rückstand rund 8.000"). Ein reiner CSS-Balken ist für Screenreader und für Browser-Agenten unsichtbar.
- **Nie Farbe als einziger Informationsträger** (A5) — geprüft im Graustufen-Snapshot.
- `prefers-reduced-motion` schaltet Animationen ab, nicht nur kürzer.

## F7. Automatisierte Gates

**Pre-Commit (Husky oder Lefthook):**
```
Commit
  ├─ 1. Biome/ESLint + Format --check   ──(Fehler)──► abgelehnt
  ├─ 2. tsc --noEmit (strict)           ──(Fehler)──► abgelehnt
  └─ 3. Vitest (betroffene Tests)       ──(rot)────► abgelehnt
                                         (grün) ──► Commit erlaubt
```

**CI bei Pull Request:**
```
PR
  ├─ 1. Vitest — vollständige Suite
  ├─ 2. tsc --noEmit
  ├─ 3. npm audit + Secret-Scan
  ├─ 4. Playwright E2E (Vergleichspfad, Export, Verbinden/Trennen)
  ├─ 5. Lighthouse CI mobil gegen F1     ──(Budget gerissen)──► Merge gesperrt
  ├─ 6. Bundle-Size-Check gegen F1
  ├─ 7. Kontrast-Check aller Token-Paare (A5)
  ├─ 8. Migrationstest: fresh + rollback
  ├─ 9. Detektor-Fixture-Tests (D2)
  └─ 10. Provenance-Lint: keine nackte Zahl in der Metrik-API (A8)
                                         (alles grün) ──► Review
```

**Nicht automatisierbar** und deshalb Pflicht in der PR-Checkliste: die Verbote aus A4, die Ehrlichkeitsregeln aus Teil E, Tonalität nach A3 und der manuelle Screenreader-Spotcheck.

## F8. Tests — was wirklich getestet wird

- **Unit (Vitest):** Formatter, Konfidenzintervall-Darstellung, Domain-Normalisierung, SSRF-Blockliste, PII-Scrubber, Deltabalken-Berechnung, Modellausgabe-Serialisierung.
- **Contract:** Zod-Schemata gegen eingefrorene echte Antworten von GA4, GSC, CrUX, Radar, Shopify, WooCommerce. Diese Tests fangen fremde API-Änderungen ab, bevor Nutzer sie sehen.
- **E2E (Playwright):** Domain eingeben → vergleichen → Zeitraum wechseln → exportieren; Konto verbinden → Werte werden zu Messwerten → trennen → Werte werden wieder zu Schätzwerten; Kontingent überschreiten.
- **Zwei Testkonten sehen ihre Daten getrennt** — dieser Test existiert ab Sprint 3 und wird nie übersprungen.
- **Snapshot:** Deltabalken und Chart in Farbe **und** in Graustufen.

## F9. PR-Checkliste

- [ ] Lint · `tsc` · Vitest · Playwright grün
- [ ] Lighthouse mobil im Budget, Accessibility ≥ 95 (F1)
- [ ] Keine Regel aus **A4** verletzt — keine Zahl ohne Herkunft, keine Schätzung ohne Spanne, kein Fixture-Fallback in Produktion
- [ ] Jede neue Kennzahl trägt `Provenance` und wird gemessen/öffentlich/geschätzt **visuell unterschieden** (A8)
- [ ] Export (CSV/PDF) trägt Herkunft, Stand und Spanne (A8)
- [ ] Keine Farb-, Größen- oder Font-Literale statt Token (A5/A6)
- [ ] `--ocker` nicht als Textfarbe; Serienunterscheidung nicht allein über Farbe (A5)
- [ ] Datenzugriff ausschließlich über `lib/data-source.ts` (A9)
- [ ] Keine personenbezogenen Daten in Logs, Traces, Sentry (A11)
- [ ] Neue Drittdienste in `docs/drittdienste.md`, neue Quellen in `docs/datenquellen.md` (A11/D3)
- [ ] Neue Strings in `locales/de.json`, Begriffe nach Glossar (A3/F3)
- [ ] Jeder Fehlerpfad mit sichtbarer Rückmeldung; Teil-Verfügbarkeit behandelt (F2)
- [ ] Fokusring, Tastaturbedienung, `aria-live`, Textäquivalent des Deltabalkens (F6)
- [ ] Bei Datenänderung: Migration reversibel, Löschkonzept weiterhin gültig (A10/G3)
- [ ] Bei Crawler-Änderung: robots.txt, Rate-Limit, User-Agent, Qualitäts-Gates geprüft (Teil D)
- [ ] Bei Modelländerung: Backtesting-Report aktualisiert, MAPE-Änderung im PR benannt (E2)
- [ ] Keine neue Abhängigkeit ohne Begründung im PR-Text (A13)
- [ ] Mandantentrennung: neue Queries filtern auf `organization_id` (A12)
- [ ] Manueller Screenreader-Spotcheck durchgeführt

---

# Teil G — Recht & Datenschutz im Detail

> Gilt ab Sprint 4 operativ, ab Sprint 0 planerisch. Operative Checkliste, keine Rechtsberatung.

**G1. Rollen und Verträge**

- Bei verbundenen Konten ist Marktsicht **Auftragsverarbeiter** für die Daten des Kunden. AV-Vertrag nach Art. 28 DSGVO als Vorlage im Onboarding, nicht nachträglich per Mail.
- Verzeichnis von Verarbeitungstätigkeiten wird gepflegt (`docs/vvt.md`), nicht einmal geschrieben.
- Unterauftragnehmer (Hosting, Sentry, Stripe, SERP-Anbieter) sind gelistet, mit Serverstandort und Transfergrundlage. US-Anbieter nur mit geprüfter Grundlage.

**G2. Einwilligung pro Integration**

- **Zweckbindung schriftlich pro Integration**, granular widerrufbar. Eine Einwilligung für GA4 ist keine für Shopify.
- OAuth-Scopes minimal: nur was eine konkrete Kennzahl braucht. Ein zusätzlicher Scope braucht eine Begründung im PR und einen Eintrag im Register.
- Einwilligungen werden mit Zeitpunkt, Fassung und Umfang in `consents` protokolliert; die Fassung des Textes ist versioniert.

**G3. Löschung und Widerruf**

- **Trennen löscht nachweislich.** Rohdaten aus einer widerrufenen Verbindung werden innerhalb von 30 Tagen gelöscht, der Löschlauf ist protokolliert und getestet.
- Widerruf entfernt die Daten auch aus Trainingsbeständen und löst ein dokumentiertes Retraining aus (E2).
- Kontolöschung ist im Produkt möglich, nicht nur per Support-Mail. Datenexport (Art. 15/20) ebenfalls.
- Aggregierte, anonyme Kennzahlen dürfen bleiben — **nur wenn die k-Schwelle eingehalten ist** (G4).

**G4. Benchmarks und Rückrechenbarkeit**

- **Benchmark-Aggregate erst ab k ≥ 20 Shops.** Die Schwelle steht als Konstante im Code, ist getestet und wird nicht pro Ansicht gelockert.
- Zusätzlich gilt: Kein Aggregat, in dem ein einzelner Shop mehr als einen definierten Anteil ausmacht — sonst ist die k-Schwelle formal erfüllt und die Zahl trotzdem rückrechenbar.
- Filterkombinationen (Branche × Größe × Land) sind der eigentliche Angriffspfad: Die Schwelle wird **nach** Anwendung aller Filter geprüft, nicht davor.
- Kein Benchmark, der einen benannten Wettbewerber identifizierbar macht, auch nicht implizit über eine Ein-Element-Kategorie.

**G5. Fremde Daten**

- Gecrawlte Inhalte sind fremdes Material. Nutzungsbedingungen und Lizenzlage stehen pro Quelle in `docs/datenquellen.md`.
- Ein maschinenlesbarer Nutzungsvorbehalt für die eigene Domain gehört in `robots.txt` **und** in die Rechtstexte.
- Bei Clickstream-Plänen später: dediziertes Panel mit echter Einwilligung, nie heimlich, nie über eine Browser-Erweiterung ohne klare Aufklärung.

---

# Anhang — Häufige Fehler, die hier nicht passieren dürfen

| Fehler | Warum er falsch ist |
|---|---|
| Schätzwert als Punktzahl anzeigen | E3, Spanne ist Pflicht |
| Konfidenz-Badge weglassen, „damit die Zeile ruhiger wirkt" | A4/A8, das ist die Kernzusage des Produkts |
| Export ohne Herkunftsspalten | A8, die Zahl landet kontextlos in einer Präsentation |
| Fehlende Daten als `0` rendern | A4, sieht aus wie ein Einbruch beim Wettbewerber |
| Fixture-Fallback im Produktionspfad | A4/A9, erfundene Zahlen im Echtbetrieb |
| Hex-Wert direkt in der Komponente | A5 |
| `--ocker` als Textfarbe | 3,0:1 auf `zinn`, unter AA |
| Serie A/B nur über Farbe unterscheiden | A5, Luminanzabstand 1,2:1 — in Graustufen identisch |
| Siebte Schriftgröße „nur hier einmal" | A6, Skala ist geschlossen |
| Chart-Farben aus ECharts-Defaults | A5/Teil B |
| `fetch` auf eine externe API direkt in einer Komponente | A9 |
| Neue Query ohne `organization_id`-Filter | A12, Mandantenleck |
| Crawler folgt einer Nutzer-URL ohne SSRF-Prüfung | A12 |
| Gecrawlten Shoptitel ungefiltert rendern | A12, Fremdinhalt ist unvertrauenswürdig |
| Bot-Schutz umgehen, um an Daten zu kommen | D1, kostet das Produkt |
| Crawl ohne Kontakt-URL im User-Agent | D1 |
| Teilbestand nach fehlgeschlagenem ETL-Lauf laden | D3, erzeugt falsche Zeitreihen |
| CrUX-Lücke bei kleinen Shops als „wenig Traffic" darstellen | D3, Abdeckungsgrenze ≠ Messergebnis |
| Konfidenzintervall verengen, damit es souveräner aussieht | E3, schwerster Verstoß in diesem Dokument |
| Modellversion nicht im Cache-Schlüssel | Teil C, mischt zwei Modellstände in einer Ansicht |
| MAPE-Verschlechterung im Mittelwert verstecken | E2 |
| Gespeicherter Vergleich zeigt heute andere Zahlen | A10, Reproduzierbarkeit |
| OAuth-Token in einem Log oder Sentry-Event | A11, Merge-Blocker |
| Benchmark unter k = 20 ausspielen | G4, einzelne Shops rückrechenbar |
| k-Schwelle vor statt nach den Filtern prüfen | G4, der eigentliche Angriffspfad |
| Widerruf löscht die UI-Anzeige, nicht die Rohdaten | G3 |
| Leerer `catch`, stiller Abbruch | F2 |
| Ausfall einer Quelle killt die ganze Ansicht | F2, Teil-Verfügbarkeit ist der Normalfall |
| `outline: none` ohne Ersatz-Fokusring | F6 |
| Deltabalken ohne Textäquivalent | F6 |
| Performance-Regression „später beheben" | F1, Budget ist ein Gate |
| Kontrastwerte nach Farbänderung nicht neu berechnet | A5, Merge-Blocker |
| Produktname im Code, Repo-Name in der UI | A2 |
