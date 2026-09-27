// CSV export of a report (S2-12, CLAUDE.md rule 12): one row per finding, UTF-8 with BOM,
// semicolon, every cell quoted. Cells that a spreadsheet would read as a formula get an apostrophe.
import type { Bericht } from "./types";

const FORMEL = /^[=+\-@\t\r]/;

export function zelle(wert: string | number | null | undefined): string {
  let text = wert === null || wert === undefined ? "" : String(wert);
  if (FORMEL.test(text)) text = `'${text}`;
  return `"${text.replaceAll('"', '""')}"`;
}

const SPALTEN = [
  "scan_art",
  "paket",
  "version",
  "geprueft_am",
  "ampel_gesamt",
  "note",
  "freigabe",
  "schwere",
  "achse",
  "rule_id",
  "titel",
  "datei",
  "zeile",
  "erklaerung",
  "beleg",
  "fix",
  "fix_prompt",
] as const;

export function berichtAlsCsv(b: Bericht, { showDsgvo = true }: { showDsgvo?: boolean } = {}): string {
  const befunde = showDsgvo ? b.befunde : b.befunde.filter((x) => x.achse !== "dsgvo");
  const gesamt = showDsgvo ? b.ampeln.gesamt : b.ampeln.sicherheit;
  const scanArt = b.scan_art === "schnell" ? "schnell (ohne Gewähr)" : b.scan_art;
  const zeilen = befunde.map((x) =>
    [
      scanArt,
      b.paket.name,
      b.paket.version ?? "",
      b.geprueft_am,
      gesamt,
      b.note,
      b.freigabe,
      x.schwere,
      x.achse,
      x.rule_id,
      x.titel,
      x.datei,
      x.zeile,
      x.erklaerung,
      x.beleg,
      x.fix,
      x.fix_prompt,
    ]
      .map(zelle)
      .join(";"),
  );
  return "﻿" + [SPALTEN.map(zelle).join(";"), ...zeilen].join("\r\n") + "\r\n";
}
