"use client";

import { useRouter } from "next/navigation";
import { useId, useState } from "react";

import { senden } from "@/lib/client-api";
import { BEFUND_STATUS_TEXT, datumZeit, MODERATION_TEXT } from "@/lib/format";
import type { BefundStatus } from "@/lib/types";

import { Meldung } from "./Formular";

const KNOPF =
  "inline-flex h-9 items-center rounded-[10px] border border-linie-stark bg-surface px-3 text-sm font-medium text-ink hover:border-petrol disabled:opacity-60";

export const STATUS_STIL: Record<string, string> = {
  behoben: "bg-gruen-bg text-gruen",
  akzeptiert: "bg-tag text-ink-2",
  bestritten: "bg-tag text-ink-2",
};

/** The badge in the finding's header; nothing while the finding is open. */
export function StatusMarke({ status }: { status?: BefundStatus }) {
  if (!status || status.status === "offen") return null;
  return (
    <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${STATUS_STIL[status.status]}`}>
      {status.moderation ? MODERATION_TEXT[status.moderation] : BEFUND_STATUS_TEXT[status.status]}
    </span>
  );
}

type Ziel = "akzeptiert" | "bestritten";

const FRAGE: Record<Ziel, { label: string; hilfe: string; knopf: string }> = {
  akzeptiert: {
    label: "Warum ist der Befund für dich in Ordnung?",
    hilfe: "Zum Beispiel: nur im Testaufbau, bewusst so entschieden. Die Bewertung des Berichts bleibt gleich.",
    knopf: "Akzeptieren",
  },
  bestritten: {
    label: "Warum ist das ein Fehlalarm?",
    hilfe:
      "luibui sieht sich den Befund mit Beleg und deiner Begründung an. Ist es ein Fehlalarm, wird die Regel angepasst und der Befund fällt bei der nächsten Prüfung weg.",
    knopf: "Einspruch einlegen",
  },
};

/**
 * Status of one finding in the developer area (S3-7): accept with a reason, dispute as a false
 * alarm, or open again. "Behoben" is only set by the next check. The texts the owner and the
 * moderation typed are rendered as plain text.
 */
export function BefundStatusSteuerung({
  scanId,
  fingerprint,
  status,
}: {
  scanId: string;
  fingerprint: string;
  status?: BefundStatus;
}) {
  const router = useRouter();
  const [aktuell, setAktuell] = useState(status);
  const [ziel, setZiel] = useState<Ziel | null>(null);
  const [text, setText] = useState("");
  const [fehler, setFehler] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);
  const feld = useId();
  const wert = aktuell?.status ?? "offen";

  async function setzen(neu: "offen" | Ziel, begruendung?: string) {
    setLaeuft(true);
    const r = await senden<BefundStatus>(`/scans/${encodeURIComponent(scanId)}/befund-status`, "POST", {
      fingerprint,
      status: neu,
      begruendung: begruendung ?? null,
    });
    setLaeuft(false);
    if (!r.ok) return setFehler(r.fehler.text);
    setAktuell(r.data);
    setZiel(null);
    setText("");
    setFehler(null);
    router.refresh(); // the open counts in the sidebar and the overview
  }

  return (
    <section aria-label="Status des Befunds" className="mt-4 flex flex-col gap-2 border-t border-linie pt-4 text-sm">
      <p>
        <span className="font-semibold">Status: </span>
        {BEFUND_STATUS_TEXT[wert]}
        {aktuell && wert !== "offen" ? (
          <span className="text-muted"> · seit {datumZeit(aktuell.geaendert_am)}</span>
        ) : null}
      </p>
      {wert === "behoben" ? (
        <p className="text-muted">In einer neueren Prüfung dieses Projekts ist der Befund nicht mehr enthalten.</p>
      ) : null}
      {aktuell?.begruendung ? (
        <p className="whitespace-pre-wrap break-words rounded-lg bg-grund px-3 py-2">{aktuell.begruendung}</p>
      ) : null}
      {wert === "bestritten" ? (
        aktuell?.moderation ? (
          <p>
            <span className="font-semibold">Entscheidung von luibui: </span>
            {MODERATION_TEXT[aktuell.moderation]}
            {aktuell.moderation_notiz ? (
              <span className="mt-1 block whitespace-pre-wrap break-words text-muted">{aktuell.moderation_notiz}</span>
            ) : null}
          </p>
        ) : (
          <p className="text-muted">Der Einspruch wird von luibui geprüft.</p>
        )
      ) : null}
      {ziel ? (
        <form
          method="post"
          className="flex flex-col gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            void setzen(ziel, text);
          }}
        >
          <label htmlFor={feld} className="font-semibold">
            {FRAGE[ziel].label}
          </label>
          <textarea
            id={feld}
            required
            maxLength={2000}
            rows={3}
            value={text}
            onChange={(e) => setText(e.target.value)}
            className="rounded-xl border border-linie-stark bg-surface px-3 py-2 text-base focus:border-petrol"
          />
          <p className="text-xs text-muted">{FRAGE[ziel].hilfe}</p>
          <div className="flex flex-wrap gap-2">
            <button type="submit" disabled={laeuft || !text.trim()} className={KNOPF}>
              {FRAGE[ziel].knopf}
            </button>
            <button type="button" onClick={() => setZiel(null)} className={KNOPF}>
              Abbrechen
            </button>
          </div>
        </form>
      ) : wert === "offen" ? (
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => setZiel("akzeptiert")} className={KNOPF}>
            Akzeptieren …
          </button>
          <button type="button" onClick={() => setZiel("bestritten")} className={KNOPF}>
            Fehlalarm melden …
          </button>
        </div>
      ) : wert !== "behoben" ? (
        <div>
          <button type="button" disabled={laeuft} onClick={() => void setzen("offen")} className={KNOPF}>
            Wieder öffnen
          </button>
        </div>
      ) : null}
      <Meldung text={fehler} />
    </section>
  );
}
