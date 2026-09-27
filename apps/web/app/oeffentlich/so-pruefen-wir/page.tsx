export const metadata = { title: "So prüfen wir – luibui" };

const EBENEN: [string, string][] = [
  ["A – Dateien", "Automatisch startende Befehle, Installationsskripte, Programmdateien, getarnte Dateitypen, fremde Paketquellen, bekannte Schadsoftware."],
  ["B – Inhalte", "Unsichtbare Unicode-Zeichen, versteckter Text, kodierte Blöcke, Anweisungen an das Sprachmodell wie Datenabfluss oder Geheimhaltung vor dem Nutzer."],
  ["Secrets", "Echte Zugangsdaten im Paket, gefunden mit gitleaks. Im Bericht nie im Klartext."],
  ["D – Abhängigkeiten", "Bekannte Schwachstellen und Schadpakete (OSV-Datenbank, offline), Namensverwechslungen, fehlende Lockfiles."],
  ["C, E, G", "Code-Analyse, MCP-Prüfungen und DSGVO-Abgleich mit dem Manifest folgen. Bis dahin ist eine gründliche Prüfung höchstens Gelb."],
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
