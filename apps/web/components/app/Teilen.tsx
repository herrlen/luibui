"use client";

import { useState } from "react";

import { senden } from "@/lib/client-api";

import { Kopieren } from "../Kopieren";
import { Meldung } from "./Formular";

const KNOPF =
  "inline-flex h-10 items-center rounded-[10px] border border-linie-stark bg-surface px-4 text-[15px] font-medium text-ink hover:border-petrol disabled:opacity-60";

/** Share a finished report by link (S2-12). The link is shown once; luibui keeps only its hash. */
export function Teilen({ scanId, geteilt }: { scanId: string; geteilt: boolean }) {
  const [aktiv, setAktiv] = useState(geteilt);
  const [link, setLink] = useState<string | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);
  const pfad = `/scans/${encodeURIComponent(scanId)}/teilen`;

  async function erzeugen() {
    setLaeuft(true);
    const r = await senden<{ token: string }>(pfad, "POST");
    setLaeuft(false);
    if (!r.ok) return setFehler(r.fehler.text);
    const oeffentlich = window.location.origin.replace("//app.", "//");
    setLink(`${oeffentlich}/bericht/${r.data.token}`);
    setAktiv(true);
    setFehler(null);
  }

  async function beenden() {
    setLaeuft(true);
    const r = await senden(pfad, "DELETE");
    setLaeuft(false);
    if (!r.ok) return setFehler(r.fehler.text);
    setLink(null);
    setAktiv(false);
  }

  return (
    <section aria-labelledby="teilen" className="flex flex-col gap-3 rounded-[14px] border border-linie bg-surface p-5">
      <h2 id="teilen" className="font-display text-lg font-bold">
        Bericht teilen
      </h2>
      <p className="text-sm text-muted">
        Wer den Link hat, sieht diesen Bericht ohne Anmeldung, aber nichts aus deinem Konto. Ein neuer Link macht den
        alten ungültig.
      </p>
      {link ? (
        <div className="flex flex-col gap-2">
          <p className="text-sm font-semibold">Der Link wird nur jetzt angezeigt:</p>
          <div className="flex flex-wrap items-center gap-2">
            <code className="break-all rounded-lg bg-grund px-3 py-2 font-mono text-xs">{link}</code>
            <Kopieren text={link} label="Link kopieren" />
          </div>
        </div>
      ) : aktiv ? (
        <p className="text-sm">Dieser Bericht ist per Link geteilt.</p>
      ) : null}
      <Meldung text={fehler} />
      <div className="flex flex-wrap gap-3">
        <button type="button" className={KNOPF} disabled={laeuft} onClick={() => void erzeugen()}>
          {aktiv ? "Neuen Link erzeugen" : "Link zum Teilen erzeugen"}
        </button>
        {aktiv ? (
          <button type="button" className={KNOPF} disabled={laeuft} onClick={() => void beenden()}>
            Teilen beenden
          </button>
        ) : null}
      </div>
    </section>
  );
}
