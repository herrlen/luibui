import { datumZeit, SCHWERE_TEXT, STATUS_TEXT } from "@/lib/format";
import type { BehobenerBefund, ScanStatus } from "@/lib/types";

import { Aktualisieren } from "./Aktualisieren";
import { Teilen } from "./app/Teilen";
import { SCHWERE_STIL } from "./report/BefundKarte";
import { ReportView } from "./report/ReportView";

/** PDFs come straight from the API (same host, the session cookie goes along); the rest is built here. */
const DOWNLOADS = [
  { pfad: "pdf", text: "PDF", titel: "Ergebnis und Liste der Befunde" },
  { pfad: "pdf-detail", text: "PDF mit Details", titel: "Jeder Befund aufgeklappt: Erklärung, Beleg, Fix und Fix-Prompt" },
  { format: "csv", text: "CSV", titel: "Eine Zeile pro Befund, für Excel und LibreOffice" },
  { format: "json", text: "JSON", titel: "Der vollständige Bericht, maschinenlesbar" },
  { format: "sarif", text: "SARIF", titel: "Für GitHub Code Scanning und andere SARIF-Werkzeuge" },
] as const;

/** Where the downloads live: the developer area, or the public quick scan page (PDF and CSV only). */
export type Downloads = "bereich" | "schnellscan";

const IM_SCHNELLSCAN = new Set(["PDF", "PDF mit Details", "CSV"]);

export function downloadUrl(scanId: string, d: (typeof DOWNLOADS)[number], wo: Downloads): string {
  const id = encodeURIComponent(scanId);
  const seite = wo === "bereich" ? "/pruefungen" : "/schnellscan";
  const api = wo === "bereich" ? "/api/v1/scans" : "/api/v1/quickscans";
  if ("format" in d) return `${seite}/${id}/bericht.${d.format}`;
  return `${api}/${id}/bericht.pdf${d.pfad === "pdf-detail" ? "?umfang=detail" : ""}`;
}

/** Findings of the previous check of this project that this check no longer has (S3-7). */
function Behoben({ liste }: { liste: BehobenerBefund[] }) {
  return (
    <section aria-labelledby="behoben" className="rounded-[14px] border border-linie bg-surface p-5">
      <h2 id="behoben" className="font-display text-lg font-bold">
        Seit der letzten Prüfung behoben: {liste.length}
      </h2>
      <ul className="mt-3 flex flex-col gap-2 text-sm">
        {liste.map((x) => (
          <li key={x.fingerprint} className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${SCHWERE_STIL[x.schwere] ?? ""}`}>
              {SCHWERE_TEXT[x.schwere] ?? x.schwere}
            </span>
            <span className="font-medium">{x.titel}</span>
            <span className="break-all font-mono text-xs text-muted">
              {x.datei ? `${x.datei}${x.zeile ? `:${x.zeile}` : ""}` : "ganzes Paket"}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** `downloads`: only where /pruefungen/<id>/bericht.* or /schnellscan/<id>/bericht.csv exists. */
export function Bericht({ scan, downloads }: { scan: ScanStatus; downloads?: Downloads }) {
  const laeuft = scan.status === "wartend" || scan.status === "laeuft";
  const b = scan.bericht;
  return (
    <div className="flex flex-col gap-6">
      <Aktualisieren aktiv={laeuft} />
      {laeuft ? (
        <div className="rounded-[14px] border border-linie bg-surface p-6" aria-live="polite">
          <p className="font-semibold">Prüfung {STATUS_TEXT[scan.status]} …</p>
          <p className="mt-1 text-sm text-muted">
            Das dauert je nach Größe wenige Sekunden bis etwa eine Minute. Die Seite aktualisiert sich selbst.
          </p>
        </div>
      ) : null}
      {scan.status === "fehlgeschlagen" ? (
        <div className="rounded-[14px] border border-rot bg-rot-bg p-6 text-rot" role="alert">
          <p className="font-semibold">Die Prüfung ist fehlgeschlagen.</p>
          <p className="mt-1 text-sm">{scan.fehler ?? "Unbekannter Fehler."}</p>
        </div>
      ) : null}
      {b ? (
        <>
          <ReportView
            bericht={b}
            status={downloads === "bereich" ? scan.befund_status : undefined}
            projektId={downloads === "bereich" ? (scan.project_id ?? undefined) : undefined}
          />
          {downloads === "bereich" && scan.behoben?.length ? <Behoben liste={scan.behoben} /> : null}
          <p className="text-sm text-muted">
            {b.paket.dateien ?? "?"} Dateien · geprüft am {datumZeit(b.geprueft_am)} · Engine {b.engine_version}
          </p>
          {downloads ? (
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-sm text-muted">Herunterladen:</span>
              {DOWNLOADS.filter((d) => downloads === "bereich" || IM_SCHNELLSCAN.has(d.text)).map((d) => (
                <a
                  key={d.text}
                  href={downloadUrl(scan.id, d, downloads)}
                  download
                  title={d.titel}
                  className="inline-flex h-10 items-center rounded-[10px] border border-linie-stark bg-surface px-4 text-[15px] font-medium text-ink hover:border-petrol"
                >
                  {d.text}
                </a>
              ))}
            </div>
          ) : null}
          {downloads === "bereich" ? <Teilen scanId={scan.id} geteilt={scan.geteilt ?? false} /> : null}
        </>
      ) : null}
    </div>
  );
}
