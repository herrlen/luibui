"use client";

import Link from "next/link";
import { useState } from "react";

import { Feld, Knopf, Meldung } from "@/components/app/Formular";
import { senden } from "@/lib/client-api";

export function PasswortNeu({ token }: { token: string }) {
  const [fertig, setFertig] = useState(false);
  const [fehler, setFehler] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);
  if (fertig)
    return (
      <div role="status" className="flex flex-col gap-3">
        <p>Dein neues Passwort gilt. Du bist auf allen Geräten abgemeldet.</p>
        <Link href="/anmelden" className="inline-flex h-12 w-fit items-center rounded-[10px] bg-petrol px-[22px] font-semibold text-white">
          Anmelden
        </Link>
      </div>
    );
  return (
    <form
      method="post"
      className="flex flex-col gap-4"
      onSubmit={async (e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        if (f.get("passwort") !== f.get("wiederholung")) return setFehler("Die beiden Passwörter stimmen nicht überein.");
        setLaeuft(true);
        const r = await senden("/auth/passwort-neu", "POST", { token, passwort: f.get("passwort") });
        setLaeuft(false);
        if (r.ok) setFertig(true);
        else setFehler(r.fehler.text);
      }}
    >
      <Feld label="Neues Passwort (mindestens 12 Zeichen)" name="passwort" type="password" autoComplete="new-password" minLength={12} required />
      <Feld label="Wiederholen" name="wiederholung" type="password" autoComplete="new-password" minLength={12} required />
      <Meldung text={fehler} />
      <Knopf disabled={laeuft}>Passwort speichern</Knopf>
    </form>
  );
}
