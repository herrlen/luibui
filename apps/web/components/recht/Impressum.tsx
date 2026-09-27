import { KONTAKT, Rechtstext } from "./Rechtstext";

export function Impressum() {
  return (
    <Rechtstext titel="Impressum" stand="27. September 2026">
      <section>
        <h2>Angaben nach § 5 DDG</h2>
        <p>
          Len Messerschmidt
          <br />
          Norderreihe 21
          <br />
          22767 Hamburg
          <br />
          Deutschland
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
        <h2>Verantwortlich für den Inhalt nach § 18 Abs. 2 MStV</h2>
        <p>Len Messerschmidt, Anschrift wie oben.</p>
      </section>
      <section>
        <h2>Verbraucherstreitbeilegung</h2>
        <p>
          Wir sind nicht verpflichtet und nicht bereit, an einem Streitbeilegungsverfahren vor einer
          Verbraucherschlichtungsstelle teilzunehmen (§ 36 VSBG).
        </p>
      </section>
      <section>
        <h2>Haftung für Prüfergebnisse</h2>
        <p>
          luibui ist eine nicht-kommerzielle, automatisierte Prüfstelle. Die Prüfung liest die übergebenen Dateien und
          wertet sie nach festen Regeln aus. Die Ergebnisse sind technische Hinweise. Eine grüne Ampel heißt „keine
          bekannten Befunde“, nicht „sicher“. Die Prüfung ersetzt weder eine manuelle Sicherheitsprüfung noch eine
          Rechtsberatung. Für Entscheidungen, die allein auf einem Bericht beruhen, wird keine Haftung übernommen.
          Schnellscans haben einen eingeschränkten Umfang und sind ausdrücklich ohne Gewähr.
        </p>
      </section>
    </Rechtstext>
  );
}
