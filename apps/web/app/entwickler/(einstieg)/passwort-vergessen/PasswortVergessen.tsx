"use client";

import Link from "next/link";
import { useState } from "react";

import { Feld, Knopf, Meldung } from "@/components/app/Formular";
import { senden } from "@/lib/client-api";

export function PasswortVergessen() {
  const [hinweis, setHinweis] = useState<string | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);
  if (hinweis)
    return (
      <div role="status" className="flex flex-col gap-3">
        <p>{hinweis}</p>
        <p className="text-sm text-muted">Der Link gilt eine Stunde. Schau auch im Spam-Ordner nach.</p>
        <Link href="/anmelden" className="text-sm text-petrol underline">
          Zurück zur Anmeldung
        </Link>
      </div>
    );
  return (
    <form
      method="post"
      className="flex flex-col gap-4"
      onSubmit={async (e) => {
        e.preventDefault();
        setLaeuft(true);
        const f = new FormData(e.currentTarget);
        const r = await senden<{ hinweis: string }>("/auth/passwort-vergessen", "POST", { email: f.get("email") });
        setLaeuft(false);
        if (r.ok) setHinweis(r.data.hinweis);
        else setFehler(r.fehler.text);
      }}
    >
      <Feld label="E-Mail" name="email" type="email" autoComplete="email" required />
      <Meldung text={fehler} />
      <Knopf disabled={laeuft}>Link schicken</Knopf>
    </form>
  );
}
