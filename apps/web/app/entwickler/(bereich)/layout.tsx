import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { AufladenDialog } from "@/components/app/Aufladen";
import { Explorer, Hauptleiste } from "@/components/app/Leisten";
import { apiGet } from "@/lib/server-api";
import type { Ich, Projekt } from "@/lib/types";

export default async function BereichLayout({ children }: { children: ReactNode }) {
  const ich = await apiGet<Ich>("/api/v1/auth/ich");
  if (!ich.ok && ich.status === 401) redirect("/anmelden");
  const projekte = await apiGet<Projekt[]>("/api/v1/projects");
  const eintraege = (projekte.ok ? projekte.data : []).map((p) => ({
    id: p.id,
    name: p.name,
    ampel: p.letzte_pruefung?.ampel_gesamt ?? null,
    offenK: p.offen_k ?? 0,
    offenH: p.offen_h ?? 0,
  }));
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[232px_264px_minmax(0,1fr)]">
      <Hauptleiste email={ich.ok ? ich.data.email : ""} admin={ich.ok && ich.data.admin === true} />
      <Explorer projekte={eintraege} />
      <main id="inhalt" className="min-w-0 px-4 py-6 sm:px-8 lg:px-10 lg:py-8">
        <div className="mx-auto max-w-5xl">{children}</div>
      </main>
      <AufladenDialog />
    </div>
  );
}
