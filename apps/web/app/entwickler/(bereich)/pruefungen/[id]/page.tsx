import { notFound, redirect } from "next/navigation";

import { Bericht } from "@/components/Bericht";
import { Brotkrumen, type Krume } from "@/components/app/Brotkrumen";
import { datumZeit } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { Projekt, ScanStatus } from "@/lib/types";

export const metadata = { title: "Prüfbericht – luibui" };
export const dynamic = "force-dynamic";

export default async function PruefungSeite({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const scan = await apiGet<ScanStatus>(`/api/v1/scans/${encodeURIComponent(id)}`);
  if (!scan.ok) {
    if (scan.status === 401) redirect("/anmelden");
    notFound();
  }
  const s = scan.data;
  const pfad: Krume[] = [{ text: "Übersicht", href: "/" }];
  if (s.project_id) {
    const projekt = await apiGet<Projekt>(`/api/v1/projects/${encodeURIComponent(s.project_id)}`);
    pfad.push({ text: "Projekte", href: "/projekte" });
    pfad.push({ text: projekt.ok ? projekt.data.name : "Projekt", href: `/projekte/${s.project_id}` });
  } else {
    pfad.push({ text: "Einzelprüfungen", href: "/pruefungen" });
  }
  pfad.push({ text: `Prüfung vom ${datumZeit(s.created_at)}` });
  return (
    <div className="flex flex-col gap-4">
      <Brotkrumen pfad={pfad} />
      <h1 className="font-display text-3xl font-bold">
        Prüfbericht{s.bericht?.paket.name ? <span className="text-ink-2">: {s.bericht.paket.name}</span> : null}
      </h1>
      <Bericht scan={s} downloads="bereich" />
    </div>
  );
}
