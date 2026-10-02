import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { Ampel } from "@/components/Ampel";
import { Brotkrumen } from "@/components/app/Brotkrumen";
import { datumZeit, SCHWERE_TEXT, UMFANG_TEXT } from "@/lib/format";
import { SCHWERE_STIL } from "@/lib/schwere";
import { apiGet } from "@/lib/server-api";
import type { Projekt, Vergleich, VergleichEintrag, VergleichSeite } from "@/lib/types";

export const metadata = { title: "Prüfungen vergleichen – luibui" };
export const dynamic = "force-dynamic";

const UUID = /^[0-9a-f-]{36}$/i;

// Two checks of a project side by side (S3-5): new, fixed and unchanged findings, matched by
// fingerprint. Titles and paths come from packages: plain text, React escapes them.
export default async function VergleichSeiteRoute({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ von?: string; bis?: string }>;
}) {
  const { id } = await params;
  const { von, bis } = await searchParams;
  const projekt = await apiGet<Projekt>(`/api/v1/projects/${encodeURIComponent(id)}`);
  if (!projekt.ok) {
    if (projekt.status === 401) redirect("/anmelden");
    notFound();
  }
  const auswahl = von && bis && UUID.test(von) && UUID.test(bis) ? `?von=${von}&bis=${bis}` : "";
  const r = await apiGet<Vergleich>(`/api/v1/projects/${encodeURIComponent(id)}/vergleich${auswahl}`);
  const pfad = [
    { text: "Übersicht", href: "/" },
    { text: "Projekte", href: "/projekte" },
    { text: projekt.data.name, href: `/projekte/${projekt.data.id}` },
    { text: "Vergleich" },
  ];
  if (!r.ok) {
    if (r.status === 409) {
      return (
        <div className="flex flex-col gap-4">
          <Brotkrumen pfad={pfad} />
          <h1 className="font-display text-3xl font-bold">Prüfungen vergleichen</h1>
          <p className="rounded-[14px] border border-linie bg-surface p-5 text-sm">{r.fehler.text}</p>
        </div>
      );
    }
    notFound();
  }
  const v = r.data;
  const diff = v.von.note !== null && v.bis.note !== null ? v.bis.note - v.von.note : null;
  return (
    <div className="flex flex-col gap-6">
      <Brotkrumen pfad={pfad} />
      <h1 className="font-display text-3xl font-bold">Prüfungen vergleichen</h1>
      <section aria-label="Gegenüberstellung" className="grid gap-3 sm:grid-cols-[1fr_auto_1fr] sm:items-center">
        <Seite titel="Vorher" s={v.von} />
        <p className="text-center text-sm text-muted" aria-label="Änderung der Note">
          {diff === null ? "→" : diff === 0 ? "Note unverändert" : `Note ${diff > 0 ? "+" : "−"}${Math.abs(diff)}`}
        </p>
        <Seite titel="Nachher" s={v.bis} />
      </section>
      {!v.gleicher_umfang ? (
        <p className="rounded-lg border border-gelb bg-gelb-bg p-3 text-sm text-gelb">
          Die Prüfungen haben unterschiedlichen Umfang ({UMFANG_TEXT[v.von.pruefumfang] ?? v.von.pruefumfang} und{" "}
          {UMFANG_TEXT[v.bis.pruefumfang] ?? v.bis.pruefumfang}). Was fehlt, kann auch außerhalb der Auswahl liegen.
        </p>
      ) : null}
      <Liste titel="Neu" leer="Keine neuen Befunde." eintraege={v.neu} />
      <Liste titel="Behoben" leer="Nichts behoben." eintraege={v.behoben} />
      <details>
        <summary className="cursor-pointer font-display text-xl font-bold">Unverändert ({v.unveraendert.length})</summary>
        <div className="mt-3">
          <Eintraege eintraege={v.unveraendert} leer="Keine." />
        </div>
      </details>
    </div>
  );
}

function Seite({ titel, s }: { titel: string; s: VergleichSeite }) {
  return (
    <Link
      href={`/pruefungen/${s.scan_id}`}
      className="flex flex-col gap-2 rounded-[14px] border border-linie bg-surface p-5 hover:border-petrol"
    >
      <span className="text-xs text-muted">
        {titel} · {datumZeit(s.created_at)}
      </span>
      <span className="flex items-center gap-3">
        {s.ampel_gesamt ? <Ampel wert={s.ampel_gesamt} /> : null}
        <span className="font-display text-2xl font-bold">{s.note ?? "–"}</span>
        <span className="text-sm text-muted">/100</span>
      </span>
    </Link>
  );
}

function Liste({ titel, leer, eintraege }: { titel: string; leer: string; eintraege: VergleichEintrag[] }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="font-display text-xl font-bold">
        {titel} ({eintraege.length})
      </h2>
      <Eintraege eintraege={eintraege} leer={leer} />
    </section>
  );
}

function Eintraege({ eintraege, leer }: { eintraege: VergleichEintrag[]; leer: string }) {
  if (!eintraege.length) return <p className="text-sm text-muted">{leer}</p>;
  return (
    <ul className="flex flex-col gap-2">
      {eintraege.map((e) => (
        <li
          key={e.fingerprint}
          className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-[14px] border border-linie bg-surface px-5 py-3"
        >
          <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${SCHWERE_STIL[e.schwere] ?? ""}`}>
            {SCHWERE_TEXT[e.schwere] ?? e.schwere}
          </span>
          <span className="min-w-0 flex-1 font-medium">{e.titel}</span>
          <span className="break-all font-mono text-xs text-muted">
            {e.datei ? `${e.datei}${e.zeile ? `:${e.zeile}` : ""}` : "ganzes Paket"}
          </span>
        </li>
      ))}
    </ul>
  );
}
