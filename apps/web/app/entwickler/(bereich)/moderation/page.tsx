import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { Brotkrumen } from "@/components/app/Brotkrumen";
import { SCHWERE_STIL } from "@/lib/schwere";
import { datumZeit, MODERATION_TEXT, SCHWERE_TEXT } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { Einspruch } from "@/lib/types";

export const metadata = { title: "Moderation – luibui" };
export const dynamic = "force-dynamic";

function Liste({ einsprueche, leer }: { einsprueche: Einspruch[]; leer: string }) {
  if (!einsprueche.length) return <p className="text-sm text-muted">{leer}</p>;
  return (
    <ul className="flex flex-col gap-2">
      {einsprueche.map((e) => (
        <li key={e.id}>
          <Link
            href={`/moderation/${e.id}`}
            className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-[14px] border border-linie bg-surface p-4 hover:border-petrol"
          >
            {e.schwere ? (
              <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${SCHWERE_STIL[e.schwere]}`}>
                {SCHWERE_TEXT[e.schwere]}
              </span>
            ) : null}
            <span className="min-w-0 flex-1 font-semibold">{e.titel}</span>
            <span className="font-mono text-xs text-muted">{e.rule_id}</span>
            <span className="w-full text-sm text-muted">
              {e.projekt} · eingereicht {datumZeit(e.eingereicht_am)}
              {e.moderation ? ` · ${MODERATION_TEXT[e.moderation]}` : ""}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

/** Disputed findings of all accounts (S3-7). The API answers 404 to everyone but admins. */
export default async function Moderation() {
  const offen = await apiGet<Einspruch[]>("/api/v1/moderation/einsprueche");
  if (!offen.ok && offen.status === 401) redirect("/anmelden");
  if (!offen.ok) notFound();
  const entschieden = await apiGet<Einspruch[]>("/api/v1/moderation/einsprueche?entschieden=true");
  return (
    <div className="flex flex-col gap-6">
      <Brotkrumen pfad={[{ text: "Übersicht", href: "/" }, { text: "Moderation" }]} />
      <h1 className="font-display text-3xl font-bold">Einsprüche</h1>
      <p className="text-sm text-muted">
        Befunde, die Autoren als Fehlalarm bestreiten. Beleg und Erklärung stehen erst in der Einzelansicht; jedes Öffnen
        und jede Entscheidung wird im Audit-Log festgehalten.
      </p>
      <section className="flex flex-col gap-3">
        <h2 className="font-display text-xl font-bold">Offen</h2>
        <Liste einsprueche={offen.data} leer="Keine offenen Einsprüche." />
      </section>
      <section className="flex flex-col gap-3">
        <h2 className="font-display text-xl font-bold">Entschieden</h2>
        <Liste einsprueche={entschieden.ok ? entschieden.data : []} leer="Noch nichts entschieden." />
      </section>
    </div>
  );
}
