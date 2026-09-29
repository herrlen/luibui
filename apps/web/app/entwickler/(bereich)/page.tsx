import Link from "next/link";
import { redirect } from "next/navigation";

import { Brotkrumen } from "@/components/app/Brotkrumen";
import { SCHWERE_TEXT } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import { AufladenKnopf, BestaetigungSenden } from "@/components/app/KontoKnoepfe";
import type { Einzel, Guthaben, Ich, OffenerBefund, Projekt } from "@/lib/types";

import { EinzelListe } from "./EinzelListe";
import { Einzelpruefung } from "./Einzelpruefung";
import { ProjektListe } from "./ProjektListe";

export const metadata = { title: "Übersicht – luibui" };
export const dynamic = "force-dynamic";

const SICHTBAR = 10;
const LETZTE_EINZEL = 5;

/** Colour plus shape and word, never colour alone (ENTWICKLERREGELN A5/F6). */
function SchwereMarke({ schwere }: { schwere: "K" | "H" }) {
  const stil = schwere === "K" ? "bg-rot-bg text-rot" : "bg-gelb-bg text-gelb";
  return (
    <span className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-0.5 text-sm font-semibold ${stil}`}>
      <span aria-hidden="true">{schwere === "K" ? "■" : "▲"}</span>
      {SCHWERE_TEXT[schwere]}
    </span>
  );
}

export default async function Uebersicht() {
  const ich = await apiGet<Ich>("/api/v1/auth/ich");
  if (!ich.ok) redirect("/anmelden");
  const projekte = await apiGet<Projekt[]>("/api/v1/projects");
  const liste = projekte.ok ? projekte.data : [];
  const einzel = await apiGet<Einzel[]>("/api/v1/scans");
  const einzelListe = einzel.ok ? einzel.data : [];
  const guthaben = await apiGet<Guthaben>("/api/v1/guthaben");
  const offen = await apiGet<OffenerBefund[]>("/api/v1/projects/offene-befunde");
  const offenListe = offen.ok ? offen.data : [];
  return (
    <div className="flex flex-col gap-6">
      <Brotkrumen pfad={[{ text: "Übersicht" }]} />
      <h1 className="font-display text-3xl font-bold">Übersicht</h1>
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
      <div className="grid items-start gap-6 xl:grid-cols-2">
        <section aria-labelledby="projekte" className="flex flex-col gap-3">
          <div className="flex flex-wrap items-baseline gap-3">
            <h2 id="projekte" className="font-display text-xl font-bold">
              Projekte
            </h2>
            <Link href="/projekte#neu" className="ml-auto text-sm font-semibold text-petrol hover:underline">
              + Neues Projekt
            </Link>
          </div>
          <ProjektListe projekte={liste} />
        </section>
        <Einzelpruefung />
      </div>
      {offenListe.length ? (
        <section aria-labelledby="offen" className="flex flex-col gap-3">
          <h2 id="offen" className="font-display text-xl font-bold">
            Offene kritische und hohe Befunde
          </h2>
          <p className="text-sm text-muted">Aus der jeweils letzten fertigen Prüfung deiner Projekte.</p>
          <ul className="flex flex-col gap-2">
            {offenListe.slice(0, SICHTBAR).map((b, i) => (
              <li key={`${b.scan_id}-${i}`}>
                <Link
                  href={`/pruefungen/${b.scan_id}`}
                  className="flex flex-wrap items-center gap-3 rounded-[14px] border border-linie bg-surface p-4 hover:border-petrol"
                >
                  <SchwereMarke schwere={b.schwere} />
                  <span className="min-w-0 font-semibold">{b.titel}</span>
                  <span className="ml-auto min-w-0 break-all text-sm text-muted">
                    {b.projekt}
                    {b.datei ? ` · ${b.datei}${b.zeile ? `:${b.zeile}` : ""}` : ""}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
          {offenListe.length > SICHTBAR ? (
            <p className="text-sm text-muted">
              Und {offenListe.length - SICHTBAR} weitere{offenListe.length >= 50 ? " oder mehr" : ""}, siehe die Projekte unten.
            </p>
          ) : null}
        </section>
      ) : null}
      {einzelListe.length ? (
        <section aria-labelledby="einzelliste" className="flex flex-col gap-3">
          <div className="flex flex-wrap items-baseline gap-3">
            <h2 id="einzelliste" className="font-display text-xl font-bold">
              Letzte Einzelprüfungen
            </h2>
            {einzelListe.length > LETZTE_EINZEL ? (
              <Link href="/pruefungen" className="ml-auto text-sm font-semibold text-petrol hover:underline">
                Alle {einzelListe.length} ansehen
              </Link>
            ) : null}
          </div>
          <EinzelListe pruefungen={einzelListe.slice(0, LETZTE_EINZEL)} />
        </section>
      ) : null}
    </div>
  );
}
