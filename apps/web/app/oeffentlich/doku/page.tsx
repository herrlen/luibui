import type { Metadata } from "next";
import Link from "next/link";

import { appUrl } from "@/lib/hosts";

export const metadata: Metadata = {
  title: "Doku – luibui",
  description:
    "Erste Schritte mit luibui: Schnellscan, Registrierung, Hochladen, den Prüfbericht lesen, Befunde bearbeiten und das Manifest luibui.json.",
  alternates: { canonical: "/doku" },
};

const EINGABEN: [string, string][] = [
  ["Einzelne Datei", "bis 10 MB"],
  ["Mehrere Dateien oder ein Ordner", "bis 1.000 Dateien und 50 MB zusammen"],
  ["ZIP- oder tar-Archiv", "bis 50 MB gepackt, 200 MB entpackt, 10.000 Dateien"],
  ["Eingefügter Text", "bis 200 KB, etwa eine SKILL.md"],
  ["Git-Repository", "öffentlich, von GitHub, GitLab oder Codeberg"],
];

const DOWNLOADS: [string, string][] = [
  ["PDF", "als Standard oder mit allen Details, zum Weitergeben oder Ablegen."],
  ["CSV", "eine Zeile je Befund, für Excel und LibreOffice."],
  ["JSON", "der vollständige Bericht zum Weiterverarbeiten."],
  ["SARIF", "für GitHub Code Scanning und andere Werkzeuge; akzeptierte Befunde sind als unterdrückt markiert."],
];

const MANIFEST = `{
  "schema_version": "1",
  "name": "beispiel/wetter-skill",
  "version": "1.0.0",
  "typ": "skill",
  "beschreibung": "Zeigt die Wettervorhersage für einen Ort.",
  "lizenz": "MIT",
  "einstieg": "SKILL.md",
  "rechte": {
    "netzwerk": true,
    "dateien": { "lesen": [], "schreiben": [] },
    "shell": false,
    "zugangsdaten": false,
    "umgebungsvariablen": []
  },
  "endpunkte": [
    {
      "host": "api.wetter.example",
      "zweck": "Vorhersage abrufen",
      "land": "DE",
      "datenkategorien": ["nutzereingaben", "standortdaten"],
      "rechtsgrundlage": "keine_uebermittlung"
    }
  ],
  "datenkategorien": ["nutzereingaben", "standortdaten"],
  "speicherung": { "lokal": false, "dauer": "keine" }
}`;

const H2 = "font-display text-2xl font-bold";
const LINK = "font-medium text-petrol underline underline-offset-2 hover:text-petrol-dunkel";

