"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Kopieren } from "@/components/Kopieren";
import { Feld, Knopf, Meldung } from "@/components/app/Formular";
import { senden } from "@/lib/client-api";
import { datumZeit } from "@/lib/format";

export type TokenInfo = { id: string; name: string; prefix: string; expires_at: string; last_used_at: string | null };

export function Tokens({ tokens }: { tokens: TokenInfo[] }) {
  const router = useRouter();
  const [neu, setNeu] = useState<string | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);
  return (
    <section className="flex flex-col gap-4 rounded-[14px] border border-linie bg-surface p-6">
      <h2 className="font-display text-xl font-bold">API-Tokens</h2>
      <p className="text-sm text-muted">Für die CLI und CI. Ein Token wird nur einmal angezeigt.</p>
      {neu ? (
        <div className="rounded-lg bg-gelb-bg p-3 text-sm text-gelb" role="status">
          <p className="font-semibold">Neues Token, jetzt kopieren:</p>
          <p className="mt-1 break-all font-mono">{neu}</p>
          <div className="mt-2">
            <Kopieren text={neu} />
          </div>
        </div>
      ) : null}
      <form method="post"
        className="flex flex-wrap items-end gap-3"
        onSubmit={async (e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          const r = await senden<{ token: string }>("/tokens", "POST", { name: f.get("name"), gueltig_tage: 90 });
          if (!r.ok) return setFehler(r.fehler.text);
          setNeu(r.data.token);
          router.refresh();
        }}
      >
        <Feld label="Name" name="name" placeholder="z. B. github-actions" maxLength={100} required />
        <Knopf>Token erstellen (90 Tage)</Knopf>
      </form>
      <Meldung text={fehler} />
      <ul className="flex flex-col gap-2">
        {tokens.map((t) => (
          <li key={t.id} className="flex flex-wrap items-center gap-3 rounded-lg border border-linie px-3 py-2 text-sm">
            <span className="font-semibold">{t.name}</span>
            <span className="font-mono text-muted">{t.prefix}…</span>
            <span className="text-muted">läuft ab {datumZeit(t.expires_at)}</span>
            <button
              type="button"
              className="ml-auto text-rot underline"
              onClick={async () => {
                await senden(`/tokens/${t.id}`, "DELETE");
                router.refresh();
              }}
            >
              Widerrufen
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
