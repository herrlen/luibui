import Link from "next/link";
import { redirect } from "next/navigation";

import { Ampel } from "@/components/Ampel";
import { datumZeit, STATUS_TEXT } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import { AufladenKnopf, BestaetigungSenden } from "@/components/app/KontoKnoepfe";
import type { Einzel, Guthaben, Ich, Projekt } from "@/lib/types";

import { EinzelLoeschen } from "./EinzelLoeschen";
import { Einzelpruefung } from "./Einzelpruefung";
import { NeuesProjekt } from "./NeuesProjekt";

export const metadata = { title: "Übersicht – luibui" };
export const dynamic = "force-dynamic";

export default async function Uebersicht() {
  const ich = await apiGet<Ich>("/api/v1/auth/ich");
  if (!ich.ok) redirect("/anmelden");
  const projekte = await apiGet<Projekt[]>("/api/v1/projects");
  const liste = projekte.ok ? projekte.data : [];
  const einzel = await apiGet<Einzel[]>("/api/v1/scans");
  const einzelListe = einzel.ok ? einzel.data : [];
  const guthaben = await apiGet<Guthaben>("/api/v1/guthaben");
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Übersicht</h1>
        <p className="mt-1 text-sm text-muted">Angemeldet als {ich.data.email}</p>
      </div>
      {!ich.data.email_bestaetigt ? (
        <div role="status" className="flex flex-col gap-2 rounded-[14px] border border-gelb bg-gelb-bg p-5 text-gelb">
          <p className="font-semibold">Bitte bestätige deine E-Mail-Adresse.</p>
          <p className="text-sm">
            Erst danach kannst du Dateien prüfen; der Schnellscan auf luibui.com geht auch ohne. Keine Mail bekommen? Lass
            dir den Link an {ich.data.email} schicken.
          </p>
          <BestaetigungSenden />
        </div>
      ) : null}
      {guthaben.ok && guthaben.data.aktiv && ich.data.email_bestaetigt ? (
        <div className="flex flex-wrap items-center gap-4 rounded-[14px] border border-linie bg-surface p-4">
          <p className="text-[15px]">
            Guthaben: <strong>{guthaben.data.stand} Prüfungen</strong>
          </p>
          <span className="ml-auto">
            <AufladenKnopf />
          </span>
        </div>
      ) : null}
      <Einzelpruefung />
      {einzelListe.length ? (
        <section aria-labelledby="einzelliste" className="flex flex-col gap-3">
          <h2 id="einzelliste" className="font-display text-xl font-bold">
            Einzelprüfungen
          </h2>
          <ul className="flex flex-col gap-2">
            {einzelListe.map((e) => (
              <li key={e.id} className="flex flex-wrap items-center gap-4 rounded-[14px] border border-linie bg-surface p-4">
                <Link href={`/pruefungen/${e.id}`} className="min-w-0 break-all font-semibold hover:text-petrol">
                  {e.name}
                </Link>
                <span className="ml-auto flex items-center gap-3 text-sm">
                  {e.ampel_gesamt ? (
                    <>
                      <Ampel wert={e.ampel_gesamt} />
                      <span>Note {e.note}</span>
                    </>
                  ) : (
                    <span>Prüfung {STATUS_TEXT[e.status]}</span>
                  )}
                  <span className="text-muted">{datumZeit(e.created_at)}</span>
                  {e.status === "fertig" || e.status === "fehlgeschlagen" ? (
                    <EinzelLoeschen id={e.id} name={e.name} />
                  ) : null}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <h2 className="font-display text-xl font-bold">Projekte</h2>
      <NeuesProjekt />
      {liste.length === 0 ? (
        <p className="rounded-[14px] border border-dashed border-linie p-8 text-center text-ink-2">
          Noch keine Projekte. Lege oben eines an und lade dein Paket hoch.
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {liste.map((p) => (
            <li key={p.id}>
              <Link
                href={`/projekte/${p.id}`}
                className="flex flex-wrap items-center gap-4 rounded-[14px] border border-linie bg-surface p-5 hover:border-petrol"
              >
                <span className="font-semibold">{p.name}</span>
                <span className="text-sm text-muted">{p.typ}</span>
                <span className="ml-auto flex items-center gap-3 text-sm">
                  {p.letzte_pruefung?.ampel_gesamt ? (
                    <>
                      <Ampel wert={p.letzte_pruefung.ampel_gesamt} />
                      <span>Note {p.letzte_pruefung.note}</span>
                    </>
                  ) : p.letzte_pruefung ? (
                    <span>Prüfung {STATUS_TEXT[p.letzte_pruefung.status]}</span>
                  ) : (
                    <span className="text-muted">noch nicht geprüft</span>
                  )}
                  {p.letzte_pruefung ? (
                    <span className="text-muted">{datumZeit(p.letzte_pruefung.created_at)}</span>
                  ) : null}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
