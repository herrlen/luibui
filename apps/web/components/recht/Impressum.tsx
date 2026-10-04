import { KONTAKT, Rechtstext } from "./Rechtstext";

export function Impressum() {
  return (
    <Rechtstext titel="Impressum" stand="4. Oktober 2026">
      <section>
        <h2>Angaben gemäß § 5 DDG</h2>
        <p>
          Studio Luy UG (haftungsbeschränkt)
          <br />
          Norderreihe 21
          <br />
          22767 Hamburg
          <br />
          Vertretungsberechtigte Geschäftsführerin: Keren Suh
        </p>
      </section>
      <section>
        <h2>Kontakt</h2>
        <p>
          E-Mail: <a href={`mailto:${KONTAKT}`}>{KONTAKT}</a>
          <br />
          Zweiter Kontaktweg: <a href="/kontakt">Kontaktformular</a>
          <br />
          Postanschrift: siehe oben
        </p>
        <p>Eine Telefonnummer wird nicht vorgehalten. Anfragen beantworten wir schriftlich, in der Regel innerhalb von zwei Werktagen.</p>
      </section>
      <section>
        <h2>Eintragung im Handelsregister</h2>
        <p>
          Registergericht: Amtsgericht Hamburg
          <br />
          Registernummer: HRB 195975
        </p>
      </section>
      <section>
        <h2>Umsatzsteuer-Identifikationsnummer</h2>
        <p>
          Umsatzsteuer-Identifikationsnummer gemäß § 27 a Umsatzsteuergesetz:
          <br />
          DE459298622
        </p>
      </section>
      <section>
        <h2>Verantwortlich für den Inhalt nach § 18 Abs. 2 MStV</h2>
        <p>Len Messerschmidt, Anschrift wie oben.</p>
      </section>
      <section>
        <h2>EU-Streitschlichtung</h2>
        <p>
          Die Europäische Kommission stellt eine Plattform zur Online-Streitbeilegung (OS) bereit:{" "}
          <a href="https://ec.europa.eu/consumers/odr/">https://ec.europa.eu/consumers/odr/</a>.
        </p>
      </section>
      <section>
        <h2>Verbraucherstreitbeilegung / Universalschlichtungsstelle</h2>
        <p>
          Zur Teilnahme an einem Streitbeilegungsverfahren vor einer Verbraucherschlichtungsstelle sind wir nicht
          verpflichtet und nicht bereit.
        </p>
      </section>
      <section>
        <h2>Haftung für Prüfergebnisse</h2>
        <p>
          luibui ist eine automatisierte Prüfstelle. Die Prüfung liest die übergebenen Dateien und
          wertet sie nach festen Regeln aus. Die Ergebnisse sind technische Hinweise. Eine grüne Ampel heißt „keine
          bekannten Befunde“, nicht „sicher“. Die Prüfung ersetzt weder eine manuelle Sicherheitsprüfung noch eine
          Rechtsberatung. Für Entscheidungen, die allein auf einem Bericht beruhen, wird keine Haftung übernommen.
          Schnellscans haben einen eingeschränkten Umfang und sind ausdrücklich ohne Gewähr.
        </p>
      </section>
    </Rechtstext>
  );
}
