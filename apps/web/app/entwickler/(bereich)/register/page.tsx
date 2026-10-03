import Link from "next/link";
import { redirect } from "next/navigation";

import { Brotkrumen } from "@/components/app/Brotkrumen";
import { datumZeit } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { PaketVersion } from "@/lib/types";

import { Zurueckziehen } from "./Zurueckziehen";

export const metadata = { title: "Register – luibui" };
export const dynamic = "force-dynamic";

export default async function RegisterSeite() {
  const meine = await apiGet<PaketVersion[]>("/api/v1/register/meine");
  if (!meine.ok) redirect("/anmelden");
  const pakete = new Map<string, PaketVersion[]>();
  for (const v of meine.data) pakete.set(v.paket, [...(pakete.get(v.paket) ?? []), v]);
  return (
    <div className="flex flex-col gap-4">
      <Brotkrumen pfad={[{ text: "Übersicht", href: "/" }, { text: "Register" }]} />
      <h1 className="font-display text-3xl font-bold">Meine Pakete im Register</h1>
      <p className="max-w-3xl text-sm text-muted">
        Veröffentlicht wird aus einem Prüfbericht heraus: Paket-Prüfung mit <span className="font-mono">luibui.json</span>, nicht
        gesperrt, SPDX-Lizenz. Name und Version stehen in <span className="font-mono">luibui.json</span>, der Namespace muss
        dir gehören (<Link href="/konto#namespaces" className="text-petrol underline">Namespaces</Link>). Jede Version ist
        signiert und lässt sich nicht mehr ändern, nur zurückziehen.
      </p>
      {pakete.size === 0 ? (
        <p className="rounded-[14px] border border-linie bg-surface p-6 text-ink-2">Noch keine Pakete veröffentlicht.</p>
      ) : (
        [...pakete.entries()].map(([paket, versionen]) => (
          <section key={paket} className="flex flex-col gap-3 rounded-[14px] border border-linie bg-surface p-6">
            <h2 className="font-mono text-lg font-bold">{paket}</h2>
            <ul className="flex flex-col divide-y divide-linie text-sm">
              {versionen.map((v) => (
                <li key={v.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2">
                  <span className="font-mono font-semibold">{v.version}</span>
                  <span className="text-muted">{datumZeit(v.veroeffentlicht_am)}</span>
                  <Link href={`/pruefungen/${encodeURIComponent(v.scan_id)}`} className="text-petrol underline">
                    Prüfbericht
                  </Link>
                  <span className="break-all font-mono text-xs text-muted" title="SHA-256 des Archivs">
                    {v.archiv_sha256.slice(0, 16)}…
                  </span>
                  <span className="ml-auto">
                    {v.zurueckgezogen_am ? (
                      <span className="text-muted">zurückgezogen am {datumZeit(v.zurueckgezogen_am)}</span>
                    ) : (
                      <Zurueckziehen id={v.id} version={v.version} />
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        ))
      )}
    </div>
  );
}
