"use client";

import { useEffect, useRef, useState } from "react";

import { senden } from "@/lib/client-api";
import type { Fehler } from "@/lib/types";

import { Meldung } from "./Formular";

type Paket = { id: string; pruefungen: number; preis_cent: number; preis_text?: string };
const EVENT = "luibui:aufladen";

/** Open the top-up dialog, e.g. after a 402 answer. */
export function aufladen(fehler?: Fehler) {
  window.dispatchEvent(new CustomEvent(EVENT, { detail: fehler ?? null }));
}

/** true if the answer was "payment required" and the dialog has been opened. */
export function zahlungNoetig(r: { ok: boolean; status?: number; fehler?: Fehler }): boolean {
  if (r.ok || r.status !== 402) return false;
  aufladen(r.fehler);
  return true;
}

const TITEL: Record<string, string> = {
  guthaben_leer: "Dein Guthaben ist aufgebraucht",
  projekt_limit: "Weitere Projekte mit Guthaben",
};

function preis(cent: number): string {
  return `${Math.floor(cent / 100)},${String(cent % 100).padStart(2, "0")} €`;
}

export function AufladenDialog() {
  const dialog = useRef<HTMLDialogElement>(null);
  const [anlass, setAnlass] = useState<Fehler | null>(null);
  const [pakete, setPakete] = useState<Paket[]>([]);
  const [paket, setPaket] = useState("p10");
  const [zustimmung, setZustimmung] = useState(false);
  const [kenntnis, setKenntnis] = useState(false);
  const [fehler, setFehler] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);

  useEffect(() => {
    const oeffnen = async (e: Event) => {
      const detail = (e as CustomEvent<(Fehler & { pakete?: Paket[] }) | null>).detail;
      setAnlass(detail);
      setFehler(null);
      setZustimmung(false);
      setKenntnis(false);
      if (detail?.pakete) setPakete(detail.pakete);
      else {
        const r = await fetch("/api/v1/guthaben", { credentials: "same-origin" });
        if (r.ok) setPakete(((await r.json()) as { pakete: Paket[] }).pakete);
      }
      dialog.current?.showModal();
    };
    window.addEventListener(EVENT, oeffnen);
    return () => window.removeEventListener(EVENT, oeffnen);
  }, []);

  return (
    <dialog
      ref={dialog}
      aria-labelledby="aufladen-titel"
      className="m-auto w-[min(560px,calc(100vw-32px))] rounded-[18px] border border-linie bg-surface p-0 backdrop:bg-ink/50"
    >
      <form
        method="post"
        className="flex flex-col gap-5 p-6 sm:p-8"
        onSubmit={async (e) => {
          e.preventDefault();
          setLaeuft(true);
          setFehler(null);
          const r = await senden<{ url: string }>("/guthaben/kaufen", "POST", {
            paket,
            zustimmung,
            kenntnis,
            weiter: window.location.pathname,
          });
          if (r.ok) return window.location.assign(r.data.url);
          setLaeuft(false);
          setFehler(r.fehler.text);
        }}
      >
        <div>
          <h2 id="aufladen-titel" className="font-display text-2xl font-bold tracking-[-0.01em]">
            {TITEL[anlass?.code ?? ""] ?? "Guthaben aufladen"}
          </h2>
          <p className="mt-2 text-[15px] leading-[1.6] text-ink-2">
            Gratis sind ein Projekt und drei Prüfungen, der Schnellscan bleibt immer kostenlos. Danach kostet jede
            Prüfung 1 Guthaben, im Projekt wie als Einzelprüfung. Mit einem Kauf kannst du beliebig viele Projekte
            anlegen. Kein Abo, das Guthaben verfällt nicht.
          </p>
        </div>
        <fieldset className="grid gap-3 sm:grid-cols-2">
          <legend className="sr-only">Paket</legend>
          {pakete.map((p) => (
            <label
              key={p.id}
              className={`flex cursor-pointer flex-col gap-1 rounded-[14px] border p-4 ${
                paket === p.id ? "border-petrol bg-petrol-hell" : "border-linie-stark bg-surface"
              }`}
            >
              <input type="radio" name="paket" value={p.id} checked={paket === p.id} onChange={() => setPaket(p.id)} className="sr-only" />
              <span className="font-display text-2xl font-bold">{p.pruefungen} Prüfungen</span>
              <span className="text-[15px] font-semibold">{preis(p.preis_cent)}</span>
              <span className="text-sm text-muted">{preis(Math.round(p.preis_cent / p.pruefungen))} pro Prüfung</span>
            </label>
          ))}
        </fieldset>
        <p className="text-sm text-muted">Endpreise. Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.</p>
        <label className="flex items-start gap-3 text-sm">
          <input type="checkbox" required checked={zustimmung} onChange={(e) => setZustimmung(e.target.checked)} className="mt-1 size-4" />
          <span>Ich stimme ausdrücklich zu, dass luibui vor Ablauf der Widerrufsfrist mit der Ausführung beginnt und mir das Guthaben sofort bereitstellt.</span>
        </label>
        <label className="flex items-start gap-3 text-sm">
          <input type="checkbox" required checked={kenntnis} onChange={(e) => setKenntnis(e.target.checked)} className="mt-1 size-4" />
          <span>
            Mir ist bekannt, dass ich mit Beginn der Ausführung mein{" "}
            <a href="/widerruf" target="_blank" className="text-petrol underline">
              Widerrufsrecht
            </a>{" "}
            verliere. Es gelten die{" "}
            <a href="/nutzungsbedingungen" target="_blank" className="text-petrol underline">
              Nutzungsbedingungen
            </a>
            .
          </span>
        </label>
        <Meldung text={fehler} />
        <div className="flex flex-wrap gap-3">
          <button
            type="submit"
            disabled={laeuft || !pakete.length}
            className="inline-flex h-12 items-center rounded-[10px] bg-petrol px-[22px] text-[15px] font-semibold text-white hover:bg-petrol-dunkel disabled:opacity-60"
          >
            {laeuft ? "Weiter zu PayPal …" : "Zahlungspflichtig mit PayPal bezahlen"}
          </button>
          <button
            type="button"
            onClick={() => dialog.current?.close()}
            className="inline-flex h-12 items-center rounded-[10px] border border-linie-stark bg-surface px-[22px] text-[15px] font-medium"
          >
            Abbrechen
          </button>
        </div>
      </form>
    </dialog>
  );
}
