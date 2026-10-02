import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "So prüfen wir – luibui",
  description:
    "Wie luibui KI-Skills, Plugins und MCP-Server prüft: acht Prüfebenen, nichts wird ausgeführt, Ampeln und Note nach festen Regeln.",
  alternates: { canonical: "/so-pruefen-wir" },
};

const EBENEN: [string, string][] = [
  [
    "Dateien",
    "Automatisch startende Befehle (Hooks, Installationsskripte, Python-Startdateien, Dev Container), Programmdateien ohne Quellcode, getarnte Dateitypen, Modelldateien, die beim Laden Code ausführen, aktive Inhalte in PDF- und Office-Dateien, fremde Paketquellen und bekannte Schadsoftware.",
  ],
  [
    "Inhalte",
    "Unsichtbare Unicode-Zeichen, versteckter und kodierter Text, Anweisungen an das Sprachmodell wie Datenabfluss oder Geheimhaltung vor dem Nutzer, auch wenn sie kodiert versteckt sind.",
  ],
  ["Secrets", "Echte Zugangsdaten und Schlüsseldateien im Paket. Im Bericht nie im Klartext."],
  [
    "Code",
    "Skripte und Serverquellcode in Python, JavaScript/TypeScript und Shell: Befehlsausführung, nachgeladener Code, Datenabfluss, Dateizugriffe ohne Grenze. Grundmuster auch für Go, Ruby, PHP, Rust, Java, C# und PowerShell. Wird eine Datei aus einer Anleitung heraus aufgerufen, wiegt ein Befund dort schwerer.",
  ],
  [
    "Abhängigkeiten",
    "Bekannte Schwachstellen und Schadpakete aus der OSV-Datenbank, offline abgefragt, dazu Namensverwechslungen, fehlende Lockfiles und Downloads ohne Prüfsumme.",
  ],
  [
    "MCP-Server",
    "Tool-Namen, Beschreibungen und Parameter werden aus dem Code gelesen und wie Anleitungen geprüft, ohne den Server zu starten. Dazu Startbefehle, die ungeprüft Pakete nachladen, fehlende Anmeldung, offene CORS-Regeln und weitergereichte Tokens.",
  ],
  [
    "DSGVO und Rechte",
    "Welche Dienste das Paket anspricht und in welchem Land sie stehen, abgeglichen mit Angemessenheitsbeschlüssen der EU. Mit Manifest auch: Stimmen die angegebenen Rechte und Endpunkte mit dem Code überein? Personenbezogene Daten in Dateien werden gemeldet.",
  ],
];

const UMFANG: [string, string, string[]][] = [
  [
    "Schnellscan",
    "Auf dieser Website, ohne Anmeldung, ohne Gewähr.",
    [
      "Eine Datei oder ein ZIP bis 2 MB oder ein öffentliches Repository",
      "Dateien, Inhalte, Secrets und Abhängigkeiten",
      "Nichts wird gespeichert, der Bericht ist 7 Tage abrufbar",
    ],
  ],
  [
    "Gründliche Prüfung",
    "Im Entwicklerbereich, nach der Registrierung.",
    [
      "Dateien, Ordner, ZIP- oder tar-Archive, Text oder Git-Repositories (GitHub, GitLab, Codeberg)",
      "Alle Prüfebenen einschließlich Code, MCP und DSGVO",
      "Verlauf, Vergleich zweier Prüfungen, Befund-Status, PDF, CSV und SARIF",
    ],
  ],
];

const SCHWERE: [string, string, string][] = [
  ["Kritisch", "−40", "Rot; auf der Sperrliste: Gesperrt"],
  ["Hoch", "−15", "Rot"],
  ["Mittel", "−5", "Gelb"],
  ["Niedrig", "−1", "bleibt Grün"],
  ["Info", "0", "bleibt Grün"],
];

const H2 = "font-display text-2xl font-bold";

