"use client";

import { useState } from "react";

import { Feld, Knopf, Meldung } from "@/components/app/Formular";
import { senden } from "@/lib/client-api";

import { KONTAKT } from "./Rechtstext";

export function Kontaktformular() {
  const [fehler, setFehler] = useState<string | null>(null);
  const [gesendet, setGesendet] = useState(false);
  const [laeuft, setLaeuft] = useState(false);
  if (gesendet) {
    return (
      <p role="status" className="rounded-[14px] border border-linie bg-surface p-6">
        Danke, deine Nachricht ist angekommen. Die Antwort kommt per E-Mail, in der Regel innerhalb von zwei
        Werktagen.
      </p>
    );
  }
  return (
    <form
      className="flex flex-col gap-4 rounded-[18px] border border-linie bg-surface p-6 sm:p-8"
      onSubmit={async (e) => {
        e.preventDefault();
        setLaeuft(true);
        setFehler(null);
        const f = new FormData(e.currentTarget);
        const r = await senden("/kontakt", "POST", {
          name: f.get("name"),
          email: f.get("email"),
          nachricht: f.get("nachricht"),
          website: f.get("website"),
        });
        setLaeuft(false);
        if (r.ok) setGesendet(true);
        else if (r.fehler.felder?.includes("nachricht")) setFehler("Die Nachricht braucht 10 bis 5.000 Zeichen.");
        else if (r.fehler.felder?.includes("email")) setFehler("Bitte gib eine gültige E-Mail-Adresse an.");
        else setFehler(r.fehler.text);
      }}
    >
      <Feld label="Name (freiwillig)" name="name" autoComplete="name" maxLength={100} />
      <Feld label="E-Mail für die Antwort" name="email" type="email" autoComplete="email" required maxLength={320} />
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-semibold">Nachricht</span>
        <textarea
          name="nachricht"
          required
          minLength={10}
          maxLength={5000}
          rows={7}
          className="rounded-xl border border-linie-stark bg-surface px-4 py-3 text-base focus:border-petrol"
        />
      </label>
      {/* Honeypot: invisible for people and screen readers, bots fill it in. */}
      <div aria-hidden="true" className="absolute -left-[9999px] h-px w-px overflow-hidden">
        <label>
          Website
          <input name="website" tabIndex={-1} autoComplete="off" />
        </label>
      </div>
      <Meldung text={fehler} />
      <p className="text-sm text-muted">
        Die Nachricht geht per E-Mail an {KONTAKT}. luibui speichert sie nicht. Mehr dazu in der{" "}
        <a href="/datenschutz" className="text-petrol underline">
          Datenschutzerklärung
        </a>
        .
      </p>
      <div>
        <Knopf disabled={laeuft}>{laeuft ? "Wird gesendet …" : "Nachricht senden"}</Knopf>
      </div>
    </form>
  );
}
