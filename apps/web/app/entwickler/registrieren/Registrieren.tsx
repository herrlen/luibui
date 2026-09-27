"use client";

import Link from "next/link";
import { useState } from "react";

import { Feld, Knopf, Meldung } from "@/components/app/Formular";
import { senden } from "@/lib/client-api";

export function Registrieren() {
  const [fehler, setFehler] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);
  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={async (e) => {
        e.preventDefault();
        setLaeuft(true);
        const f = new FormData(e.currentTarget);
        const r = await senden("/auth/registrieren", "POST", { email: f.get("email"), passwort: f.get("passwort") });
        setLaeuft(false);
        if (r.ok) window.location.assign("/");
        else setFehler(r.fehler.felder?.includes("passwort") ? "Das Passwort braucht mindestens 12 Zeichen." : r.fehler.text);
      }}
    >
      <Feld label="E-Mail" name="email" type="email" autoComplete="email" required />
      <Feld label="Passwort (mindestens 12 Zeichen)" name="passwort" type="password" autoComplete="new-password" minLength={12} required />
      <Meldung text={fehler} />
      <Knopf disabled={laeuft}>Konto anlegen</Knopf>
      <p className="text-sm">
        Schon registriert? <Link href="/anmelden" className="text-petrol underline">Anmelden</Link>
      </p>
    </form>
  );
}
