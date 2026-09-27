import { KONTAKT, Rechtstext, Zeilen } from "./Rechtstext";

// Every statement here must match the code (apps/api, apps/worker). When the processing changes,
// this text changes in the same commit.
export function Datenschutz() {
  const mail = <a href={`mailto:${KONTAKT}`}>{KONTAKT}</a>;
  return (
    <Rechtstext titel="Datenschutzerklärung" stand="27. September 2026">
      <section>
        <h2>1. Verantwortlicher</h2>
        <p>
          Len Messerschmidt
          <br />
          Norderreihe 21
          <br />
          22767 Hamburg
          <br />
          E-Mail: {mail}
        </p>
      </section>

      <section>
        <h2>2. Für welche Angebote diese Erklärung gilt</h2>
        <ul>
          <li>
            <strong>luibui.com</strong> – die öffentliche Seite mit dem Schnellscan. Dafür brauchst du kein Konto.
          </li>
          <li>
            <strong>app.luibui.com</strong> – der Entwicklerbereich mit Konto, Projekten, Dateien und Berichten.
          </li>
          <li>
            <strong>api.luibui.com</strong> – die Schnittstelle für Kommandozeile und CI, nur mit API-Token.
          </li>
        </ul>
        <p>Wer nur den Schnellscan nutzt, den betreffen die Abschnitte 5 und 6 nicht.</p>
      </section>

      <section>
        <h2>3. Aufruf der Seiten</h2>
        <p>
          Beim Ausliefern der Seiten verarbeitet unser Hoster technisch notwendige Verbindungsdaten wie IP-Adresse,
          Zeitpunkt und aufgerufene Adresse. Grundlage ist unser berechtigtes Interesse am sicheren Betrieb (Art. 6
          Abs. 1 lit. f DSGVO). luibui selbst schreibt keine Zugriffsprotokolle.
        </p>
        <p>
          Es gibt keine Reichweitenmessung, keine Werbung und kein Tracking. Schriften und alle anderen Bestandteile
          liefern wir selbst aus; dein Browser lädt nichts von fremden Servern.
        </p>
      </section>

      <section>
        <h2>4. Schnellscan ohne Konto</h2>
        <Zeilen
          zeilen={[
            [
              "Adresse des Repositorys",
              "Um das öffentliche Repository zu prüfen, das du angibst. Unser Server lädt es dafür bei GitHub, Codeberg oder GitLab herunter. Grundlage: Nutzungsverhältnis auf deine Anfrage (Art. 6 Abs. 1 lit. b DSGVO).",
            ],
            [
              "Inhalt des Repositorys",
              "Wird nur für die Dauer der Prüfung in einem eigenen Arbeitsordner abgelegt und danach gelöscht. Nichts daraus wird ausgeführt.",
            ],
            [
              "Bericht",
              "Wird 7 Tage gespeichert, damit du ihn über den Link abrufen kannst, und danach automatisch gelöscht. Er enthält Dateinamen und kurze Ausschnitte aus dem Repository, keine Angaben zu dir.",
            ],
            [
              "IP-Adresse",
              "Um Missbrauch zu begrenzen (höchstens drei Schnellscans pro Tag). Grundlage: berechtigtes Interesse (Art. 6 Abs. 1 lit. f DSGVO). Die Adresse liegt nur im Arbeitsspeicher, wird nicht in eine Datei oder Datenbank geschrieben und nach 24 Stunden verworfen.",
            ],
          ]}
        />
      </section>

      <section>
        <h2>4a. Kontaktformular</h2>
        <p>
          Was du ins Kontaktformular schreibst (Name, freiwillig; E-Mail-Adresse für die Antwort; Nachricht), schicken
          wir per E-Mail an unser Postfach {mail}. luibui selbst speichert die Nachricht nicht. Im Postfach bleibt sie,
          bis die Anfrage erledigt ist. Grundlage: die Bearbeitung deiner Anfrage (Art. 6 Abs. 1 lit. b DSGVO) und
          unser berechtigtes Interesse, Anfragen zu beantworten (Art. 6 Abs. 1 lit. f DSGVO). Gegen massenhafte
          Nachrichten zählen wir pro IP-Adresse höchstens fünf Nachrichten pro Stunde, nur im Arbeitsspeicher.
        </p>
      </section>

      <section>
        <h2>5. Konto im Entwicklerbereich</h2>
        <p>
          Mit der Registrierung entsteht ein Konto. Grundlage ist die Erfüllung des Nutzungsverhältnisses (Art. 6 Abs.
          1 lit. b DSGVO), soweit unten nichts anderes steht. Wir verschicken keine E-Mails, weder Werbung noch
          Newsletter.
        </p>
        <Zeilen
          zeilen={[
            ["E-Mail-Adresse", "Dein Kennzeichen für die Anmeldung."],
            [
              "Passwort",
              "Wir speichern nicht dein Passwort, sondern nur einen Prüfwert daraus (Argon2id mit Zufallssalz). Daraus lässt sich das Passwort nicht zurückrechnen, auch wir können es nicht einsehen.",
            ],
            [
              "Zwei-Faktor-Anmeldung",
              "Freiwillig. Das Geheimnis für die Einmalcodes liegt verschlüsselt in der Datenbank; der Schlüssel liegt getrennt davon in der Serverumgebung.",
            ],
            [
              "Sitzungen und API-Tokens",
              "Damit du angemeldet bleibst und Kommandozeile oder CI nutzen kannst. Gespeichert wird nur ein Prüfwert (SHA-256) des Tokens, nicht das Token selbst.",
            ],
            ["Zeitpunkte", "Registrierung und letzte Anmeldung, zur Nachvollziehbarkeit des Kontos."],
            [
              "Fehlgeschlagene Anmeldungen",
              "Nach zehn Fehlversuchen innerhalb von 15 Minuten wird für diese E-Mail-Adresse und diesen Anschluss vorübergehend gesperrt. Grundlage: berechtigtes Interesse am Schutz deines Kontos (Art. 6 Abs. 1 lit. f DSGVO). Der Zähler liegt nur im Arbeitsspeicher.",
            ],
          ]}
        />
      </section>

      <section>
        <h2>6. Projekte, Dateien und Berichte</h2>
        <Zeilen
          zeilen={[
            [
              "Hochgeladene Dateien",
              "Die Dateien, Ordner, Archive, Texte oder Repositorys, die du prüfen lässt. Sie liegen verschlüsselt (AES-256-GCM, ein eigener Schlüssel pro Projekt) auf dem Server, bis du das Projekt löschst. Gespeichert werden höchstens die letzten 10 Versionen und 500 MB pro Konto. Mit der Option „nach Prüfung löschen“ werden die Dateien direkt nach der Prüfung entfernt.",
            ],
            [
              "Berichte",
              "Ampeln, Note, Befunde mit Datei, Zeile und kurzem Ausschnitt sowie der Status, den du Befunden gibst. Sie bleiben erhalten, bis du das Projekt löschst.",
            ],
            [
              "Bekannte Schadsoftware",
              "Stimmt der Prüfwert einer Datei mit einer bekannten Schadsoftware überein, wird die Datei nicht gespeichert.",
            ],
          ]}
        />
        <p>
          Bitte lade keine personenbezogenen Daten anderer Menschen hoch. Findet die Prüfung solche Daten, etwa
          E-Mail-Adressen in einer Tabelle oder Standortdaten in einem Foto, weist der Bericht darauf hin, ohne die
          Werte anzuzeigen.
        </p>
        <p>
          Die Prüfung liest und analysiert die Dateien nur. Nichts daraus wird ausgeführt. Sie läuft in einem Prozess
          ohne Internetzugang; der Arbeitsordner wird nach jeder Prüfung gelöscht.
        </p>
      </section>

      <section>
        <h2>7. Wie lange wir speichern</h2>
        <Zeilen
          zeilen={[
            ["Konto", "Bis du es löschen lässt."],
            ["Projekte, Dateien, Berichte", "Bis du das Projekt löschst; höchstens die letzten 10 Versionen."],
            ["Bericht eines Schnellscans", "7 Tage."],
            ["Sitzung", "14 Tage oder bis du dich abmeldest."],
            ["API-Token", "Bis du es widerrufst."],
            ["IP-Adresse für die Missbrauchsgrenze", "Höchstens 24 Stunden, nur im Arbeitsspeicher."],
            ["Nachricht über das Kontaktformular", "Bei luibui gar nicht; im Postfach, bis die Anfrage erledigt ist."],
            [
              "Aktionsprotokoll",
              "Metadaten zu Aktionen wie Registrierung, Anmeldung, Anlegen oder Löschen eines Projekts, Start einer Prüfung und Erstellen eines Tokens, ohne Inhalte. Es dient der Sicherheit (Art. 6 Abs. 1 lit. f DSGVO). Wird das Konto gelöscht, verlieren die Einträge den Bezug zu dir.",
            ],
          ]}
        />
      </section>

      <section>
        <h2>8. Cookies</h2>
        <p>
          <strong>luibui.com</strong> setzt keine Cookies und speichert nichts auf deinem Gerät.
        </p>
        <p>
          <strong>app.luibui.com</strong> setzt genau ein Cookie, sobald du dich anmeldest: <code>__Host-luibui_session</code>.
          Es enthält dein Sitzungstoken, gilt 14 Tage, ist für Skripte im Browser nicht lesbar (HttpOnly), wird nur über
          HTTPS übertragen (Secure), gilt nur für app.luibui.com und wird nicht an fremde Seiten mitgeschickt
          (SameSite=Lax). Beim Abmelden wird es gelöscht. Es ist nach § 25 Abs. 2 Nr. 2 TDDDG einwilligungsfrei, weil
          ohne es keine Anmeldung möglich ist. Deshalb gibt es kein Einwilligungsbanner.
        </p>
      </section>

      <section>
        <h2>9. Empfänger</h2>
        <p>
          Website, Entwicklerbereich, Datenbank, Dateiablage und Postfach werden bei der Mittwald CM Service GmbH &amp; Co. KG,
          Königsberger Straße 4–6, 32339 Espelkamp, betrieben. Das Unternehmen ist als Auftragsverarbeiter nach Art. 28
          DSGVO tätig; ein entsprechender Vertrag besteht. Die Server stehen in Deutschland.
        </p>
        <p>Eine Weitergabe deiner Daten an weitere Dritte findet nicht statt. Wir verkaufen keine Daten.</p>
      </section>

      <section>
        <h2>10. Drittlandübermittlung</h2>
        <p>
          Personenbezogene Daten über dich werden nicht in ein Land außerhalb der EU beziehungsweise des EWR
          übermittelt. Drei Berührungspunkte nennen wir der Vollständigkeit halber:
        </p>
        <ul>
          <li>
            Gibst du ein Repository an, lädt unser Server es beim jeweiligen Anbieter herunter. GitHub hat seinen Sitz
            in den USA. Übertragen werden dabei nur die Adresse des Repositorys und die Adresse unseres Servers, keine
            Daten über dich.
          </li>
          <li>
            Die Datenbank bekannter Sicherheitslücken (OSV) und die Liste bekannter Schadsoftware (MalwareBazaar von
            abuse.ch) lädt unser Server täglich über Google Cloud Storage herunter. Dabei wird nur heruntergeladen,
            nichts von dir oder deinen Dateien verschickt.
          </li>
          <li>Die Prüfung selbst läuft ohne Internetzugang auf unserem Server in Deutschland.</li>
        </ul>
      </section>

      <section>
        <h2>11. Keine automatisierte Entscheidung über Personen</h2>
        <p>
          Ampel und Note bewerten Dateien, nicht Menschen. Es findet keine automatisierte Entscheidung im Sinne von
          Art. 22 DSGVO und kein Profiling statt.
        </p>
      </section>

      <section>
        <h2>12. Datenschutzbeauftragter</h2>
        <p>
          Ein Datenschutzbeauftragter ist nicht bestellt, weil die Voraussetzungen des Art. 37 DSGVO und des § 38 BDSG
          nicht vorliegen. Für alle Fragen zum Datenschutz erreichst du den Verantwortlichen direkt unter {mail}.
        </p>
      </section>

      <section>
        <h2>13. Deine Rechte</h2>
        <ul>
          <li>Auskunft über die zu dir verarbeiteten Daten (Art. 15 DSGVO)</li>
          <li>Berichtigung (Art. 16) und Löschung (Art. 17)</li>
          <li>Einschränkung der Verarbeitung (Art. 18)</li>
          <li>Datenübertragbarkeit (Art. 20)</li>
          <li>Widerspruch gegen Verarbeitungen auf Grundlage berechtigter Interessen (Art. 21)</li>
        </ul>
        <p>
          Projekte, Dateien, Berichte und API-Tokens kannst du im Entwicklerbereich selbst löschen. Für Auskunft,
          Datenexport und das Löschen deines Kontos genügt eine formlose E-Mail an {mail}; eine Funktion dafür im
          Entwicklerbereich folgt.
        </p>
        <p>
          Du hast das Recht, dich bei einer Aufsichtsbehörde zu beschweren. Für uns zuständig ist der Hamburgische
          Beauftragte für Datenschutz und Informationsfreiheit, Ludwig-Erhard-Straße 22, 20459 Hamburg.
        </p>
      </section>
    </Rechtstext>
  );
}
