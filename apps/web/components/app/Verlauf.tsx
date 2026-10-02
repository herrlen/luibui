"use client";

import Link from "next/link";
import { useState } from "react";

import { AMPEL_TEXT, datum, datumZeit } from "@/lib/format";
import type { VerlaufPunkt } from "@/lib/types";

// History of a project (S3-5): grade over time (line) and findings per check (stacked bars), one
// shared X (the checks in order) and one hover readout for both. Severity uses one red ramp, dark
// = critical (ordinal, validated with the dataviz checker); N and I share the lightest step.
// Every value is also in the table below. Only numbers, dates and fixed labels, no package text.
const STUFEN = [
  { key: "K", text: "Kritisch", farbe: "#5c1a13" },
  { key: "H", text: "Hoch", farbe: "#a3261b" },
  { key: "M", text: "Mittel", farbe: "#d4604d" },
  { key: "NI", text: "Niedrig/Info", farbe: "#e0958a" },
] as const;

const B = 640; // viewBox width
const LINKS = 36;
const RECHTS = 12;
const NOTE_H = 150;
const BALKEN_H = 120;
const OBEN = 10;
const UNTEN = 22;

function anzahl(p: VerlaufPunkt, key: (typeof STUFEN)[number]["key"]): number {
  return key === "NI" ? p.befunde.N + p.befunde.I : p.befunde[key];
}

function summe(p: VerlaufPunkt): number {
  return p.befunde.K + p.befunde.H + p.befunde.M + p.befunde.N + p.befunde.I;
}

