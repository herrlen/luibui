import { Ampel } from "@/components/Ampel";
import { appUrl } from "@/lib/hosts";

import { Schnellscan } from "./Schnellscan";

const SCHRITTE = [
  ["Hochladen", "Datei, Ordner, ZIP- oder tar-Archiv, Text oder ein Git-Repository. Jede Eingabe gilt als feindlich und wird nur gelesen."],
  ["Prüfen", "Versteckte Anweisungen, automatisch startende Befehle, Secrets, Abhängigkeiten mit bekannten Lücken und mehr."],
  ["Beheben", "Jeder Befund mit Datei, Zeile, Beleg und einem fertigen Prompt für deinen Coding-Agent."],
];

const ZAHLEN: [string, string][] = [
  ["36,8 %", "der untersuchten Skills mit mindestens einer Sicherheitslücke"],
  ["13,4 %", "mit einer kritischen Lücke – mehr als jeder achte"],
  ["82 %", "der untersuchten MCP-Server mit Dateizugriffen, die für Zugriff außerhalb des erlaubten Bereichs anfällig sind"],
];

const KIS = ["Claude", "ChatGPT", "Gemini", "Mistral", "Open WebUI", "MCP-Clients"];

const ARTEN: [string, string[]][] = [
  ["Skills", ["Versteckte Anweisungen, auch kodiert", "Unsichtbare Unicode-Zeichen", "Links, über die Daten abfließen"]],
  ["Plugins", ["Hooks, die Befehle automatisch starten", "Zu weit gefasste Werkzeugrechte", "Programmdateien ohne Quellcode"]],
  ["Tools", ["Zugangsdaten und Schlüsseldateien", "Abhängigkeiten mit bekannten Lücken", "Modelldateien, die beim Laden Code ausführen"]],
  ["MCP-Server", ["Startbefehle, die ungeprüft Pakete nachladen", "Unsichtbare Zeichen in Tool-Beschreibungen", "Namensverwechslungen bei Paketen"]],
];

const AMPELN: [string, string][] = [
  ["gruen", "Keine bekannten Befunde. Heißt nicht „sicher“, sondern: Wir haben nichts gefunden."],
  ["gelb", "Etwas sollte geprüft werden, oder nicht alle Prüfungen konnten laufen."],
  ["rot", "Mindestens ein ernster Befund."],
  ["gesperrt", "Ein kritischer Befund aus der Sperrliste, etwa versteckte Anweisungen oder echte Zugangsdaten."],
];

const CHIPS = ["Offen", "Kostenlos", "Gehostet in Deutschland"];

const H2 = "font-display text-[32px] font-bold leading-[1.1] tracking-[-0.03em] sm:text-[40px]";

