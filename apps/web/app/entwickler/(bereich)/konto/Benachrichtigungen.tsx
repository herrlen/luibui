"use client";

import { useState } from "react";

import { Meldung } from "@/components/app/Formular";
import { senden } from "@/lib/client-api";

export type BenachrichtigungenInfo = { einstellungen: Record<string, boolean>; beschreibungen: Record<string, string> };

/** Which mails the account wants (S5-9). Saved as soon as a box changes. */
export function Benachrichtigungen({ info }: { info: BenachrichtigungenInfo }) {
  const [werte, setWerte] = useState(info.einstellungen);
  const [fehler, setFehler] = useState<string | null>(null);
  const [gespeichert, setGespeichert] = useState(false);
  return (
    <section
      id="benachrichtigungen"
      aria-labelledby="benachrichtigungen-titel"
      className="flex scroll-mt-6 flex-col gap-3 rounded-[14px] border border-linie bg-surface p-6"
    >
      <h2 id="benachrichtigungen-titel" className="font-display text-xl font-bold">
        Benachrichtigungen
      </h2>
      <p className="text-sm text-muted">Mails an deine Adresse. Mails zum Konto selbst (Bestätigung, Passwort) kommen immer.</p>
      <fieldset className="flex flex-col gap-2 text-sm">
        <legend className="sr-only">Benachrichtigungen per Mail</legend>
        {Object.entries(info.beschreibungen).map(([art, text]) => (
          <label key={art} className="flex items-start gap-2">
            <input
              type="checkbox"
              className="mt-0.5"
              checked={werte[art] ?? true}
              onChange={async (e) => {
                const neu = { ...werte, [art]: e.currentTarget.checked };
                setWerte(neu);
                setFehler(null);
                setGespeichert(false);
                const r = await senden<{ einstellungen: Record<string, boolean> }>("/konto/benachrichtigungen", "POST", neu);
                if (r.ok) {
                  setWerte(r.data.einstellungen);
                  setGespeichert(true);
                } else setFehler(r.fehler.text);
              }}
            />
            {text}
          </label>
        ))}
      </fieldset>
      <Meldung text={fehler} />
      {gespeichert ? (
        <p role="status" className="text-sm text-gruen">
          Gespeichert.
        </p>
      ) : null}
    </section>
  );
}
