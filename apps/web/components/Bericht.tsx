import { datumZeit, STATUS_TEXT } from "@/lib/format";
import type { ScanStatus } from "@/lib/types";

import { Aktualisieren } from "./Aktualisieren";
import { Teilen } from "./app/Teilen";
import { Veroeffentlichen } from "./app/Veroeffentlichen";
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
          {scan.status === "laeuft" && scan.fortschritt ? <Fortschritt {...scan.fortschritt} /> : null}
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
            befundStatus={downloads === "bereich" ? scan.befund_status : undefined}
            scanId={scan.id}
          />
          <p className="text-sm text-muted">
            {b.paket.dateien ?? "?"} Dateien · geprüft am {datumZeit(b.geprueft_am)} · Engine {b.engine_version}
            {downloads === "bereich" && scan.project_id ? (
              <>
                {" · "}
                <a href={`/pruefungen/${encodeURIComponent(scan.id)}/dateien`} className="text-petrol underline">
                  Dateien ansehen
                </a>
              </>
            ) : null}
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
          {downloads === "bereich" && scan.project_id && scan.pruefumfang === "paket" && scan.ampeln?.gesamt !== "gesperrt" ? (
            <Veroeffentlichen scanId={scan.id} />
          ) : null}
        </>
      ) : null}
    </div>
  );
}

/** Step n of m with the title of the current check. Titles come from the engine, shown as text. */
export function Fortschritt({ schritt, von, titel }: { schritt: number; von: number; titel: string }) {
  const anteil = von > 0 ? Math.min(1, Math.max(0, (schritt - 1) / von)) : 0;
  return (
    <div className="mt-3 flex max-w-md flex-col gap-1.5">
      <p className="text-sm">
        Schritt {schritt} von {von}: {titel}
      </p>
      <div
        role="progressbar"
        aria-label="Fortschritt der Prüfung"
        aria-valuemin={0}
        aria-valuemax={von}
        aria-valuenow={schritt - 1}
        aria-valuetext={`Schritt ${schritt} von ${von}`}
        className="h-2 overflow-hidden rounded-full bg-flaeche-2"
      >
        <div className="h-full bg-petrol transition-[width]" style={{ width: `${anteil * 100}%` }} />
      </div>
    </div>
  );
}
