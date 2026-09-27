import { Ampel } from "@/components/Ampel";
import { appUrl } from "@/lib/hosts";

import { Schnellscan } from "./Schnellscan";

const SCHRITTE = [
  ["Hochladen", "Datei, Ordner, ZIP, Text oder ein Git-Repository. Jede Eingabe gilt als feindlich und wird nur gelesen."],
  ["Prüfen", "Versteckte Anweisungen, automatisch startende Befehle, Secrets, Abhängigkeiten mit bekannten Lücken und mehr."],
  ["Beheben", "Jeder Befund mit Datei, Zeile, Beleg und einem fertigen Prompt für deinen Coding-Agent."],
];

const ZAHLEN: [string, string, string][] = [
  ["36,8 %", "der untersuchten Skills mit mindestens einer Sicherheitslücke", "1"],
  ["13,4 %", "mit einer kritischen Lücke – mehr als jeder achte", "1"],
  ["82 %", "der untersuchten MCP-Server mit Dateizugriffen, die für Zugriff außerhalb des erlaubten Bereichs anfällig sind", "2"],
];

const QUELLEN: [string, string, string][] = [
  ["1", "Snyk, „ToxicSkills“, Februar 2026: 3.984 Skills aus ClawHub und skills.sh.", "https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/"],
  ["2", "Endor Labs, 2026: 2.614 MCP-Implementierungen, Path Traversal (CWE-22).", "https://www.endorlabs.com/learn/classic-vulnerabilities-meet-ai-infrastructure-why-mcp-needs-appsec"],
];

const KIS = ["Claude", "ChatGPT", "Gemini", "Mistral", "Open WebUI", "MCP-Clients"];

const ARTEN: [string, string[]][] = [
  ["Skills", ["Versteckte Anweisungen an das Sprachmodell", "Unsichtbare Unicode-Zeichen", "Links, über die Daten abfließen"]],
  ["Plugins", ["Hooks, die Befehle automatisch starten", "Installationsskripte", "Programmdateien ohne Quellcode"]],
  ["Tools", ["Zugangsdaten im Code", "Abhängigkeiten mit bekannten Lücken", "Pakete aus fremden Quellen"]],
  ["MCP-Server", ["Startbefehle in der MCP-Konfiguration", "Namensverwechslungen bei Paketen", "Fehlende Lockfiles"]],
];

const AMPELN: [string, string][] = [
  ["gruen", "Keine bekannten Befunde. Heißt nicht „sicher“, sondern: Wir haben nichts gefunden."],
  ["gelb", "Etwas sollte geprüft werden, oder nicht alle Prüfungen konnten laufen."],
  ["rot", "Mindestens ein ernster Befund."],
  ["gesperrt", "Ein kritischer Befund aus der Sperrliste, etwa versteckte Anweisungen oder echte Zugangsdaten."],
];

export default async function Startseite() {
  const registrieren = await appUrl("/registrieren");
  return (
    <div className="flex flex-col gap-16">
      <section className="grid gap-10 pt-10 lg:grid-cols-[1.1fr_1fr] lg:items-center">
        <div>
          <p className="text-sm font-semibold text-petrol">Offen · Kostenlos · Gehostet in Deutschland</p>
          <h1 className="mt-3 font-display text-5xl font-bold leading-tight sm:text-6xl">
            Prüfen, bevor man installiert.
          </h1>
          <p className="mt-5 max-w-xl text-lg text-ink-2">
            luibui prüft KI-Skills, Plugins, Tools und MCP-Server auf Sicherheit und Datenschutz. Du bekommst einen
            Bericht mit zwei Ampeln, einer Note und konkreten Hinweisen zum Beheben.
          </p>
          <a
            href={registrieren}
            className="mt-6 inline-block rounded-[10px] bg-petrol px-5 py-3 font-semibold text-white hover:bg-petrol-dunkel"
          >
            Kostenlos registrieren und gründlich prüfen
          </a>
        </div>
        <Schnellscan />
      </section>

      <section aria-labelledby="lage" className="rounded-[14px] bg-ink p-8 text-white sm:p-10">
        <h2 id="lage" className="max-w-3xl font-display text-3xl font-bold sm:text-4xl">
          Mehr als jeder dritte KI-Skill hat eine Sicherheitslücke.
        </h2>
        <dl className="mt-8 grid gap-6 md:grid-cols-3">
          {ZAHLEN.map(([zahl, text, quelle]) => (
            <div key={zahl}>
              <dt className="font-display text-5xl font-bold">
                {zahl}
                <sup className="ml-1 text-lg font-normal">{quelle}</sup>
              </dt>
              <dd className="mt-2 text-sm text-white/80">{text}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-8 max-w-3xl text-lg">
          Skills und Plugins sehen harmlos aus und laufen mit Zugriff auf deine Chats, Dateien und Zugangsdaten. luibui
          prüft sie, bevor du sie installierst.
        </p>
        <ol className="mt-6 flex flex-col gap-1 text-xs text-white/70">
          {QUELLEN.map(([nr, text, url]) => (
            <li key={nr}>
              {nr} {text}{" "}
              <a href={url} className="underline hover:text-white" rel="noopener noreferrer">
                Quelle
              </a>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="umfang">
        <h2 id="umfang" className="font-display text-3xl font-bold">
          Was luibui prüft
        </h2>
        <p className="mt-3 max-w-3xl text-ink-2">
          Erweiterungen für {KIS.slice(0, -1).join(", ")} und {KIS[KIS.length - 1]}. Einige Beispiele:
        </p>
        <ul className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {ARTEN.map(([art, beispiele]) => (
            <li key={art} className="rounded-[14px] border border-linie bg-surface p-6">
              <h3 className="text-lg font-semibold">{art}</h3>
              <ul className="mt-3 flex list-disc flex-col gap-1 pl-5 text-sm text-ink-2">
                {beispiele.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="ablauf">
        <h2 id="ablauf" className="font-display text-3xl font-bold">
          In drei Schritten
        </h2>
        <ol className="mt-6 grid gap-4 md:grid-cols-3">
          {SCHRITTE.map(([titel, text], i) => (
            <li key={titel} className="rounded-[14px] border border-linie bg-surface p-6">
              <p className="font-mono text-sm text-petrol">0{i + 1}</p>
              <h3 className="mt-2 text-lg font-semibold">{titel}</h3>
              <p className="mt-2 text-sm text-ink-2">{text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="ampel">
        <h2 id="ampel" className="font-display text-3xl font-bold">
          Was die Ampel bedeutet
        </h2>
        <ul className="mt-6 grid gap-4 md:grid-cols-2">
          {AMPELN.map(([wert, text]) => (
            <li key={wert} className="flex items-start gap-4 rounded-[14px] border border-linie bg-surface p-5">
              <Ampel wert={wert} />
              <p className="text-sm text-ink-2">{text}</p>
            </li>
          ))}
        </ul>
        <p className="mt-4 text-sm text-muted">Die Ampel ist ein automatischer Hinweis, keine Zertifizierung.</p>
      </section>
    </div>
  );
}
