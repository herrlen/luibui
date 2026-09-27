"use client";

import { useId, useRef, useState } from "react";

import { groesse } from "@/lib/format";

export type Eintrag = { datei: File; pfad: string };
export type Modus = "dateien" | "ordner" | "zip";

const ARCHIV = /\.(zip|tar|tgz|tar\.gz|tar\.bz2|tar\.xz)$/i;
const MAX_DATEIEN = 1000;
const MAX_BYTES = 50 * 1024 * 1024;

export function istArchiv(name: string): boolean {
  return ARCHIV.test(name);
}

// Dropped folders arrive as FileSystemEntry trees; readEntries returns at most ~100 per call.
async function sammeln(entry: FileSystemEntry, pfad: string, out: Eintrag[]): Promise<void> {
  if (out.length > MAX_DATEIEN) return;
  if (entry.isFile) {
    const datei = await new Promise<File>((ok, fehler) => (entry as FileSystemFileEntry).file(ok, fehler));
    out.push({ datei, pfad: pfad + entry.name });
    return;
  }
  const leser = (entry as FileSystemDirectoryEntry).createReader();
  for (;;) {
    const teil = await new Promise<FileSystemEntry[]>((ok, fehler) => leser.readEntries(ok, fehler));
    if (!teil.length) break;
    for (const kind of teil) await sammeln(kind, `${pfad}${entry.name}/`, out);
  }
}

async function ausDrop(daten: DataTransfer): Promise<Eintrag[]> {
  const eintraege = Array.from(daten.items)
    .map((i) => (i.kind === "file" ? i.webkitGetAsEntry() : null))
    .filter((e): e is FileSystemEntry => e !== null);
  if (!eintraege.length) return Array.from(daten.files).map((d) => ({ datei: d, pfad: d.name }));
  const out: Eintrag[] = [];
  for (const e of eintraege) await sammeln(e, "", out);
  return out;
}

export function Ablage({
  modus,
  auswahl,
  setAuswahl,
}: {
  modus: Modus;
  auswahl: Eintrag[];
  setAuswahl: (e: Eintrag[]) => void;
}) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const [ueber, setUeber] = useState(false);
  const bytes = auswahl.reduce((s, e) => s + e.datei.size, 0);
  const zuViel = auswahl.length > MAX_DATEIEN || bytes > MAX_BYTES;
  const was = modus === "ordner" ? "einen Ordner" : modus === "zip" ? "ein Archiv" : "Dateien oder einen Ordner";

  return (
    <div className="flex flex-col gap-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setUeber(true);
        }}
        onDragLeave={() => setUeber(false)}
        onDrop={async (e) => {
          e.preventDefault();
          setUeber(false);
          setAuswahl(await ausDrop(e.dataTransfer));
        }}
        className={`flex flex-col items-center justify-center gap-3 rounded-[14px] border-2 border-dashed px-6 py-10 text-center transition-colors ${
          ueber ? "border-petrol bg-petrol-hell" : "border-linie-stark bg-flaeche-2"
        }`}
      >
        <svg aria-hidden="true" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#0E5E5B" strokeWidth="2">
          <path d="M12 16V4m0 0-4 4m4-4 4 4M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
        </svg>
        <p className="text-[15px] font-medium text-ink">Hierher ziehen: {was}</p>
        <p className="text-sm text-muted">oder</p>
        <label
          htmlFor={id}
          className="inline-flex h-11 cursor-pointer items-center rounded-[10px] border border-linie-stark bg-surface px-[18px] text-[15px] font-semibold text-ink hover:border-petrol focus-within:ring-2 focus-within:ring-petrol"
        >
          {modus === "ordner" ? "Ordner auswählen" : modus === "zip" ? "Archiv auswählen" : "Dateien auswählen"}
        </label>
        <input
          ref={input}
          id={id}
          key={modus}
          type="file"
          className="sr-only"
          multiple={modus !== "zip"}
          accept={modus === "zip" ? ".zip,.tar,.tgz,.gz,.bz2,.xz" : undefined}
          {...(modus === "ordner" ? { webkitdirectory: "", directory: "" } : {})}
          onChange={(e) =>
            setAuswahl(
              Array.from(e.currentTarget.files ?? []).map((d) => ({ datei: d, pfad: d.webkitRelativePath || d.name })),
            )
          }
        />
      </div>
      {auswahl.length ? (
        <div className="flex flex-col gap-2 rounded-[12px] border border-linie bg-surface p-4 text-sm" aria-live="polite">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="font-semibold">
              {auswahl.length === 1 ? "1 Datei" : `${auswahl.length} Dateien`} · {groesse(bytes)}
            </p>
            <button
              type="button"
              onClick={() => {
                setAuswahl([]);
                if (input.current) input.current.value = "";
              }}
              className="text-sm text-petrol underline"
            >
              Auswahl leeren
            </button>
          </div>
          <ul className="max-h-40 overflow-y-auto font-mono text-xs text-muted">
            {auswahl.slice(0, 50).map((e) => (
              <li key={e.pfad} className="truncate">
                {e.pfad}
              </li>
            ))}
            {auswahl.length > 50 ? <li>… und {auswahl.length - 50} weitere</li> : null}
          </ul>
          {zuViel ? (
            <p className="text-rot">
              Zu groß: höchstens 1.000 Dateien und 50 MB. Lege den Ordner als ZIP-Archiv an oder wähle weniger aus.
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
