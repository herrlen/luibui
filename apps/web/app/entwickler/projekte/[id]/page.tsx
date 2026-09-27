import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { Ampel } from "@/components/Ampel";
import { datumZeit, STATUS_TEXT, UMFANG_TEXT } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { Projekt, Pruefungskurz } from "@/lib/types";

import { Upload } from "./Upload";

export const dynamic = "force-dynamic";

export default async function ProjektSeite({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const projekt = await apiGet<Projekt>(`/api/v1/projects/${encodeURIComponent(id)}`);
  if (!projekt.ok) {
    if (projekt.status === 401) redirect("/anmelden");
    notFound();
  }
  const scans = await apiGet<Pruefungskurz[]>(`/api/v1/projects/${encodeURIComponent(id)}/scans`);
  const liste = scans.ok ? scans.data : [];
  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link href="/" className="text-sm text-petrol">
          ← Übersicht
        </Link>
        <h1 className="mt-2 font-display text-3xl font-bold">{projekt.data.name}</h1>
        <p className="text-sm text-muted">
          {projekt.data.typ}
          {projekt.data.nach_pruefung_loeschen ? " · Dateien werden nach der Prüfung gelöscht" : " · Dateien verschlüsselt gespeichert"}
        </p>
      </div>
      <Upload projektId={projekt.data.id} />
      <section>
        <h2 className="font-display text-xl font-bold">Prüfungen</h2>
        {liste.length === 0 ? (
          <p className="mt-2 text-sm text-muted">Noch keine Prüfung.</p>
        ) : (
          <ul className="mt-3 flex flex-col gap-2">
            {liste.map((s) => (
              <li key={s.id}>
                <Link
                  href={`/pruefungen/${s.id}`}
                  className="flex flex-wrap items-center gap-4 rounded-[14px] border border-linie bg-surface px-5 py-3 hover:border-petrol"
                >
                  <span className="text-sm">{datumZeit(s.created_at)}</span>
                  <span className="text-sm text-muted">{UMFANG_TEXT[s.pruefumfang] ?? s.pruefumfang}</span>
                  <span className="ml-auto flex items-center gap-3 text-sm">
                    {s.ampel_gesamt ? <Ampel wert={s.ampel_gesamt} /> : <span>{STATUS_TEXT[s.status]}</span>}
                    {s.note !== null ? <span>Note {s.note}</span> : null}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
