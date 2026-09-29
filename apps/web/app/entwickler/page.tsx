import Link from "next/link";
import { redirect } from "next/navigation";

import { Ampel } from "@/components/Ampel";
import { datumZeit, SCHWERE_TEXT, STATUS_TEXT } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import { AufladenKnopf, BestaetigungSenden } from "@/components/app/KontoKnoepfe";
import type { Einzel, Guthaben, Ich, OffenerBefund, Projekt } from "@/lib/types";

import { EinzelLoeschen } from "./EinzelLoeschen";
import { Einzelpruefung } from "./Einzelpruefung";
import { NeuesProjekt } from "./NeuesProjekt";

export const metadata = { title: "Übersicht – luibui" };
export const dynamic = "force-dynamic";

const SICHTBAR = 10;

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

function OffeneZahl({ k = 0, h = 0 }: { k?: number; h?: number }) {
  if (!k && !h) return null;
  const teile = [k ? `${k} kritisch` : "", h ? `${h} hoch` : ""].filter(Boolean);
  return <span className={k ? "font-semibold text-rot" : "font-semibold text-gelb"}>{teile.join(" · ")} offen</span>;
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
                <span className="ml-auto flex flex-wrap items-center gap-3 text-sm">
                  <OffeneZahl k={p.offen_k} h={p.offen_h} />
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
