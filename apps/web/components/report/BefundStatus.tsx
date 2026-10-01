"use client";

import { useRouter } from "next/navigation";
import { useId, useState } from "react";

import { senden } from "@/lib/client-api";
import type { BefundStatus } from "@/lib/types";

import { Meldung } from "../app/Formular";

/** Short label for a finding's status (S3-7); null for an open finding. */
export function statusText(s: BefundStatus | undefined): string | null {
  if (!s || s.status === "offen") return null;
  if (s.status === "akzeptiert") return "Akzeptiert";
  if (s.status === "behoben") return "Behoben";
  if (s.moderation === "fehlalarm") return "Fehlalarm bestätigt";
  if (s.moderation === "bestritten") return "Vom Autor bestritten";
  return "Bestritten, wird geprüft";
}

const WAHL = [
  { wert: "offen", text: "Offen", hilfe: "Der Befund gilt und wird bearbeitet." },
  { wert: "akzeptiert", text: "Akzeptieren", hilfe: "Bewusst so gelassen. Zählt nicht mehr als offen." },
  {
    wert: "bestritten",
    text: "Einspruch: Fehlalarm",
    hilfe: "luibui prüft den Einspruch und passt bei einem Fehlalarm die Regel an.",
  },
] as const;

/**
 * Set a finding's status in the developer area. The reason is plain text, shown escaped like
 * everything else; it goes to the moderation only for a dispute.
 */
export function BefundStatusSetzen({
  projektId,
  fingerprint,
  status,
}: {
  projektId: string;
  fingerprint: string;
  status?: BefundStatus;
}) {
  const router = useRouter();
  const id = useId();
  const [aktuell, setAktuell] = useState(status);
  const [wahl, setWahl] = useState<string>(status?.status ?? "offen");
  const [begruendung, setBegruendung] = useState(status?.begruendung ?? "");
  const [fehler, setFehler] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);

  async function speichern(e: React.FormEvent) {
    e.preventDefault();
    setLaeuft(true);
    const pfad = `/projects/${encodeURIComponent(projektId)}/befunde/${encodeURIComponent(fingerprint)}/status`;
    const r = await senden<BefundStatus>(pfad, "POST", { status: wahl, begruendung });
    setLaeuft(false);
    if (!r.ok) return setFehler(r.fehler.text);
    setFehler(null);
    setAktuell(r.data);
    router.refresh();
  }

  const label = statusText(aktuell);
  return (
    <form method="post" onSubmit={(e) => void speichern(e)} className="mt-4 flex flex-col gap-3 rounded-lg bg-grund p-4">
      <fieldset className="flex flex-col gap-2">
        <legend className="text-sm font-semibold">
          Status{label ? `: ${label}` : ": offen"}
        </legend>
        {WAHL.map((w) => (
          <label key={w.wert} className="flex items-start gap-2 text-sm">
            <input
              type="radio"
              name={`${id}-status`}
              value={w.wert}
              checked={wahl === w.wert}
              onChange={() => setWahl(w.wert)}
              className="mt-1"
            />
            <span>
              <span className="font-medium">{w.text}</span> <span className="text-muted">– {w.hilfe}</span>
            </span>
          </label>
        ))}
      </fieldset>
      {wahl !== "offen" ? (
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-semibold">Begründung</span>
          <textarea
            value={begruendung}
            onChange={(e) => setBegruendung(e.target.value)}
            maxLength={2000}
            rows={3}
            required
            minLength={5}
            className="rounded-xl border border-linie-stark bg-surface p-3 text-base focus:border-petrol"
          />
        </label>
      ) : null}
      <Meldung text={fehler} />
      <div>
        <button
          type="submit"
          disabled={laeuft}
          className="inline-flex h-10 items-center rounded-[10px] border border-linie-stark bg-surface px-4 text-[15px] font-medium text-ink hover:border-petrol disabled:opacity-60"
        >
          Status speichern
        </button>
      </div>
    </form>
  );
}
