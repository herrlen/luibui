import { notFound, redirect } from "next/navigation";

import { Brotkrumen } from "@/components/app/Brotkrumen";
import { datumZeit } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { Einspruch } from "@/lib/types";

import { Entscheiden } from "./Entscheiden";

export const metadata = { title: "Einsprüche – luibui" };
export const dynamic = "force-dynamic";

const ERGEBNIS: Record<string, string> = {
  fehlalarm: "Fehlalarm, Regel wird angepasst",
  bestritten: "Bleibt: vom Autor bestritten",
};

// Moderation of disputed findings (S3-7, Konzept §5). Admins only: for everybody else the API
// answers 404 and so does this page. Rule, title, place and the author's reason, never the report.
export default async function Einsprueche() {
  const r = await apiGet<Einspruch[]>("/api/v1/admin/einsprueche");
  if (!r.ok) {
    if (r.status === 401) redirect("/anmelden");
    notFound();
  }
  const wartend = r.data.filter((e) => e.moderation === null);
  const erledigt = r.data.filter((e) => e.moderation !== null);
  return (
    <div className="flex flex-col gap-6">
      <Brotkrumen pfad={[{ text: "Übersicht", href: "/" }, { text: "Einsprüche" }]} />
      <h1 className="font-display text-3xl font-bold">Einsprüche</h1>
      <p className="text-sm text-muted">
        Autoren halten diese Befunde für Fehlalarme. Bei „Fehlalarm“ die Regel anpassen und im Prüfkatalog begründen.
        Jeder Aufruf dieser Seite wird protokolliert.
      </p>
      <section aria-labelledby="wartend" className="flex flex-col gap-3">
        <h2 id="wartend" className="font-display text-xl font-bold">
          Offen ({wartend.length})
        </h2>
        {wartend.length ? (
          wartend.map((e) => <Karte key={e.id} e={e} />)
        ) : (
          <p className="rounded-[14px] border border-linie bg-surface p-5 text-sm">Keine offenen Einsprüche.</p>
        )}
      </section>
      {erledigt.length ? (
        <section aria-labelledby="erledigt" className="flex flex-col gap-3">
          <h2 id="erledigt" className="font-display text-xl font-bold">
            Entschieden ({erledigt.length})
          </h2>
          {erledigt.map((e) => (
            <Karte key={e.id} e={e} />
          ))}
        </section>
      ) : null}
    </div>
  );
}

// Everything here comes from packages and authors: plain text only, React escapes it.
function Karte({ e }: { e: Einspruch }) {
  return (
    <article className="flex flex-col gap-2 rounded-[14px] border border-linie bg-surface p-5">
      <p className="font-mono text-xs text-muted">
        {e.rule_id} · {e.datei ? `${e.datei}${e.zeile ? `:${e.zeile}` : ""}` : "ganzes Paket"} · eingereicht{" "}
        {datumZeit(e.updated_at)}
      </p>
      <h3 className="text-base font-semibold">{e.titel}</h3>
      <p className="whitespace-pre-wrap text-sm">
        <span className="font-semibold">Begründung des Autors: </span>
        {e.begruendung}
      </p>
      {e.moderation ? (
        <p className="text-sm text-muted">
          {ERGEBNIS[e.moderation]}
          {e.moderiert_am ? ` (${datumZeit(e.moderiert_am)})` : ""}
        </p>
      ) : (
        <Entscheiden id={e.id} />
      )}
    </article>
  );
}
