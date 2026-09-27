import { notFound } from "next/navigation";

import { Bericht } from "@/components/Bericht";
import { apiGet } from "@/lib/server-api";
import type { ScanStatus } from "@/lib/types";

export const metadata = { title: "Schnellscan – luibui", robots: { index: false } };
export const dynamic = "force-dynamic";

export default async function SchnellscanErgebnis({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const scan = await apiGet<ScanStatus>(`/api/v1/quickscans/${encodeURIComponent(id)}`, false);
  if (!scan.ok) notFound();
  return (
    <div className="flex max-w-5xl flex-col gap-4 pt-10">
      <h1 className="font-display text-3xl font-bold">Schnellscan</h1>
      <p className="text-sm text-muted">
        Dieser Bericht ist 7 Tage unter diesem Link abrufbar. Wer den Link hat, kann ihn sehen.
      </p>
      <Bericht scan={scan.data} />
    </div>
  );
}
