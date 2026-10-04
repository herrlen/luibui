import { KONTAKT, Rechtstext } from "./Rechtstext";

// The German text follows the statutory model (Anlage 1 zu Art. 246a § 1 Abs. 2 EGBGB); its wording
// is prescribed and deliberately kept in "Sie".
export function Widerruf() {
  return (
    <Rechtstext titel="Widerrufsbelehrung" stand="4. Oktober 2026">
      <p>
        Diese Belehrung gilt für den kostenpflichtigen Kauf von Guthaben. Der Schnellscan und die kostenlosen Prüfungen
        sind kein entgeltlicher Vertrag; dafür gibt es nichts zu widerrufen.
      </p>
      <section>
        <h2>Widerrufsrecht</h2>
        <p>
          Sie haben das Recht, binnen vierzehn Tagen ohne Angabe von Gründen diesen Vertrag zu widerrufen. Die
          Widerrufsfrist beträgt vierzehn Tage ab dem Tag des Vertragsschlusses.
        </p>
        <p>
          Um Ihr Widerrufsrecht auszuüben, müssen Sie uns (Studio Luy UG (haftungsbeschränkt), Norderreihe 21, 22767 Hamburg,{" "}
          <a href={`mailto:${KONTAKT}`}>{KONTAKT}</a>) mittels einer eindeutigen Erklärung (z. B. ein mit der Post
          versandter Brief oder eine E-Mail) über Ihren Entschluss, diesen Vertrag zu widerrufen, informieren. Sie können
          dafür das <a href="#muster">Muster-Widerrufsformular</a> verwenden, das aber nicht vorgeschrieben ist.
        </p>
        <p>
          Zur Wahrung der Widerrufsfrist reicht es aus, dass Sie die Mitteilung über die Ausübung des Widerrufsrechts vor
          Ablauf der Widerrufsfrist absenden.
        </p>
      </section>
      <section>
        <h2>Folgen des Widerrufs</h2>
        <p>
          Wenn Sie diesen Vertrag widerrufen, haben wir Ihnen alle Zahlungen, die wir von Ihnen erhalten haben, unverzüglich
          und spätestens binnen vierzehn Tagen ab dem Tag zurückzuzahlen, an dem die Mitteilung über Ihren Widerruf dieses
          Vertrags bei uns eingegangen ist. Für diese Rückzahlung verwenden wir dasselbe Zahlungsmittel, das Sie bei der
          ursprünglichen Transaktion eingesetzt haben, es sei denn, mit Ihnen wurde ausdrücklich etwas anderes vereinbart; in
          keinem Fall werden Ihnen wegen dieser Rückzahlung Entgelte berechnet.
        </p>
      </section>
      <section>
        <h2>Vorzeitiges Erlöschen des Widerrufsrechts</h2>
        <p>
          Das Widerrufsrecht erlischt bei einem Vertrag über die Bereitstellung digitaler Inhalte, die nicht auf einem
          körperlichen Datenträger geliefert werden, wenn wir mit der Ausführung begonnen haben, nachdem Sie
        </p>
        <ol className="list-decimal pl-6">
          <li>
            ausdrücklich zugestimmt haben, dass wir mit der Ausführung des Vertrags vor Ablauf der Widerrufsfrist beginnen,
            und
          </li>
          <li>
            Ihre Kenntnis davon bestätigt haben, dass Sie durch Ihre Zustimmung mit Beginn der Ausführung des Vertrags Ihr
            Widerrufsrecht verlieren (§ 356 Abs. 5 BGB).
          </li>
        </ol>
        <p>
          <strong>Was das praktisch heißt.</strong> Beim Kauf setzen Sie zwei Häkchen mit genau diesen Erklärungen. Das
          Guthaben steht danach sofort bereit. <strong>Solange Sie davon nichts genutzt haben, erstatten wir trotzdem</strong>{" "}
          – darauf haben Sie streng genommen keinen Anspruch mehr, aber wir halten es für richtig. Schreiben Sie uns
          einfach.
        </p>
      </section>
      <section>
        <h2 id="muster">Muster-Widerrufsformular</h2>
        <p className="whitespace-pre-line rounded-[14px] border border-linie bg-surface p-4 font-mono text-sm">
          {`An Studio Luy UG (haftungsbeschränkt), Norderreihe 21, 22767 Hamburg, ${KONTAKT}:

Hiermit widerrufe(n) ich/wir (*) den von mir/uns (*) abgeschlossenen Vertrag über den Kauf der folgenden Waren (*)/die Erbringung der folgenden Dienstleistung (*)

Bestellt am (*)/erhalten am (*): ____________
Name des/der Verbraucher(s): ____________
Anschrift des/der Verbraucher(s): ____________
Belegnummer: ____________
Unterschrift (nur bei Mitteilung auf Papier): ____________
Datum: ____________

(*) Unzutreffendes streichen.`}
        </p>
      </section>
    </Rechtstext>
  );
}
