"use client";

import { useEffect, useState } from "react";

import { senden } from "@/lib/client-api";

// Back from PayPal: confirm the payment on the server, then reload where the purchase started.
export function Zurueck({ orderId, weiter, abgebrochen }: { orderId?: string; weiter: string; abgebrochen: boolean }) {
  const [meldung, setMeldung] = useState(abgebrochen ? "Die Zahlung wurde abgebrochen. Es wurde nichts abgebucht." : "Zahlung wird bestätigt …");
  const [fertig, setFertig] = useState(abgebrochen);
  useEffect(() => {
    if (abgebrochen || !orderId) return;
    void (async () => {
      const r = await senden<{ bezahlt: boolean; stand: number }>("/guthaben/bestaetigen", "POST", { order_id: orderId });
      if (r.ok && r.data.bezahlt) {
        setMeldung(`Danke! Dein Guthaben: ${r.data.stand} Prüfungen. Es geht gleich weiter …`);
        setTimeout(() => window.location.assign(weiter), 1500);
        return;
      }
      setFertig(true);
      setMeldung(
        r.ok
          ? "PayPal hat die Zahlung nicht bestätigt. Es wurde nichts gutgeschrieben und nichts abgebucht."
          : r.fehler.text,
      );
    })();
  }, [orderId, weiter, abgebrochen]);
  return (
    <div className="flex flex-col gap-4">
      <p className="text-lg" role="status" aria-live="polite">
        {meldung}
      </p>
      {fertig ? (
        <a href={weiter} className="inline-flex h-12 w-fit items-center rounded-[10px] bg-petrol px-[22px] font-semibold text-white">
          Zurück
        </a>
      ) : null}
    </div>
  );
}
