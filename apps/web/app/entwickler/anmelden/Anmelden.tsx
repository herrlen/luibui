"use client";

import Link from "next/link";
import { useState } from "react";

import { Feld, Knopf, Meldung } from "@/components/app/Formular";
import { senden } from "@/lib/client-api";

export function Anmelden() {
  const [fehler, setFehler] = useState<string | null>(null);
  const [totp, setTotp] = useState(false);
  const [laeuft, setLaeuft] = useState(false);
  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={async (e) => {
        e.preventDefault();
        setLaeuft(true);
        const f = new FormData(e.currentTarget);
        const r = await senden("/auth/anmelden", "POST", {
          email: f.get("email"),
          passwort: f.get("passwort"),
          totp: f.get("totp") || undefined,
        });
        setLaeuft(false);
        if (r.ok) {
          window.location.assign("/");
          return;
        }
        if (r.fehler.code === "totp_erforderlich") setTotp(true);
        setFehler(r.fehler.text);
      }}
    >
      <Feld label="E-Mail" name="email" type="email" autoComplete="email" required />
      <Feld label="Passwort" name="passwort" type="password" autoComplete="current-password" required />
      {totp ? <Feld label="Code aus der Authenticator-App" name="totp" inputMode="numeric" autoComplete="one-time-code" /> : null}
      <Meldung text={fehler} />
      <Knopf disabled={laeuft}>Anmelden</Knopf>
      <p className="text-sm">
        Noch kein Konto? <Link href="/registrieren" className="text-petrol underline">Kostenlos registrieren</Link>
      </p>
    </form>
  );
}
