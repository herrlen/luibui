"use client";

import { useState } from "react";

import { senden } from "@/lib/client-api";
import { herkunftAnzeige } from "@/lib/herkunft";
import type { PaketVersion } from "@/lib/types";

/** Publish this check's package to the register (S4-2). The server checks everything again. */
export function Veroeffentlichen({ scanId }: { scanId: string }) {
  const [ergebnis, setErgebnis] = useState<PaketVersion | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);
  if (ergebnis) {
    const h = herkunftAnzeige(ergebnis.herkunft);
    return (
      <div className="flex flex-col gap-2">
        <p role="status" className="rounded-lg bg-gruen-bg px-4 py-3 text-sm text-gruen">
          Veröffentlicht: <span className="font-mono font-semibold">{ergebnis.paket}</span> {ergebnis.version}.{" "}
          <a href="/register" className="underline">
            Zu deinen Paketen
          </a>
        </p>
        {h.ton === "rot" || h.ton === "gelb" ? (
          <p className={`rounded-lg px-4 py-3 text-sm ${h.ton === "rot" ? "bg-rot-bg text-rot" : "bg-gelb-bg text-gelb"}`}>
            Herkunft: {h.titel}. {h.text} Das steht so auf der Paketseite; eine neue Version mit passendem Tag behebt es.
          </p>
        ) : null}
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          disabled={laeuft}
          className="inline-flex h-10 items-center rounded-[10px] bg-petrol px-4 text-[15px] font-semibold text-white hover:bg-petrol-dunkel disabled:opacity-60"
          onClick={async () => {
            if (!window.confirm("Paket öffentlich im Register veröffentlichen? Die Version lässt sich danach nicht mehr ändern, nur zurückziehen.")) return;
            setLaeuft(true);
            setFehler(null);
            const r = await senden<PaketVersion>("/register/veroeffentlichen", "POST", { scan_id: scanId });
            setLaeuft(false);
            if (r.ok) setErgebnis(r.data);
            else setFehler(r.fehler.text);
          }}
        >
          {laeuft ? "Wird veröffentlicht …" : "Im Register veröffentlichen"}
        </button>
        <span className="text-sm text-muted">Öffentlich, signiert, Name und Version aus luibui.json. Nennt sie ein Repository, gleicht luibui mit dem Tag der Version ab.</span>
      </div>
      {fehler ? (
        <p role="alert" className="rounded-lg bg-rot-bg px-3 py-2 text-sm text-rot">
          {fehler}
        </p>
      ) : null}
    </div>
  );
}
