import { redirect } from "next/navigation";

import { apiGet } from "@/lib/server-api";
import Link from "next/link";

import { AufladenKnopf } from "@/components/app/KontoKnoepfe";
import { datumZeit } from "@/lib/format";
import type { Guthaben, Ich } from "@/lib/types";

import { Abmelden } from "./Abmelden";
import { type TokenInfo, Tokens } from "./Tokens";

export const metadata = { title: "Konto – luibui" };
export const dynamic = "force-dynamic";

export default async function Konto() {
  const ich = await apiGet<Ich>("/api/v1/auth/ich");
  if (!ich.ok) redirect("/anmelden");
  const tokens = await apiGet<TokenInfo[]>("/api/v1/tokens");
  const guthaben = await apiGet<Guthaben>("/api/v1/guthaben");
  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-display text-3xl font-bold">Konto</h1>
      <section className="rounded-[14px] border border-linie bg-surface p-6 text-sm">
        <p>
          <span className="font-semibold">E-Mail:</span> {ich.data.email}
        </p>
        <p className="mt-1">
          <span className="font-semibold">Zwei-Faktor-Anmeldung:</span> {ich.data.totp_aktiv ? "aktiv" : "nicht aktiv"}
        </p>
      </section>
      {guthaben.ok && guthaben.data.aktiv ? (
        <section aria-labelledby="guthaben" className="flex flex-col gap-3 rounded-[14px] border border-linie bg-surface p-6">
          <div className="flex flex-wrap items-center gap-4">
            <h2 id="guthaben" className="font-display text-xl font-bold">
              Guthaben: {guthaben.data.stand} Prüfungen
            </h2>
            <span className="ml-auto">
              <AufladenKnopf />
            </span>
          </div>
          {guthaben.data.kaeufe.length ? (
            <ul className="flex flex-col divide-y divide-linie text-sm">
              {guthaben.data.kaeufe.map((k) => (
                <li key={k.id} className="flex flex-wrap items-center gap-4 py-2">
                  <span>{k.bezahlt_am ? datumZeit(k.bezahlt_am) : ""}</span>
                  <span>{k.pruefungen} Prüfungen</span>
                  <span>
                    {Math.floor(k.betrag_cent / 100)},{String(k.betrag_cent % 100).padStart(2, "0")} €
                  </span>
                  <Link href={`/konto/beleg/${k.id}`} className="ml-auto text-petrol underline">
                    Beleg
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted">Noch keine Käufe.</p>
          )}
        </section>
      ) : null}
      <Tokens tokens={tokens.ok ? tokens.data : []} />
      <div>
        <Abmelden />
      </div>
    </div>
  );
}
