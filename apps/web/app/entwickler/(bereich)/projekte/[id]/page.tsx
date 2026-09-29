import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { Ampel } from "@/components/Ampel";
import { Brotkrumen } from "@/components/app/Brotkrumen";
import { datumZeit, groesse, STATUS_TEXT, UMFANG_TEXT } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { Projekt, Pruefungskurz, Version } from "@/lib/types";

import { ProjektLoeschen } from "./ProjektLoeschen";
import { Upload } from "./Upload";
import { VersionLoeschen } from "./VersionLoeschen";

export const dynamic = "force-dynamic";

export default async function ProjektSeite({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const projekt = await apiGet<Projekt>(`/api/v1/projects/${encodeURIComponent(id)}`);
  if (!projekt.ok) {
    if (projekt.status === 401) redirect("/anmelden");
    notFound();
  }
  const scans = await apiGet<Pruefungskurz[]>(`/api/v1/projects/${encodeURIComponent(id)}/scans`);
  const liste = scans.ok ? scans.data : [];
  const versionen = await apiGet<Version[]>(`/api/v1/projects/${encodeURIComponent(id)}/versions`);
  const versionListe = versionen.ok ? versionen.data : [];
  return (
    <div className="flex flex-col gap-6">
      <Brotkrumen
        pfad={[{ text: "Übersicht", href: "/" }, { text: "Projekte", href: "/projekte" }, { text: projekt.data.name }]}
      />
      <div>
        <h1 className="font-display text-3xl font-bold">{projekt.data.name}</h1>
        <p className="text-sm text-muted">
          {projekt.data.typ}
          {projekt.data.nach_pruefung_loeschen ? " · Dateien werden nach der Prüfung gelöscht" : " · Dateien verschlüsselt gespeichert"}
        </p>
      </div>
      <Upload projektId={projekt.data.id} quelle={projekt.data.quelle} gitUrl={projekt.data.git_url} />
      {versionListe.length ? (
        <section aria-labelledby="versionen">
          <h2 id="versionen" className="font-display text-xl font-bold">
            Versionen
          </h2>
          <p className="mt-1 text-sm text-muted">
            Die letzten 10 Versionen bleiben verschlüsselt gespeichert. Löschen entfernt die Dateien, der Bericht bleibt.
          </p>
          <ul className="mt-3 flex flex-col gap-2">
            {versionListe.map((v) => (
              <li
                key={v.id}
                className="flex flex-wrap items-center gap-4 rounded-[14px] border border-linie bg-surface px-5 py-3"
              >
                <span className="font-semibold">Version {v.nummer}</span>
                <span className="text-sm text-muted">
                  {datumZeit(v.angelegt)} · {v.dateien} {v.dateien === 1 ? "Datei" : "Dateien"} · {groesse(v.bytes)}
                  {v.commit_sha ? ` · Commit ${v.commit_sha.slice(0, 7)}` : ""}
                  {v.dateien_geloescht ? " · Dateien gelöscht" : ""}
                </span>
                <span className="ml-auto flex items-center gap-3 text-sm">
                  {v.pruefung ? (
                    <Link href={`/pruefungen/${v.pruefung.id}`} className="flex items-center gap-2 hover:text-petrol">
                      {v.pruefung.ampel_gesamt ? (
                        <>
                          <Ampel wert={v.pruefung.ampel_gesamt} />
                          {v.pruefung.note !== null ? <span>Note {v.pruefung.note}</span> : null}
                        </>
                      ) : (
                        <span>Prüfung {STATUS_TEXT[v.pruefung.status]}</span>
                      )}
                    </Link>
                  ) : null}
                  <VersionLoeschen projektId={projekt.data.id} versionId={v.id} nummer={v.nummer} />
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <section>
        <h2 className="font-display text-xl font-bold">Prüfungen</h2>
        {liste.length === 0 ? (
          <p className="mt-2 text-sm text-muted">Noch keine Prüfung.</p>
        ) : (
          <ul className="mt-3 flex flex-col gap-2">
            {liste.map((s) => (
              <li key={s.id}>
                <Link
                  href={`/pruefungen/${s.id}`}
                  className="flex flex-wrap items-center gap-4 rounded-[14px] border border-linie bg-surface px-5 py-3 hover:border-petrol"
                >
                  <span className="text-sm">{datumZeit(s.created_at)}</span>
                  <span className="text-sm text-muted">{UMFANG_TEXT[s.pruefumfang] ?? s.pruefumfang}</span>
                  <span className="ml-auto flex items-center gap-3 text-sm">
                    {s.ampel_gesamt ? <Ampel wert={s.ampel_gesamt} /> : <span>{STATUS_TEXT[s.status]}</span>}
                    {s.note !== null ? <span>Note {s.note}</span> : null}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section aria-labelledby="gefahr" className="flex flex-col gap-3 rounded-[14px] border border-rot bg-surface p-6">
        <h2 id="gefahr" className="font-display text-xl font-bold">
          Projekt löschen
        </h2>
        <p className="text-sm text-muted">
          Löscht das Projekt mit allen Versionen, gespeicherten Dateien, Prüfungen und Berichten sofort und endgültig.
          Geteilte Berichtslinks funktionieren danach nicht mehr.
        </p>
        <ProjektLoeschen id={projekt.data.id} name={projekt.data.name} />
      </section>
    </div>
  );
}
