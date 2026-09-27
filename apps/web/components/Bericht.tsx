import { datumZeit, STATUS_TEXT } from "@/lib/format";
import type { ScanStatus } from "@/lib/types";

import { Aktualisieren } from "./Aktualisieren";
import { ReportView } from "./report/ReportView";

export function Bericht({ scan }: { scan: ScanStatus }) {
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
        </>
      ) : null}
    </div>
  );
}
