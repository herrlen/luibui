import { notFound } from "next/navigation";

import { Bericht } from "@/components/Bericht";
import { appUrl } from "@/lib/hosts";
import { apiGet } from "@/lib/server-api";
import type { ScanStatus } from "@/lib/types";

export const metadata = { title: "Schnellscan – luibui", robots: { index: false } };
export const dynamic = "force-dynamic";

export default async function SchnellscanErgebnis({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const scan = await apiGet<ScanStatus>(`/api/v1/quickscans/${encodeURIComponent(id)}`, false);
  if (!scan.ok) notFound();
  const registrieren = await appUrl("/registrieren");
  return (
    <div className="flex max-w-5xl flex-col gap-4 pt-10">
      <h1 className="font-display text-3xl font-bold">Schnellscan</h1>
      <p className="text-sm text-muted">
        Dieser Bericht ist 7 Tage unter diesem Link abrufbar. Wer den Link hat, kann ihn sehen.
      </p>
      <Bericht scan={scan.data} downloads="schnellscan" />
      <section
        aria-labelledby="intensivscan"
        className="mt-4 flex flex-col gap-3 rounded-[14px] border border-petrol bg-surface p-6 sm:flex-row sm:items-center sm:justify-between"
      >
        <div>
          <h2 id="intensivscan" className="font-display text-xl font-bold">
            Gründlich prüfen
          </h2>
          <p className="mt-1 text-sm text-muted">
            Der Intensivscan prüft zusätzlich, was der Code tut, MCP-Server, DSGVO und Verweise zwischen den Dateien, und
            kann ein Paket als geprüft freigeben. Mit bestätigter E-Mail sind drei Prüfungen gratis.
          </p>
        </div>
        <a
          href={registrieren}
          className="inline-flex h-12 shrink-0 items-center rounded-[10px] bg-petrol px-[22px] font-semibold text-white hover:bg-petrol-dunkel"
        >
          Intensivscan starten
        </a>
      </section>
    </div>
  );
}