export default async function Doku() {
  const registrieren = await appUrl("/registrieren");
  return (
    <article className="flex max-w-3xl flex-col gap-6 pt-6">
      <h1 className="font-display text-4xl font-bold">Doku</h1>
      <p className="text-lg text-ink-2">
        Alles, was du für deine erste Prüfung brauchst. Wie wir prüfen und bewerten, steht unter{" "}
        <Link href="/so-pruefen-wir" className={LINK}>
          So prüfen wir
        </Link>
        .
      </p>
      <nav aria-label="Inhalt dieser Seite">
        <ol className="list-decimal pl-6 text-ink-2">
          <li>
            <a href="#schnellscan" className={LINK}>
              Schnellscan
            </a>
          </li>
          <li>
            <a href="#start" className={LINK}>
              Registrieren und erstes Projekt
            </a>
          </li>
          <li>
            <a href="#bericht" className={LINK}>
              Den Bericht lesen
            </a>
          </li>
          <li>
            <a href="#befunde" className={LINK}>
              Befunde bearbeiten und vergleichen
            </a>
          </li>
          <li>
            <a href="#manifest" className={LINK}>
              Das Manifest luibui.json
            </a>
          </li>
        </ol>
      </nav>

      <section aria-labelledby="schnellscan" className="flex flex-col gap-3">
        <h2 id="schnellscan" className={H2}>
          1. Schnellscan
        </h2>
        <p className="text-ink-2">
          Auf der{" "}
          <Link href="/" className={LINK}>
            Startseite
          </Link>{" "}
          eine Datei oder ein ZIP bis 2 MB hochladen oder die Adresse eines öffentlichen Repositorys eingeben. Nach
          wenigen Sekunden steht der Bericht da, 7 Tage lang unter seinem Link. Der Schnellscan prüft Dateien, Inhalte,
          Secrets und Abhängigkeiten, nicht den Code und nicht die DSGVO, und gilt ausdrücklich ohne Gewähr. Gespeichert
          wird nichts außer dem Bericht.
        </p>
      </section>

      <section aria-labelledby="start" className="flex flex-col gap-3">
        <h2 id="start" className={H2}>
          2. Registrieren und erstes Projekt
        </h2>
        <p className="text-ink-2">
          Nach der{" "}
          <a href={registrieren} className={LINK}>
            Registrierung
          </a>{" "}
          und der Bestätigung deiner E-Mail-Adresse hast du ein Projekt und drei Prüfungen frei. Weitere Prüfungen gibt
          es als Guthaben: 10 für 4,90 € oder 25 für 9,90 €, kein Abo.
        </p>
        <p className="text-ink-2">
          Ein Projekt ist ein Skill, Plugin, Tool oder MCP-Server. Lege es an und lade eine Version hoch:
        </p>
        <ul className="flex flex-col divide-y divide-linie rounded-[14px] border border-linie bg-surface">
          {EINGABEN.map(([art, grenze]) => (
            <li key={art} className="flex flex-wrap justify-between gap-x-4 gap-y-1 px-5 py-3 text-sm">
              <span className="font-medium">{art}</span>
              <span className="text-ink-2">{grenze}</span>
            </li>
          ))}
        </ul>
        <p className="text-ink-2">
          Archive werden nur gelesen, nie ausgeführt. Symbolische Links, absolute Pfade und Pfade mit „..“ werden
          abgelehnt. Für eine einzelne Datei ohne Projekt gibt es auf der Übersicht „Schnell prüfen, ohne Projekt“.
        </p>
      </section>

      <section aria-labelledby="bericht" className="flex flex-col gap-3">
        <h2 id="bericht" className={H2}>
          3. Den Bericht lesen
        </h2>
        <p className="text-ink-2">
          Oben stehen die Ampeln für Sicherheit und DSGVO, die Gesamtbewertung und die Note von 0 bis 100. Darunter die
          Befunde, die schwersten zuerst. Jeder Befund nennt die Datei, die Zeile, einen kurzen Beleg (Zugangsdaten
          gekürzt), eine Erklärung, einen Vorschlag zum Beheben und einen fertigen Prompt für deinen Coding-Agent. Ganz
          unten steht, was geprüft wurde und was nicht.
        </p>
        <p className="text-ink-2">Herunterladen kannst du den Bericht als:</p>
        <ul className="list-disc pl-6 text-ink-2">
          {DOWNLOADS.map(([format, text]) => (
            <li key={format}>
              <span className="font-medium text-ink">{format}</span> {text}
            </li>
          ))}
        </ul>
        <p className="text-ink-2">Über „Teilen“ erzeugst du einen Link, den du jederzeit wieder zurückziehen kannst.</p>
      </section>

      <section aria-labelledby="befunde" className="flex flex-col gap-3">
        <h2 id="befunde" className={H2}>
          4. Befunde bearbeiten und vergleichen
        </h2>
        <p className="text-ink-2">
          Einen Befund kannst du mit Begründung akzeptieren, etwa weil das Verhalten gewollt ist, oder bestreiten, wenn
          du ihn für einen Fehlalarm hältst. Bestrittene Befunde sieht sich die Moderation an. Ist ein Befund in einer
          neuen Version mit gleichem Prüfumfang verschwunden, steht er automatisch auf „behoben“. Ampel und Note
          bleiben davon unberührt.
        </p>
        <p className="text-ink-2">
          Ab der zweiten Prüfung zeigt die Projektseite den Verlauf von Note und Befunden. Zwei Prüfungen lassen sich
          vergleichen: neue, behobene und unveränderte Befunde.
        </p>
      </section>

      <section aria-labelledby="manifest" className="flex flex-col gap-3">
        <h2 id="manifest" className={H2}>
          5. Das Manifest luibui.json
        </h2>
        <p className="text-ink-2">
          Mit einer Datei <code className="font-mono text-sm">luibui.json</code> im Hauptordner sagst du, was dein Paket
          darf und mit wem es spricht. Nur dann wird die DSGVO-Ampel vergeben, und wir prüfen, ob Code und Angaben
          zusammenpassen: Spricht der Code einen Dienst an, der nicht im Manifest steht, ist das ein Befund.
        </p>
        <pre className="overflow-x-auto rounded-[14px] border border-linie bg-flaeche-2 p-5 font-mono text-[13px] leading-[1.55]">
          {MANIFEST}
        </pre>
        <ul className="list-disc pl-6 text-ink-2">
          <li>
            <span className="font-medium text-ink">typ</span>: skill, mcp-server, plugin oder tool.
          </li>
          <li>
            <span className="font-medium text-ink">lizenz</span>: ein SPDX-Ausdruck wie MIT oder Apache-2.0.
          </li>
          <li>
            <span className="font-medium text-ink">endpunkte</span>: alle Hosts, mit denen das Paket spricht, mit Zweck,
            Land und den übermittelten Daten. Leer, wenn <span className="font-mono text-sm">netzwerk</span> false ist.
          </li>
        </ul>
      </section>
    </article>
  );
}
