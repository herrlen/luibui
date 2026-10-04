import { notFound, redirect } from "next/navigation";

import { Brotkrumen } from "@/components/app/Brotkrumen";
import { Drucken } from "@/components/app/Drucken";
import { datumZeit } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { Beleg } from "@/lib/types";

export const metadata = { title: "Beleg – luibui" };
export const dynamic = "force-dynamic";

function euro(cent: number): string {
  return `${Math.floor(cent / 100)},${String(cent % 100).padStart(2, "0")} €`;
}

export default async function BelegSeite({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const b = await apiGet<Beleg>(`/api/v1/guthaben/belege/${encodeURIComponent(id)}`);
  if (!b.ok) {
    if (b.status === 401) redirect("/anmelden");
    notFound();
  }
  const d = b.data;
  const nummer = `LB-${String(d.belegnummer).padStart(6, "0")}`;
  return (
    <div className="flex flex-col gap-4">
      <Brotkrumen pfad={[{ text: "Übersicht", href: "/" }, { text: "Konto", href: "/konto" }, { text: `Beleg ${nummer}` }]} />
    <article className="flex max-w-2xl flex-col gap-6 rounded-[14px] border border-linie bg-surface p-8 print:border-0 print:p-0">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="text-sm leading-[1.6]">
          <p className="font-display text-2xl font-bold">luibui</p>
          <p>Studio Luy UG (haftungsbeschränkt)</p>
          <p>Norderreihe 21, 22767 Hamburg</p>
          <p>hallo@luibui.com</p>
        </div>
        <div className="text-right text-sm">
          <p className="font-semibold">Beleg Nr. LB-{String(d.belegnummer).padStart(6, "0")}</p>
          <p>{datumZeit(d.datum)}</p>
        </div>
      </div>
      <p className="text-sm">Käufer: {d.kaeufer_email ?? "–"}</p>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-linie text-left">
            <th className="py-2 font-semibold">Leistung</th>
            <th className="py-2 text-right font-semibold">Betrag</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-b border-linie">
            <td className="py-2">{d.beschreibung}</td>
            <td className="py-2 text-right">{euro(d.betrag_cent)}</td>
          </tr>
          <tr>
            <td className="py-2 font-semibold">Gesamt</td>
            <td className="py-2 text-right font-semibold">{euro(d.betrag_cent)}</td>
          </tr>
        </tbody>
      </table>
      <p className="text-sm">Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.</p>
      <p className="text-sm text-muted">
        Bezahlt über PayPal{d.paypal_transaktion ? `, Transaktion ${d.paypal_transaktion}` : ""}. Leistung: Bereitstellung von
        Prüfguthaben am {datumZeit(d.datum)}.
      </p>
      <div className="print:hidden">
        <Drucken />
      </div>
    </article>
    </div>
  );
}
