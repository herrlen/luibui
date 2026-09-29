import { notFound } from "next/navigation";

import { ReportView } from "@/components/report/ReportView";
import { datumZeit } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { Bericht } from "@/lib/types";

// A report someone shared by link (S2-12). The link is the permission; no account data is shown.
export const metadata = { title: "Geteilter Prüfbericht – luibui", robots: { index: false, follow: false } };
export const dynamic = "force-dynamic";

export default async function GeteilterBericht({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const r = await apiGet<{ bericht: Bericht; geprueft_am: string | null }>(
    `/api/v1/geteilt/${encodeURIComponent(token)}`,
    false,
  );
  if (!r.ok) notFound();
  const b = r.data.bericht;
  return (
    <div className="flex max-w-5xl flex-col gap-4 pt-10">
      <h1 className="font-display text-3xl font-bold">Geteilter Prüfbericht</h1>
      <p className="text-sm text-muted">
        Jemand hat diesen Bericht mit dir geteilt. Er zeigt den Stand der Prüfung
        {r.data.geprueft_am ? ` vom ${datumZeit(r.data.geprueft_am)}` : ""}; spätere Änderungen am Paket sind darin nicht
        enthalten.
      </p>
      <ReportView bericht={b} />
    </div>
  );
}
