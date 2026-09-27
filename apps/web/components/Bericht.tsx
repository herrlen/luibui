import { datumZeit, FREIGABE_TEXT, SCHWERE_TEXT, STATUS_TEXT, UMFANG_TEXT } from "@/lib/format";
import type { ScanStatus } from "@/lib/types";

import { Aktualisieren } from "./Aktualisieren";
import { Ampel } from "./Ampel";
import { Befund } from "./Befund";

const REIHENFOLGE = ["K", "H", "M", "N", "I"] as const;

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
          {b.scan_art === "schnell" ? (
            <p className="rounded-lg border border-gelb bg-gelb-bg p-3 text-sm text-gelb">
              Schnellscan mit eingeschränktem Umfang, <strong>ohne Gewähr</strong>.
            </p>
          ) : null}
          <section className="grid gap-4 rounded-[14px] border border-linie bg-surface p-6 sm:grid-cols-4" aria-label="Ergebnis">
            <div>
              <p className="text-xs text-muted">Gesamt</p>
              <div className="mt-1">
                <Ampel wert={b.ampeln.gesamt} gross />
              </div>
              <p className="mt-2 text-sm">
                {b.ampeln.gesamt === "gruen"
                  ? `Keine bekannten Befunde, geprüft am ${datumZeit(b.geprueft_am)}`
                  : FREIGABE_TEXT[b.freigabe]}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted">Sicherheit</p>
              <div className="mt-1">
                <Ampel wert={b.ampeln.sicherheit} />
              </div>
            </div>
            <div>
              <p className="text-xs text-muted">DSGVO</p>
              <div className="mt-1">
                <Ampel wert={b.ampeln.dsgvo} />
              </div>
            </div>
            <div>
              <p className="text-xs text-muted">Note</p>
              <p className="mt-1 font-display text-3xl font-bold">
                {b.note}
                <span className="text-base font-normal text-muted"> von 100</span>
              </p>
            </div>
          </section>
          <p className="text-sm text-muted">
            {b.paket.name} · {UMFANG_TEXT[b.pruefumfang]} · {b.paket.dateien ?? "?"} Dateien · geprüft am{" "}
            {datumZeit(b.geprueft_am)} · Engine {b.engine_version}
          </p>
          {b.hinweise.length ? (
            <ul className="flex flex-col gap-1 text-sm">
              {b.hinweise.map((h) => (
                <li key={h} className="rounded-lg bg-surface px-3 py-2">
                  {h}
                </li>
              ))}
            </ul>
          ) : null}
          {REIHENFOLGE.map((s) => {
            const liste = b.befunde.filter((x) => x.schwere === s);
            if (!liste.length) return null;
            return (
              <section key={s} className="flex flex-col gap-3">
                <h2 className="font-display text-xl font-bold">
                  {SCHWERE_TEXT[s]} ({liste.length})
                </h2>
                {liste.map((x, i) => (
                  <Befund key={`${x.rule_id}-${x.datei}-${i}`} b={x} />
                ))}
              </section>
            );
          })}
          {!b.befunde.length ? (
            <p className="rounded-[14px] border border-linie bg-surface p-6">Keine Befunde.</p>
          ) : null}
          {b.nicht_geprueft.length ? (
            <section>
              <h2 className="font-display text-xl font-bold">Nicht geprüft</h2>
              <ul className="mt-2 flex flex-col gap-1 text-sm">
                {b.nicht_geprueft.map((n) => (
                  <li key={n.pruefung}>
                    {n.pruefung}: <span className="text-muted">{n.grund}</span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
