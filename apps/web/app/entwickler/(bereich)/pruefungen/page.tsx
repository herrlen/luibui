import { redirect } from "next/navigation";

import { Brotkrumen } from "@/components/app/Brotkrumen";
import { apiGet } from "@/lib/server-api";
import type { Einzel } from "@/lib/types";

import { EinzelListe } from "../EinzelListe";
import { Einzelpruefung } from "../Einzelpruefung";

export const metadata = { title: "Einzelprüfungen – luibui" };
export const dynamic = "force-dynamic";

export default async function Einzelpruefungen() {
  const einzel = await apiGet<Einzel[]>("/api/v1/scans");
  if (!einzel.ok && einzel.status === 401) redirect("/anmelden");
  const liste = einzel.ok ? einzel.data : [];
  return (
    <div className="flex flex-col gap-6">
      <Brotkrumen pfad={[{ text: "Übersicht", href: "/" }, { text: "Einzelprüfungen" }]} />
      <h1 className="font-display text-3xl font-bold">Einzelprüfungen</h1>
      <Einzelpruefung />
      {liste.length ? (
        <EinzelListe pruefungen={liste} />
      ) : (
        <p className="text-sm text-muted">Noch keine Einzelprüfung.</p>
      )}
    </div>
  );
}