export default async function Startseite() {
  const anmelden = await appUrl("/anmelden");
  const registrieren = await appUrl("/registrieren");
  return (
    <div className="flex flex-col gap-20 lg:gap-24">
      <section className="grid items-center gap-12 pt-12 lg:grid-cols-2 lg:gap-[72px] lg:pb-20 lg:pt-[88px]">
        <div className="flex flex-col gap-7">
          <ul className="flex flex-wrap gap-2" aria-label="Kurz gesagt">
            {CHIPS.map((c) => (
              <li
                key={c}
                className="rounded-full border border-linie-stark px-3 py-1.5 text-[13px] font-medium text-chip-text"
              >
                {c}
              </li>
            ))}
          </ul>
          <h1 className="font-display text-[44px] font-bold leading-[1.02] tracking-[-0.035em] sm:text-6xl lg:text-[72px]">
            Prüfen, bevor man <span className="text-petrol">installiert.</span>
          </h1>
          <p className="max-w-[580px] text-[17px] leading-[1.6] text-ink-2 sm:text-[19px]">
            luibui prüft KI-Skills, Plugins, Tools und MCP-Server auf Sicherheit und Datenschutz. Du bekommst einen
            Bericht mit zwei Ampeln, einer Note und konkreten Hinweisen zum Beheben.
          </p>
          <a
            href={registrieren}
            className="inline-flex min-h-15 items-center self-start rounded-xl bg-petrol px-[26px] py-3 text-base font-semibold text-white hover:bg-petrol-dunkel"
          >
            Kostenlos registrieren und gründlich prüfen
          </a>
        </div>
        <Schnellscan />
      </section>

      <section aria-labelledby="lage" className="rounded-[18px] bg-band p-6 sm:p-10 lg:p-14">
        <h2 id="lage" className={`max-w-3xl ${H2}`}>
          Mehr als jeder dritte KI-Skill hat eine Sicherheitslücke.
        </h2>
        <dl className="mt-9 grid gap-5 md:grid-cols-3">
          {ZAHLEN.map(([zahl, text]) => (
            <div key={zahl} className="flex flex-col gap-3 rounded-[14px] bg-surface p-7">
              <dt className="font-display text-[56px] font-bold leading-none tracking-[-0.035em] text-petrol lg:text-[64px]">
                {zahl}
              </dt>
              <dd className="text-[15px] leading-[1.55] text-ink-2">{text}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-9 max-w-3xl text-[17px] leading-[1.6] text-ink-2">
          Skills und Plugins sehen harmlos aus und laufen mit Zugriff auf deine Chats, Dateien und Zugangsdaten. luibui
          prüft sie, bevor du sie installierst.
        </p>
      </section>

      <section aria-labelledby="umfang" className="flex flex-col gap-7">
        <h2 id="umfang" className={H2}>
          Was luibui prüft
        </h2>
        <div className="flex flex-col gap-4">
          <p className="max-w-3xl text-[17px] text-ink-2">Erweiterungen für diese KI-Anwendungen:</p>
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {KIS.map((ki) => (
              <li key={ki} className="rounded-xl border border-linie bg-flaeche-2 px-[18px] py-4 text-base font-semibold">
                {ki}
              </li>
            ))}
          </ul>
        </div>
        <p className="max-w-3xl text-[17px] text-ink-2">Einige Beispiele:</p>
        <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {ARTEN.map(([art, beispiele]) => (
            <li key={art} className="flex flex-col gap-3.5 rounded-[14px] border border-linie bg-surface p-6">
              <h3 className="self-start rounded-md bg-tag px-[9px] py-[3px] text-[13px] font-medium">{art}</h3>
              <ul className="flex flex-col gap-2 text-[15px] leading-[1.55] text-ink-2">
                {beispiele.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="ablauf" className="flex flex-col gap-7">
        <h2 id="ablauf" className={H2}>
          In drei Schritten
        </h2>
        <ol className="grid gap-5 md:grid-cols-3">
          {SCHRITTE.map(([titel, text], i) => (
            <li key={titel} className="flex flex-col gap-3.5 rounded-[14px] border border-linie bg-surface p-7">
              <div className="flex items-center gap-3">
                <span
                  aria-hidden="true"
                  className="flex size-[34px] shrink-0 items-center justify-center rounded-full bg-petrol font-semibold text-white"
                >
                  {i + 1}
                </span>
                <h3 className="text-xl font-semibold">{titel}</h3>
              </div>
              <p className="text-[15px] leading-[1.6] text-ink-2">{text}</p>
            </li>
          ))}
        </ol>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section
          aria-labelledby="ampel"
          className="flex flex-col gap-5 rounded-[18px] border border-linie bg-surface p-7 sm:p-9"
        >
          <h2 id="ampel" className="font-display text-[28px] font-bold tracking-[-0.02em] sm:text-[32px]">
            Was die Ampel bedeutet
          </h2>
          <ul className="flex flex-col gap-3.5">
            {AMPELN.map(([wert, text]) => (
              <li key={wert} className="flex items-start gap-3.5">
                <span className="w-[104px] shrink-0">
                  <Ampel wert={wert} />
                </span>
                <p className="text-[15px] leading-[1.55] text-ink-2">{text}</p>
              </li>
            ))}
          </ul>
          <p className="text-[13px] text-muted">Die Ampel ist ein automatischer Hinweis, keine Zertifizierung.</p>
        </section>

        <section
          aria-labelledby="gruendlich"
          className="flex flex-col gap-5 rounded-[18px] bg-petrol p-7 text-grund sm:p-9"
        >
          <h2 id="gruendlich" className="font-display text-[28px] font-bold tracking-[-0.02em] sm:text-[32px]">
            Gründlich prüfen im Entwicklerbereich
          </h2>
          <p className="text-base leading-[1.6] text-petrol-hell">
            Im Entwicklerbereich prüfst du Dateien, Ordner, ZIP- oder tar-Archive, eingefügten Text oder Git-Repositories.
            Projekte, Berichte und Verlauf liegen in deinem privaten Bereich und sind nur für dich sichtbar.
          </p>
          <div className="mt-auto flex flex-wrap gap-3">
            <a
              href={registrieren}
              className="inline-flex h-12 items-center rounded-[10px] bg-grund px-[22px] text-[15px] font-semibold text-petrol hover:bg-surface focus-visible:outline-grund"
            >
              Kostenlos registrieren
            </a>
            <a
              href={anmelden}
              className="inline-flex h-12 items-center rounded-[10px] border border-grund/50 px-[22px] text-[15px] font-semibold text-grund hover:border-grund focus-visible:outline-grund"
            >
              Anmelden
            </a>
          </div>
        </section>
      </div>
    </div>
  );
}
