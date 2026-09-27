import { Ampel } from "@/components/Ampel";
import { appUrl } from "@/lib/hosts";

import { Schnellscan } from "./Schnellscan";

const SCHRITTE = [
  ["Hochladen", "Datei, Ordner, ZIP, Text oder ein Git-Repository. Jede Eingabe gilt als feindlich und wird nur gelesen."],
  ["Prüfen", "Versteckte Anweisungen, automatisch startende Befehle, Secrets, Abhängigkeiten mit bekannten Lücken und mehr."],
  ["Beheben", "Jeder Befund mit Datei, Zeile, Beleg und einem fertigen Prompt für deinen Coding-Agent."],
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
