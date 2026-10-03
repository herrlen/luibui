import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { Ampel } from "@/components/Ampel";
import { Brotkrumen } from "@/components/app/Brotkrumen";
import { Verlauf } from "@/components/app/Verlauf";
import { datumZeit, groesse, STATUS_TEXT, UMFANG_TEXT } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { Projekt, Pruefungskurz, VerlaufPunkt, Version } from "@/lib/types";

import { CiAnbindung } from "./CiAnbindung";
import { ProjektLoeschen } from "./ProjektLoeschen";
import { Upload } from "./Upload";
import { VersionLoeschen } from "./VersionLoeschen";
import { Webhook, type WebhookInfo } from "./Webhook";

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
  const verlauf = await apiGet<VerlaufPunkt[]>(`/api/v1/projects/${encodeURIComponent(id)}/verlauf`);
  const punkte = verlauf.ok ? verlauf.data : [];
  const webhook =
    projekt.data.quelle === "git"
      ? await apiGet<WebhookInfo>(`/api/v1/projects/${encodeURIComponent(id)}/webhook`)
      : null;
  // A check can be compared with the finished one before it (list is newest first).
  const fertig = liste.filter((s) => s.status === "fertig");
  const vorgaenger = new Map(fertig.slice(0, -1).map((s, i) => [s.id, fertig[i + 1].id]));
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
      {webhook?.ok ? <Webhook projektId={projekt.data.id} info={webhook.data} /> : null}
      <CiAnbindung projektId={projekt.data.id} projektName={projekt.data.name} />
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
      {punkte.length ? (
        <section aria-labelledby="verlauf" className="flex flex-col gap-3 rounded-[14px] border border-linie bg-surface p-5">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 id="verlauf" className="font-display text-xl font-bold">
              Verlauf
            </h2>
            {fertig.length > 1 ? (
              <Link href={`/projekte/${projekt.data.id}/vergleich`} className="text-sm font-medium text-petrol hover:underline">
                Letzte Prüfung mit der vorigen vergleichen
              </Link>
            ) : null}
          </div>
          {punkte.length > 1 ? (
            <Verlauf punkte={punkte} />
          ) : (
            <p className="text-sm text-muted">
              Eine fertige Prüfung (Note {punkte[0].note ?? "–"}). Der Verlauf erscheint ab der zweiten.
            </p>
          )}
        </section>
      ) : null}
      <section>
        <h2 className="font-display text-xl font-bold">Prüfungen</h2>
        {liste.length === 0 ? (
          <p className="mt-2 text-sm text-muted">Noch keine Prüfung.</p>
        ) : (
          <ul className="mt-3 flex flex-col gap-2">
            {liste.map((s) => (
              <li key={s.id} className="flex items-stretch gap-2">
                <Link
                  href={`/pruefungen/${s.id}`}
                  className="flex min-w-0 flex-1 flex-wrap items-center gap-4 rounded-[14px] border border-linie bg-surface px-5 py-3 hover:border-petrol"
                >
                  <span className="text-sm">{datumZeit(s.created_at)}</span>
                  <span className="text-sm text-muted">{UMFANG_TEXT[s.pruefumfang] ?? s.pruefumfang}</span>
                  <span className="ml-auto flex items-center gap-3 text-sm">
                    {s.ampel_gesamt ? <Ampel wert={s.ampel_gesamt} /> : <span>{STATUS_TEXT[s.status]}</span>}
                    {s.note !== null ? <span>Note {s.note}</span> : null}
                  </span>
                </Link>
                {vorgaenger.has(s.id) ? (
                  <Link
                    href={`/projekte/${projekt.data.id}/vergleich?von=${vorgaenger.get(s.id)}&bis=${s.id}`}
                    className="flex items-center rounded-[14px] border border-linie bg-surface px-4 text-sm hover:border-petrol"
                    title="Mit der Prüfung davor vergleichen"
                  >
                    Vergleichen
                  </Link>
                ) : null}
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
