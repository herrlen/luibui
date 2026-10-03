import type { Metadata } from "next";
import Link from "next/link";

import { Ampel } from "@/components/Ampel";
import { datumZeit } from "@/lib/format";
import { apiGet } from "@/lib/server-api";

export const metadata: Metadata = {
  title: "Register – luibui",
  description: "Geprüfte KI-Skills, Plugins, Tools und MCP-Server mit Ampel, Note und Rechte-Label.",
  alternates: { canonical: "/pakete" },
};
export const dynamic = "force-dynamic";

type Eintrag = {
  paket: string;
  version: string;
  beschreibung: string | null;
  typ: string | null;
  ampel: string | null;
  note: number | null;
  veroeffentlicht_am: string;
};

export default async function Register() {
  const r = await apiGet<Eintrag[]>("/api/v1/register/pakete", false);
  const pakete = r.ok ? r.data : [];
  return (
    <div className="flex max-w-5xl flex-col gap-6 pt-10">
      <h1 className="font-display text-4xl font-bold">Register</h1>
      <p className="max-w-3xl text-lg text-ink-2">
        Pakete, die ihre Autoren nach einer Prüfung bei luibui veröffentlicht haben. Jede Version ist signiert und zeigt
        den Bericht, mit dem sie veröffentlicht wurde. Grün heißt „keine bekannten Befunde“, nie „sicher“.
      </p>
      {!r.ok ? (
        <p className="rounded-[14px] border border-linie bg-surface p-6 text-ink-2">Das Register antwortet gerade nicht.</p>
      ) : pakete.length === 0 ? (
        <p className="rounded-[14px] border border-linie bg-surface p-6 text-ink-2">Noch keine Pakete veröffentlicht.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {pakete.map((p) => (
            <li key={p.paket}>
              <Link
                href={`/pakete/${p.paket}`}
                className="flex flex-wrap items-start gap-x-6 gap-y-2 rounded-[14px] border border-linie bg-surface p-5 hover:border-petrol"
              >
                <span className="flex min-w-0 flex-1 flex-col gap-1">
                  <span className="break-all font-mono text-lg font-semibold">{p.paket}</span>
                  {p.beschreibung ? <span className="text-sm text-ink-2">{p.beschreibung}</span> : null}
                  <span className="text-xs text-muted">
                    {p.typ ? `${p.typ} · ` : ""}Version {p.version} · {datumZeit(p.veroeffentlicht_am)}
                  </span>
                </span>
                <span className="flex items-center gap-3">
                  {p.ampel ? (
                    <span className="w-[104px]">
                      <Ampel wert={p.ampel} />
                    </span>
                  ) : null}
                  {p.note !== null ? <span className="font-display text-2xl font-bold tabular-nums">{p.note}</span> : null}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
