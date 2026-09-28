import { datumZeit, STATUS_TEXT } from "@/lib/format";
import type { ScanStatus } from "@/lib/types";

import { Aktualisieren } from "./Aktualisieren";
import { ReportView } from "./report/ReportView";

const DOWNLOADS = [
  { format: "csv", text: "CSV", titel: "Eine Zeile pro Befund, für Excel und LibreOffice" },
  { format: "json", text: "JSON", titel: "Der vollständige Bericht, maschinenlesbar" },
  { format: "sarif", text: "SARIF", titel: "Für GitHub Code Scanning und andere SARIF-Werkzeuge" },
] as const;

/** `downloads`: only in the developer area, where /pruefungen/<id>/bericht.* exists. */
export function Bericht({ scan, downloads = false }: { scan: ScanStatus; downloads?: boolean }) {
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
          <ReportView bericht={b} />
          <p className="text-sm text-muted">
            {b.paket.dateien ?? "?"} Dateien · geprüft am {datumZeit(b.geprueft_am)} · Engine {b.engine_version}
          </p>
          {downloads ? (
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-sm text-muted">Herunterladen:</span>
              {DOWNLOADS.map((d) => (
                <a
                  key={d.format}
                  href={`/pruefungen/${encodeURIComponent(scan.id)}/bericht.${d.format}`}
                  download
                  title={d.titel}
                  className="inline-flex h-10 items-center rounded-[10px] border border-linie-stark bg-surface px-4 text-[15px] font-medium text-ink hover:border-petrol"
                >
                  {d.text}
                </a>
              ))}
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
