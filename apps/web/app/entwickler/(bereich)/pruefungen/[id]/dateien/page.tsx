import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { Brotkrumen } from "@/components/app/Brotkrumen";
import { datumZeit } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { Dateiliste, ScanStatus } from "@/lib/types";

export const metadata = { title: "Dateien – luibui" };
export const dynamic = "force-dynamic";

function groesse(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toLocaleString("de-DE", { maximumFractionDigits: 1 })} MB`;
}

export default async function DateienSeite({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ pfad?: string; zeile?: string }>;
}) {
  const { id } = await params;
  const { pfad, zeile } = await searchParams;
  const sid = encodeURIComponent(id);
  const [scan, liste] = await Promise.all([
    apiGet<ScanStatus>(`/api/v1/scans/${sid}`),
    apiGet<Dateiliste>(`/api/v1/scans/${sid}/dateien`),
  ]);
  if (!scan.ok) {
    if (scan.status === 401) redirect("/anmelden");
    notFound();
  }
  if (!liste.ok) notFound();
  // Link from a finding in the report: open the file by its path, at the line.
  if (pfad) {
    const treffer = liste.data.dateien.find((d) => d.path === pfad);
    if (treffer) {
      const anker = zeile && /^\d+$/.test(zeile) ? `#z${zeile}` : "";
      redirect(`/pruefungen/${sid}/dateien/${encodeURIComponent(treffer.id)}${anker}`);
    }
  }
  const dateien = liste.data.dateien;
  return (
    <div className="flex flex-col gap-4">
      <Brotkrumen
        pfad={[
          { text: "Übersicht", href: "/" },
          { text: `Prüfung vom ${datumZeit(scan.data.created_at)}`, href: `/pruefungen/${sid}` },
          { text: "Dateien" },
        ]}
      />
      <h1 className="font-display text-3xl font-bold">Dateien der geprüften Version</h1>
      {pfad ? (
        <p role="status" className="text-sm text-muted">
          Die Datei aus dem Befund ist nicht gespeichert (etwa eine Datei aus einem entpackten Paketformat).
        </p>
      ) : null}
      {!liste.data.verfuegbar ? (
        <p className="rounded-[14px] border border-linie bg-surface p-6 text-ink-2">{liste.data.grund}</p>
      ) : (
        <ul className="flex flex-col divide-y divide-linie rounded-[14px] border border-linie bg-surface">
          {dateien.map((d) => {
            const teile = d.path.split("/");
            const name = teile.pop();
            return (
              <li key={d.id}>
                <Link
                  href={`/pruefungen/${sid}/dateien/${encodeURIComponent(d.id)}`}
                  className="flex flex-wrap items-center gap-x-4 gap-y-1 px-5 py-3 text-sm hover:bg-flaeche-2"
                >
                  <span className="min-w-0 break-all font-mono">
                    {teile.length ? <span className="text-muted">{teile.join("/")}/</span> : null}
                    <span className="font-semibold">{name}</span>
                  </span>
                  <span className="ml-auto flex items-center gap-3 text-muted">
                    {d.befunde ? (
                      <span className="rounded-md bg-rot-bg px-2 py-0.5 text-xs font-semibold text-rot">
                        {d.befunde} {d.befunde === 1 ? "Befund" : "Befunde"}
                      </span>
                    ) : null}
                    <span className="tabular-nums">{groesse(d.size)}</span>
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
