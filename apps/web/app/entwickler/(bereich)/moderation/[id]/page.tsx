import { notFound, redirect } from "next/navigation";

import { Brotkrumen } from "@/components/app/Brotkrumen";
import { MitCode } from "@/components/report/BefundKarte";
import { SCHWERE_STIL } from "@/lib/schwere";
import { datumZeit, MODERATION_TEXT, SCHWERE_TEXT } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { EinspruchDetail } from "@/lib/types";

import { Entscheiden } from "./Entscheiden";

export const metadata = { title: "Einspruch – luibui" };
export const dynamic = "force-dynamic";

/** One dispute with evidence. Opening it is logged by the API. Package content only as text. */
export default async function EinspruchSeite({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const r = await apiGet<EinspruchDetail>(`/api/v1/moderation/einsprueche/${encodeURIComponent(id)}`);
  if (!r.ok && r.status === 401) redirect("/anmelden");
  if (!r.ok) notFound();
  const e = r.data;
  const ort = e.datei ? `${e.datei}${e.zeile ? `:${e.zeile}` : ""}` : "ganzes Paket";
  return (
    <div className="flex flex-col gap-6">
      <Brotkrumen
        pfad={[{ text: "Übersicht", href: "/" }, { text: "Moderation", href: "/moderation" }, { text: e.titel }]}
      />
      <h1 className="font-display text-3xl font-bold">Einspruch</h1>
      <article className="flex flex-col gap-3 rounded-[14px] border border-linie bg-surface p-5">
        <p className="flex flex-wrap items-center gap-3">
          {e.schwere ? (
            <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${SCHWERE_STIL[e.schwere]}`}>
              {SCHWERE_TEXT[e.schwere]}
            </span>
          ) : null}
          <span className="font-semibold">{e.titel}</span>
        </p>
        <p className="font-mono text-xs text-muted">
          {e.rule_id} · {e.projekt} · {ort}
        </p>
        {e.erklaerung ? (
          <p className="text-[15px] leading-[1.6] text-ink-2">
            <MitCode text={e.erklaerung} />
          </p>
        ) : null}
        {e.beleg ? (
          <figure>
            <figcaption className="text-xs text-muted">Beleg aus {ort}</figcaption>
            <pre className="mt-1 overflow-x-auto whitespace-pre rounded-lg bg-grund p-3 font-mono text-xs">{e.beleg}</pre>
          </figure>
        ) : null}
      </article>
      <section className="flex flex-col gap-2 rounded-[14px] border border-linie bg-surface p-5">
        <h2 className="font-display text-lg font-bold">Begründung des Autors</h2>
        <p className="text-sm text-muted">eingereicht {datumZeit(e.eingereicht_am)}</p>
        <p className="whitespace-pre-wrap break-words">{e.begruendung}</p>
      </section>
      {e.moderation ? (
        <p className="text-sm">
          Entschieden am {e.moderiert_am ? datumZeit(e.moderiert_am) : "?"}:{" "}
          <span className="font-semibold">{MODERATION_TEXT[e.moderation]}</span>
          {e.moderation_notiz ? <span className="block whitespace-pre-wrap text-muted">{e.moderation_notiz}</span> : null}
        </p>
      ) : null}
      <Entscheiden id={e.id} />
    </div>
  );
}
