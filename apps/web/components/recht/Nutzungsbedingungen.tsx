import { KONTAKT, Rechtstext } from "./Rechtstext";

export function Nutzungsbedingungen() {
  const mail = <a href={`mailto:${KONTAKT}`}>{KONTAKT}</a>;
  return (
    <Rechtstext titel="Nutzungsbedingungen" stand="27. September 2026">
      <p>Diese Bedingungen gelten für den Schnellscan auf luibui.com und den Entwicklerbereich auf app.luibui.com.</p>
      <section>
        <h2>1. Anbieter</h2>
        <p>
          Len Messerschmidt, Norderreihe 21, 22767 Hamburg, E-Mail: {mail}
        </p>
      </section>
      <section>
        <h2>2. Was der Dienst leistet</h2>
        <p>
          luibui prüft KI-Skills, Plugins, Tools und MCP-Server automatisiert auf Merkmale aus den Bereichen Sicherheit und
          Datenschutz und erstellt daraus einen Bericht mit Ampeln, Note und Hinweisen zum Beheben. Die Dateien werden
          nur gelesen, nie ausgeführt.
        </p>
        <p>
          Der Bericht ist <strong>keine Garantie für Sicherheit</strong>. Eine automatisierte Prüfung findet, wonach sie
          sucht. Grün heißt „keine bekannten Befunde“, nicht „sicher“. Der Bericht ist auch keine Rechtsberatung.
        </p>
      </section>
      <section>
        <h2>3. Was du prüfen lassen darfst</h2>
        <p>
          Du darfst Dateien hochladen, die du prüfen lassen willst, auch verdächtige Pakete aus fremder Quelle; genau
          dafür ist luibui da. Nicht gestattet ist es, luibui zu nutzen, um Schadsoftware zu verbreiten, Rechte Dritter zu
          verletzen oder personenbezogene Daten anderer Menschen ohne Grundlage hochzuladen.
        </p>
      </section>
      <section>
        <h2>4. Konto</h2>
        <ul>
          <li>Für den Schnellscan brauchst du kein Konto.</li>
          <li>Die E-Mail-Adresse muss dir gehören; Prüfungen im Entwicklerbereich setzen voraus, dass du sie bestätigt hast.</li>
          <li>Ein Konto ist persönlich. Halte dein Passwort geheim und melde uns einen Verdacht auf Missbrauch.</li>
          <li>
            Du kannst dein Konto jederzeit löschen lassen (formlose E-Mail an {mail}). Wir können ein Konto sperren, wenn
            es gegen diese Bedingungen verstößt; bei geringfügigen Verstößen weisen wir vorher darauf hin.
          </li>
        </ul>
      </section>
      <section>
        <h2>5. Faire Nutzung</h2>
        <p>
          Es gelten Mengengrenzen: höchstens drei Schnellscans pro Tag und Anschluss, Größengrenzen je Upload, wie sie im
          Formular stehen. Nicht gestattet sind automatisierte Massenabfragen und Versuche, die Grenzen zu umgehen, zum
          Beispiel mit mehreren Konten.
        </p>
      </section>
      <section>
        <h2>6. Verfügbarkeit</h2>
        <p>
          Der Dienst wird ohne zugesicherte Verfügbarkeit bereitgestellt. Wartung, Störungen und Weiterentwicklung können
          zu Unterbrechungen führen. Der Schnellscan ist eine freiwillige Leistung; ein Anspruch auf ihn besteht nicht.
        </p>
      </section>
      <section>
        <h2>7. Preise und Guthaben</h2>
        <ul>
          <li>Der Schnellscan ist kostenlos.</li>
          <li>
            Nach der Bestätigung deiner E-Mail-Adresse sind <strong>ein Projekt und drei Prüfungen</strong> im
            Entwicklerbereich kostenlos.
          </li>
          <li>
            Danach kostet jede Prüfung 1 Guthaben, im Projekt wie als Einzelprüfung. Guthaben gibt es als Paket:{" "}
            <strong>10 Prüfungen für 4,90 €</strong> oder <strong>25 Prüfungen für 9,90 €</strong>. Mit einem Kauf kannst du
            beliebig viele Projekte anlegen.
          </li>
          <li>Einmalig, kein Abo. Guthaben verfällt nicht. Du kannst beliebig oft nachkaufen.</li>
          <li>Die Preise sind Endpreise. Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.</li>
          <li>
            Bezahlt wird über PayPal. Der Vertrag kommt zustande, wenn PayPal die Zahlung bestätigt; das Guthaben steht
            unmittelbar danach bereit. Du bekommst einen Beleg in deinem Konto. Zum Widerruf siehe die{" "}
            <a href="/widerruf">Widerrufsbelehrung</a>.
          </li>
          <li>
            Scheitert eine Prüfung aus einem Grund, der bei uns liegt, wird das Guthaben zurückgebucht, automatisch und ohne
            dass du dich melden musst. Lehnt die Prüfung eine Eingabe ab (zum Beispiel ein beschädigtes Archiv), wird nichts
            abgebucht.
          </li>
        </ul>
      </section>
      <section>
        <h2>8. Rechte an den Berichten</h2>
        <p>
          Der Bericht zu deinen Dateien gehört dir. Du darfst ihn frei verwenden und weitergeben. Die zugrundeliegende
          Software und die Prüfregeln bleiben beim Anbieter.
        </p>
      </section>
      <section>
        <h2>9. Haftung</h2>
        <p>
          Wir haften unbeschränkt bei Vorsatz und grober Fahrlässigkeit sowie für Schäden aus der Verletzung des Lebens, des
          Körpers oder der Gesundheit. Bei einfacher Fahrlässigkeit haften wir nur bei Verletzung einer Pflicht, deren
          Erfüllung die ordnungsgemäße Durchführung überhaupt erst ermöglicht und auf deren Einhaltung du regelmäßig
          vertrauen darfst, und der Höhe nach begrenzt auf den vorhersehbaren, vertragstypischen Schaden. Die Haftung nach
          dem Produkthaftungsgesetz bleibt unberührt. Für Entscheidungen, die du allein auf Grundlage eines Berichts
          triffst, haften wir nicht (siehe Abschnitt 2).
        </p>
      </section>
      <section>
        <h2>10. Änderungen</h2>
        <p>
          Wir können diese Bedingungen ändern, wenn sich der Dienst oder die Rechtslage ändert. Über wesentliche Änderungen
          informieren wir Kontoinhaber mindestens 14 Tage vorher per E-Mail. Bereits gekauftes Guthaben bleibt davon
          unberührt.
        </p>
      </section>
      <section>
        <h2>11. Schlussbestimmungen</h2>
        <p>
          Es gilt deutsches Recht. Bist du Verbraucher, bleiben die zwingenden Verbraucherschutzvorschriften deines
          Aufenthaltsstaats unberührt. Wir sind weder verpflichtet noch bereit, an einem Streitbeilegungsverfahren vor
          einer Verbraucherschlichtungsstelle teilzunehmen.
        </p>
      </section>
    </Rechtstext>
  );
}
