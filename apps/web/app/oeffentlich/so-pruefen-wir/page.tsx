export const metadata = { title: "So prüfen wir – luibui" };

const EBENEN: [string, string][] = [
  ["A – Dateien", "Automatisch startende Befehle (Hooks, Installationsskripte, Python-Startdateien, Dev Container), Programmdateien, getarnte Dateitypen, Modelldateien, die beim Laden Code ausführen, aktive Inhalte in PDF- und Office-Dateien, fremde Paketquellen."],
  ["B – Inhalte", "Unsichtbare Unicode-Zeichen, versteckter und kodierter Text, Anweisungen an das Sprachmodell wie Datenabfluss oder Geheimhaltung vor dem Nutzer, auch wenn sie kodiert versteckt sind."],
  ["Secrets", "Echte Zugangsdaten und Schlüsseldateien im Paket. Im Bericht nie im Klartext."],
  ["D – Abhängigkeiten", "Bekannte Schwachstellen und Schadpakete (OSV-Datenbank, offline), Namensverwechslungen, fehlende Lockfiles, Downloads ohne Prüfsumme."],
  ["E – MCP-Konfiguration", "Startbefehle, die ungeprüft Pakete nachladen, unverschlüsselte Verbindungen und zu weit gefasste Werkzeugrechte."],
  ["C, E, G – folgen", "Die vollständige Code-Analyse, die Prüfung von MCP-Servern im Code und der DSGVO-Abgleich mit dem Manifest folgen. Bis dahin ist eine gründliche Prüfung höchstens Gelb. Personenbezogene Daten und Standortdaten in Dateien werden schon jetzt gemeldet."],
];

export default function SoPruefenWir() {
  return (
    <article className="flex max-w-3xl flex-col gap-6 pt-6">
      <h1 className="font-display text-4xl font-bold">So prüfen wir</h1>
      <p className="text-lg text-ink-2">
        Jede Eingabe gilt als feindlich. Wir lesen und analysieren, führen aber nie etwas aus dem Paket aus. Die
        Prüfung läuft in einem Prozess ohne Internetzugang.
      </p>
      <ul className="flex flex-col gap-3">
        {EBENEN.map(([titel, text]) => (
          <li key={titel} className="rounded-[14px] border border-linie bg-surface p-5">
            <h2 className="font-semibold">{titel}</h2>
            <p className="mt-1 text-sm text-ink-2">{text}</p>
          </li>
        ))}
      </ul>
      <h2 className="font-display text-2xl font-bold">Ehrlich bewerten</h2>
      <ul className="list-disc pl-6 text-ink-2">
        <li>Grün heißt „keine bekannten Befunde“, nie „sicher“.</li>
        <li>Fehlt eine Prüfung oder schlägt sie fehl, ist das Ergebnis höchstens Gelb.</li>
        <li>Ein Sprachmodell allein entscheidet nie über Grün oder eine Sperre.</li>
        <li>Jeder Befund nennt Regel, Datei, Zeile und Beleg.</li>
      </ul>
    </article>
  );
}
