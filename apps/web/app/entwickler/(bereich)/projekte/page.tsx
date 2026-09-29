import { redirect } from "next/navigation";

import { Brotkrumen } from "@/components/app/Brotkrumen";
import { apiGet } from "@/lib/server-api";
import type { Projekt } from "@/lib/types";

import { NeuesProjekt } from "../NeuesProjekt";
import { ProjektListe } from "../ProjektListe";

export const metadata = { title: "Projekte – luibui" };
export const dynamic = "force-dynamic";

export default async function Projekte() {
  const projekte = await apiGet<Projekt[]>("/api/v1/projects");
  if (!projekte.ok && projekte.status === 401) redirect("/anmelden");
  return (
    <div className="flex flex-col gap-6">
      <Brotkrumen pfad={[{ text: "Übersicht", href: "/" }, { text: "Projekte" }]} />
      <h1 className="font-display text-3xl font-bold">Projekte</h1>
      <NeuesProjekt />
      <ProjektListe projekte={projekte.ok ? projekte.data : []} />
    </div>
  );
}
