import { notFound, redirect } from "next/navigation";

import { Brotkrumen } from "@/components/app/Brotkrumen";
import { Dateiansicht } from "@/components/app/Dateiansicht";
import { apiGet } from "@/lib/server-api";
import type { DateiAnsicht } from "@/lib/types";

export const metadata = { title: "Datei – luibui" };
export const dynamic = "force-dynamic";

export default async function DateiSeite({ params }: { params: Promise<{ id: string; datei: string }> }) {
  const { id, datei } = await params;
  const sid = encodeURIComponent(id);
  const fid = encodeURIComponent(datei);
  const ansicht = await apiGet<DateiAnsicht>(`/api/v1/scans/${sid}/dateien/${fid}`);
  if (!ansicht.ok) {
    if (ansicht.status === 401) redirect("/anmelden");
    if (ansicht.status === 413)
      return <p className="rounded-[14px] border border-linie bg-surface p-6">Dateien über 50 MB lassen sich hier nicht öffnen.</p>;
    notFound();
  }
  return (
    <div className="flex flex-col gap-4">
      <Brotkrumen
        pfad={[
          { text: "Übersicht", href: "/" },
          { text: "Prüfung", href: `/pruefungen/${sid}` },
          { text: "Dateien", href: `/pruefungen/${sid}/dateien` },
          { text: ansicht.data.path },
        ]}
      />
      <Dateiansicht datei={ansicht.data} download={`/api/v1/scans/${sid}/dateien/${fid}/download`} />
    </div>
  );
}