export default function SoPruefenWir() {
  return (
    <article className="flex max-w-3xl flex-col gap-6 pt-6">
      <h1 className="font-display text-4xl font-bold">So prüfen wir</h1>
      <p className="text-lg text-ink-2">
        Jede Eingabe gilt als feindlich. Wir lesen und analysieren, führen aber nie etwas aus dem Paket aus: kein
        Installieren, kein Starten, kein Importieren. Die Prüfung läuft in einem Prozess ohne Internetzugang.
      </p>

      <h2 className={H2}>Was geprüft wird</h2>
      <ul className="flex flex-col gap-3">
        {EBENEN.map(([titel, text]) => (
          <li key={titel} className="rounded-[14px] border border-linie bg-surface p-5">
            <h3 className="font-semibold">{titel}</h3>
            <p className="mt-1 text-sm text-ink-2">{text}</p>
          </li>
        ))}
      </ul>
      <p className="text-sm text-muted">
        Noch nicht dabei: das Ausführen in einer abgeschotteten Umgebung und eine zusätzliche Prüfung durch ein
        Sprachmodell. Beides kommt später und kann nur Befunde hinzufügen, nie ein Paket grün machen.
      </p>

      <h2 className={H2}>Schnellscan und gründliche Prüfung</h2>
      <div className="grid gap-4 sm:grid-cols-2">
        {UMFANG.map(([titel, wo, punkte]) => (
          <section key={titel} className="flex flex-col gap-2 rounded-[14px] border border-linie bg-surface p-5">
            <h3 className="font-semibold">{titel}</h3>
            <p className="text-sm text-muted">{wo}</p>
            <ul className="list-disc pl-5 text-sm text-ink-2">
              {punkte.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      <h2 className={H2}>Wie bewertet wird</h2>
      <p className="text-ink-2">
        Es gibt zwei Ampeln, eine für Sicherheit und eine für die DSGVO, und eine Gesamtbewertung, die der schlechteren
        folgt. Die Note beginnt bei 100; jeder Befund zieht nach seiner Schwere ab, mindestens bleibt 0.
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-muted">
            <tr>
              <th scope="col" className="py-2 pr-4 font-medium">
                Schwere
              </th>
              <th scope="col" className="py-2 pr-4 font-medium">
                Note
              </th>
              <th scope="col" className="py-2 font-medium">
                Ampel Sicherheit
              </th>
            </tr>
          </thead>
          <tbody>
            {SCHWERE.map(([schwere, abzug, ampel]) => (
              <tr key={schwere} className="border-t border-linie">
                <td className="py-2 pr-4 font-medium">{schwere}</td>
                <td className="py-2 pr-4 tabular-nums">{abzug}</td>
                <td className="py-2 text-ink-2">{ampel}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-ink-2">
        Die DSGVO-Ampel wird nur für Pakete mit Manifest vergeben. Ohne Manifest bleibt sie „nicht bewertet“, es sei
        denn, ein Befund färbt sie ein, etwa ein Dienst in einem Land ohne Angemessenheitsbeschluss.
      </p>

      <h2 className={H2}>Ehrlich bewerten</h2>
      <ul className="list-disc pl-6 text-ink-2">
        <li>Grün heißt „keine bekannten Befunde“, nie „sicher“.</li>
        <li>Fehlt eine Prüfung oder schlägt sie fehl, ist das Ergebnis höchstens Gelb.</li>
        <li>Ein Sprachmodell allein entscheidet nie über Grün oder eine Sperre.</li>
        <li>Jeder Befund nennt Regel, Datei, Zeile, Beleg und einen Vorschlag zum Beheben.</li>
        <li>
          Wer einen Befund für falsch hält, kann ihn im Entwicklerbereich mit Begründung bestreiten. Ampel und Note
          ändern sich dadurch nicht; bestätigte Fehlalarme führen zu angepassten Regeln.
        </li>
      </ul>

      <h2 className={H2}>Was mit deinen Dateien passiert</h2>
      <ul className="list-disc pl-6 text-ink-2">
        <li>Gehostet in Deutschland, ohne US-Dienste, ohne Tracking.</li>
        <li>Der Arbeitsordner einer Prüfung wird danach gelöscht, auch bei Abbruch.</li>
        <li>
          Projekt-Dateien im Entwicklerbereich liegen verschlüsselt, mit einem eigenen Schlüssel je Projekt, bis du sie
          löschst. Auf Wunsch werden sie direkt nach der Prüfung gelöscht.
        </li>
        <li>Bekannte Schadsoftware wird nie abgelegt.</li>
      </ul>
    </article>
  );
}