export function Verlauf({ punkte }: { punkte: VerlaufPunkt[] }) {
  const [aktiv, setAktiv] = useState<number | null>(null);
  const n = punkte.length;
  const breite = B - LINKS - RECHTS;
  const schritt = n > 1 ? breite / (n - 1) : 0;
  const x = (i: number) => (n > 1 ? LINKS + i * schritt : LINKS + breite / 2);
  const yNote = (note: number) => OBEN + (1 - note / 100) * (NOTE_H - OBEN - UNTEN);
  const maxBefunde = Math.max(1, ...punkte.map(summe));
  const balkenBreite = Math.max(4, Math.min(28, (n > 1 ? schritt : breite) * 0.6));
  const yBalken = (wert: number) => (wert / maxBefunde) * (BALKEN_H - OBEN - UNTEN);
  const linie = punkte
    .map((p, i) => (p.note === null ? null : `${x(i).toFixed(1)},${yNote(p.note).toFixed(1)}`))
    .filter(Boolean)
    .join(" ");
  const p = aktiv === null ? null : punkte[aktiv];
  const trefferBreite = n > 1 ? schritt : breite;

  // One transparent column per check, wider than the marks: hover and keyboard focus.
  const treffer = (hoehe: number) =>
    punkte.map((pt, i) => (
      <rect
        key={pt.scan_id}
        x={x(i) - trefferBreite / 2}
        y={0}
        width={trefferBreite}
        height={hoehe}
        fill="transparent"
        tabIndex={0}
        role="button"
        aria-label={`Prüfung vom ${datumZeit(pt.created_at)}: Note ${pt.note ?? "–"}, ${summe(pt)} Befunde`}
        onPointerEnter={() => setAktiv(i)}
        onFocus={() => setAktiv(i)}
        onBlur={() => setAktiv(null)}
      />
    ));

  return (
    <div className="flex flex-col gap-4">
      <div className="relative" onPointerLeave={() => setAktiv(null)}>
        <figure className="m-0">
          <figcaption className="text-sm font-semibold">Note (0–100)</figcaption>
          <svg viewBox={`0 0 ${B} ${NOTE_H}`} className="mt-1 w-full" role="img" aria-label="Note je Prüfung">
            {[0, 50, 100].map((t) => (
              <g key={t}>
                <line x1={LINKS} x2={B - RECHTS} y1={yNote(t)} y2={yNote(t)} stroke="#e2ded3" strokeWidth={1} />
                <text x={LINKS - 6} y={yNote(t) + 4} textAnchor="end" fontSize={11} fill="#5a5f6a">
                  {t}
                </text>
              </g>
            ))}
            {aktiv !== null ? (
              <line x1={x(aktiv)} x2={x(aktiv)} y1={OBEN} y2={NOTE_H - UNTEN} stroke="#cfcabc" strokeWidth={1} />
            ) : null}
            {n > 1 ? <polyline points={linie} fill="none" stroke="#0e5e5b" strokeWidth={2} strokeLinejoin="round" /> : null}
            {punkte.map((pt, i) =>
              pt.note === null ? null : (
                <circle
                  key={pt.scan_id}
                  cx={x(i)}
                  cy={yNote(pt.note)}
                  r={aktiv === i ? 5.5 : 4}
                  fill="#0e5e5b"
                  stroke="#ffffff"
                  strokeWidth={2}
                />
              ),
            )}
            <text x={LINKS} y={NOTE_H - 6} fontSize={11} fill="#5a5f6a">
              {datum(punkte[0].created_at)}
            </text>
            {n > 1 ? (
              <text x={B - RECHTS} y={NOTE_H - 6} textAnchor="end" fontSize={11} fill="#5a5f6a">
                {datum(punkte[n - 1].created_at)}
              </text>
            ) : null}
            {treffer(NOTE_H)}
          </svg>
        </figure>
        <figure className="m-0 mt-2">
          <figcaption className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
            <span className="font-semibold">Befunde je Prüfung</span>
            {STUFEN.map((s) => (
              <span key={s.key} className="inline-flex items-center gap-1.5 text-xs text-ink-2">
                <svg width="10" height="10" aria-hidden="true">
                  <rect width="10" height="10" rx="2" fill={s.farbe} />
                </svg>
                {s.text}
              </span>
            ))}
          </figcaption>
          <svg viewBox={`0 0 ${B} ${BALKEN_H}`} className="mt-1 w-full" role="img" aria-label="Befunde je Prüfung nach Schwere">
            <line
              x1={LINKS}
              x2={B - RECHTS}
              y1={BALKEN_H - UNTEN}
              y2={BALKEN_H - UNTEN}
              stroke="#cfcabc"
              strokeWidth={1}
            />
            <text x={LINKS - 6} y={OBEN + 4} textAnchor="end" fontSize={11} fill="#5a5f6a">
              {maxBefunde}
            </text>
            <text x={LINKS - 6} y={BALKEN_H - UNTEN + 4} textAnchor="end" fontSize={11} fill="#5a5f6a">
              0
            </text>
            {punkte.map((pt, i) => {
              let unten = BALKEN_H - UNTEN;
              return (
                <g key={pt.scan_id} opacity={aktiv === null || aktiv === i ? 1 : 0.55}>
                  {STUFEN.map((s) => {
                    const h = yBalken(anzahl(pt, s.key));
                    if (h <= 0) return null;
                    unten -= h;
                    // 2px surface gap between stacked segments
                    return (
                      <rect
                        key={s.key}
                        x={x(i) - balkenBreite / 2}
                        y={unten}
                        width={balkenBreite}
                        height={Math.max(1, h - 2)}
                        rx={2}
                        fill={s.farbe}
                      />
                    );
                  })}
                </g>
              );
            })}
            {treffer(BALKEN_H)}
          </svg>
        </figure>
        {p ? (
          <div
            role="status"
            className="pointer-events-none absolute top-6 z-10 w-56 rounded-lg border border-linie bg-surface p-3 text-sm shadow-md"
            style={{ left: `clamp(0px, calc(${(x(aktiv!) / B) * 100}% - 7rem), calc(100% - 14rem))` }}
          >
            <p className="text-xs text-muted">{datumZeit(p.created_at)}</p>
            <p className="mt-1">
              <span className="font-display text-xl font-bold">{p.note ?? "–"}</span>{" "}
              <span className="text-muted">Note · {p.ampel_gesamt ? AMPEL_TEXT[p.ampel_gesamt] : "–"}</span>
            </p>
            <ul className="mt-2 flex flex-col gap-0.5">
              {STUFEN.map((s) => (
                <li key={s.key} className="flex items-center gap-2">
                  <svg width="12" height="4" aria-hidden="true">
                    <rect width="12" height="4" rx="2" fill={s.farbe} />
                  </svg>
                  <span className="font-semibold">{anzahl(p, s.key)}</span>
                  <span className="text-muted">{s.text}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
      <details className="text-sm">
        <summary className="cursor-pointer text-muted hover:text-ink">Als Tabelle</summary>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-left">
            <thead className="text-xs text-muted">
              <tr>
                <th className="py-1 pr-4 font-medium">Prüfung</th>
                <th className="py-1 pr-4 font-medium">Note</th>
                <th className="py-1 pr-4 font-medium">Ampel</th>
                {STUFEN.map((s) => (
                  <th key={s.key} className="py-1 pr-4 font-medium">
                    {s.text}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...punkte].reverse().map((pt) => (
                <tr key={pt.scan_id} className="border-t border-linie">
                  <td className="py-1 pr-4">
                    <Link href={`/pruefungen/${pt.scan_id}`} className="hover:text-petrol">
                      {datumZeit(pt.created_at)}
                    </Link>
                  </td>
                  <td className="py-1 pr-4">{pt.note ?? "–"}</td>
                  <td className="py-1 pr-4">{pt.ampel_gesamt ? AMPEL_TEXT[pt.ampel_gesamt] : "–"}</td>
                  {STUFEN.map((s) => (
                    <td key={s.key} className="py-1 pr-4">
                      {anzahl(pt, s.key)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
