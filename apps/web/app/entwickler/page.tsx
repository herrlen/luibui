import Link from "next/link";
import { redirect } from "next/navigation";

import { Ampel } from "@/components/Ampel";
import { datumZeit, STATUS_TEXT } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { Ich, Projekt } from "@/lib/types";

import { NeuesProjekt } from "./NeuesProjekt";

export const metadata = { title: "Übersicht – luibui" };
export const dynamic = "force-dynamic";

export default async function Uebersicht() {
  const ich = await apiGet<Ich>("/api/v1/auth/ich");
  if (!ich.ok) redirect("/anmelden");
  const projekte = await apiGet<Projekt[]>("/api/v1/projects");
  const liste = projekte.ok ? projekte.data : [];
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Deine Projekte</h1>
        <p className="mt-1 text-sm text-muted">Angemeldet als {ich.data.email}</p>
      </div>
      <NeuesProjekt />
      {liste.length === 0 ? (
        <p className="rounded-[14px] border border-dashed border-linie p-8 text-center text-ink-2">
          Noch keine Projekte. Lege oben eines an und lade dein Paket hoch.
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {liste.map((p) => (
            <li key={p.id}>
              <Link
                href={`/projekte/${p.id}`}
                className="flex flex-wrap items-center gap-4 rounded-[14px] border border-linie bg-surface p-5 hover:border-petrol"
              >
                <span className="font-semibold">{p.name}</span>
                <span className="text-sm text-muted">{p.typ}</span>
                <span className="ml-auto flex items-center gap-3 text-sm">
                  {p.letzte_pruefung?.ampel_gesamt ? (
                    <>
                      <Ampel wert={p.letzte_pruefung.ampel_gesamt} />
                      <span>Note {p.letzte_pruefung.note}</span>
                    </>
                  ) : p.letzte_pruefung ? (
                    <span>Prüfung {STATUS_TEXT[p.letzte_pruefung.status]}</span>
                  ) : (
                    <span className="text-muted">noch nicht geprüft</span>
                  )}
                  {p.letzte_pruefung ? (
                    <span className="text-muted">{datumZeit(p.letzte_pruefung.created_at)}</span>
                  ) : null}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
