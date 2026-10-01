import { datum, datumZeit, FREIGABE_TEXT, SCHWERE_TEXT, UMFANG_TEXT } from "@/lib/format";
import type { Bericht, BefundStatus } from "@/lib/types";

import { Ampel } from "../Ampel";
import { Abdeckung } from "./Abdeckung";
import { BefundKarte } from "./BefundKarte";

const REIHENFOLGE = ["K", "H", "M", "N", "I"] as const;
const SCAN_ART: Record<string, string> = {
  schnell: "Schnellscan",
  intensiv: "Intensivscan",
  lokal: "Lokale Prüfung",
};

/**
 * One report, as the developer area and the landing page show it. ``showDsgvo={false}`` hides the
 * DSGVO light and every DSGVO finding; the overall light then follows the security axis only.
 */
export function ReportView({
  bericht: b,
  showDsgvo = true,
  befundStatus,
  scanId,
}: {
  bericht: Bericht;
  showDsgvo?: boolean;
  /** S3-7: with ``scanId`` the owner can change it; lights and grade stay as the check found them. */
  befundStatus?: Record<string, BefundStatus> | null;
  scanId?: string;
}) {
  const befunde = showDsgvo ? b.befunde : b.befunde.filter((x) => x.achse !== "dsgvo");
  const gesamt = showDsgvo ? b.ampeln.gesamt : b.ampeln.sicherheit;
  const sortiert = REIHENFOLGE.flatMap((s) => befunde.filter((x) => x.schwere === s));
  const erledigt = sortiert.filter(
    (x) => x.fingerprint && (befundStatus?.[x.fingerprint]?.status ?? "offen") !== "offen",
  ).length;
  const ohneDsgvo = (liste: string[]) => (showDsgvo ? liste : liste.filter((t) => !t.startsWith("DSGVO")));
  const abdeckung = b.abdeckung?.map((a) => ({ ...a, geprueft: ohneDsgvo(a.geprueft), offen: ohneDsgvo(a.offen) }));
  return (
    <div className="flex flex-col gap-6">
      {b.scan_art === "schnell" ? (
        <p className="rounded-lg border border-gelb bg-gelb-bg p-3 text-sm text-gelb">
          Schnellscan mit eingeschränktem Umfang, <strong>ohne Gewähr</strong>.
        </p>
      ) : null}
      <section
        className="flex flex-col gap-6 rounded-[18px] border border-linie bg-surface p-6 sm:p-8 lg:flex-row lg:items-center lg:justify-between"
        aria-label="Ergebnis"
      >
        <div className="min-w-0">
          <p className="break-words font-mono text-sm text-muted">
            {b.paket.name}
            {b.paket.version ? ` · v${b.paket.version}` : ""}
          </p>
          <p className="mt-1 text-sm text-muted">
            {SCAN_ART[b.scan_art] ?? b.scan_art} · {UMFANG_TEXT[b.pruefumfang]} · geprüft am {datum(b.geprueft_am)}
          </p>
          <div className="mt-4">
            <Ampel wert={gesamt} gross />
          </div>
          <p className="mt-2 text-sm">
            {gesamt === "gruen"
              ? `Keine bekannten Befunde, geprüft am ${datumZeit(b.geprueft_am)}`
              : `Freigabe: ${FREIGABE_TEXT[b.freigabe]}`}
          </p>
        </div>
        <dl className="grid grid-cols-2 gap-x-8 gap-y-4 sm:flex sm:flex-wrap">
          <div>
            <dt className="text-xs text-muted">Sicherheit</dt>
            <dd className="mt-1">
              <Ampel wert={b.ampeln.sicherheit} />
            </dd>
          </div>
          {showDsgvo ? (
            <div>
              <dt className="text-xs text-muted">DSGVO</dt>
              <dd className="mt-1">
                <Ampel wert={b.ampeln.dsgvo} />
              </dd>
            </div>
          ) : null}
          <div>
            <dt className="text-xs text-muted">Note</dt>
            <dd className="mt-1 font-display text-3xl font-bold leading-none">
              {b.note}
              <span className="text-base font-normal text-muted">/100</span>
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Freigabe</dt>
            <dd className="mt-1 text-base font-semibold">{FREIGABE_TEXT[b.freigabe]}</dd>
          </div>
        </dl>
      </section>
      {b.hinweise.length ? (
        <ul className="flex flex-col gap-1 text-sm">
          {b.hinweise.map((h) => (
            <li key={h} className="rounded-lg bg-surface px-3 py-2">
              {h}
            </li>
          ))}
        </ul>
      ) : null}
      {sortiert.length ? (
        <section aria-label="Befunde" className="flex flex-col gap-3">
          <p className="text-sm text-muted">
            {sortiert.length} Befunde:{" "}
            {REIHENFOLGE.map((s) => [s, sortiert.filter((x) => x.schwere === s).length] as const)
              .filter(([, n]) => n > 0)
              .map(([s, n]) => `${n} ${SCHWERE_TEXT[s]}`)
              .join(", ")}
            {erledigt ? ` · ${erledigt} davon akzeptiert, bestritten oder behoben` : ""}
          </p>
          {sortiert.map((x, i) => (
            <BefundKarte
              key={`${x.rule_id}-${x.datei}-${i}`}
              b={x}
              offen={i === 0}
              status={x.fingerprint ? befundStatus?.[x.fingerprint] : undefined}
              scanId={befundStatus ? scanId : undefined}
            />
          ))}
        </section>
      ) : (
        <p className="rounded-[14px] border border-linie bg-surface p-6">Keine Befunde.</p>
      )}
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
      {abdeckung ? <Abdeckung abdeckung={abdeckung} /> : null}
    </div>
  );
}
