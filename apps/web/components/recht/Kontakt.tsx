import { Kontaktformular } from "./Kontaktformular";
import { KONTAKT, Rechtstext } from "./Rechtstext";

export function Kontakt() {
  return (
    <Rechtstext titel="Kontakt" stand="27. September 2026">
      <p>
        Fragen, Hinweise auf Fehlalarme oder übersehene Befunde, Sicherheitsmeldungen: Schreib uns über das Formular
        oder direkt an <a href={`mailto:${KONTAKT}`}>{KONTAKT}</a>.
      </p>
      <Kontaktformular />
    </Rechtstext>
  );
}
