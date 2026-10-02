// CSV export of a report (S2-12, CLAUDE.md rule 12): one row per finding, UTF-8 with BOM,
// semicolon, every cell quoted. Cells that a spreadsheet would read as a formula get an apostrophe.
// Without findings there is one row with the result and empty finding columns, so the result and
// "ohne Gewähr" in scan_art are still in the file.
import { statusLabel } from "./format";
import type { BefundStatus, Bericht } from "./types";

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
  "status",
  "status_begruendung",
] as const;

/** ``status``: the owner's finding status (S3-7), only for downloads from the developer area. */
export function berichtAlsCsv(
  b: Bericht,
  { showDsgvo = true, status }: { showDsgvo?: boolean; status?: Record<string, BefundStatus> | null } = {},
): string {
  const befunde = showDsgvo ? b.befunde : b.befunde.filter((x) => x.achse !== "dsgvo");
  const gesamt = showDsgvo ? b.ampeln.gesamt : b.ampeln.sicherheit;
  const scanArt = b.scan_art === "schnell" ? "schnell (ohne Gewähr)" : b.scan_art;
  const kopf = [scanArt, b.paket.name, b.paket.version ?? "", b.geprueft_am, gesamt, b.note, b.freigabe];
  const zeilen = (befunde.length ? befunde : [null]).map((x) =>
    [
      ...kopf,
      x?.schwere,
      x?.achse,
      x?.rule_id,
      x?.titel,
      x?.datei,
      x?.zeile,
      x?.erklaerung,
      x?.beleg,
      x?.fix,
      x?.fix_prompt,
      ...statusZellen(x?.fingerprint ? status?.[x.fingerprint] : undefined),
    ]
      .map(zelle)
      .join(";"),
  );
  return "﻿" + [SPALTEN.map(zelle).join(";"), ...zeilen].join("\r\n") + "\r\n";
}

function statusZellen(st: BefundStatus | undefined): [string, string] {
  const label = statusLabel(st);
  return label ? [label, st?.begruendung ?? ""] : ["", ""];
}
