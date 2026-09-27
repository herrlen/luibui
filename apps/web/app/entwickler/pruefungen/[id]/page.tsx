import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { Bericht } from "@/components/Bericht";
import { apiGet } from "@/lib/server-api";
import type { ScanStatus } from "@/lib/types";

export const metadata = { title: "Prüfbericht – luibui" };
export const dynamic = "force-dynamic";

export default async function PruefungSeite({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const scan = await apiGet<ScanStatus>(`/api/v1/scans/${encodeURIComponent(id)}`);
  if (!scan.ok) {
    if (scan.status === 401) redirect("/anmelden");
    notFound();
  }
  return (
    <div className="flex flex-col gap-4">
      {scan.data.project_id ? (
        <Link href={`/projekte/${scan.data.project_id}`} className="text-sm text-petrol">
          ← Projekt
        </Link>
      ) : (
        <Link href="/" className="text-sm text-petrol">
          ← Übersicht
        </Link>
      )}
      <h1 className="font-display text-3xl font-bold">Prüfbericht</h1>
      <Bericht scan={scan.data} />
    </div>
  );
}
