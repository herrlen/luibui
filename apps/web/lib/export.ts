// Report downloads (S2-12): file name and body per format. Pure, so it runs in tests.
import { berichtAlsCsv } from "./csv";
import { berichtAlsSarif, hinweise } from "./sarif";
import type { BefundStatus, Bericht } from "./types";

export type Format = "csv" | "json" | "sarif";

export const TYP: Record<Format, string> = {
  csv: "text/csv; charset=utf-8",
  json: "application/json; charset=utf-8",
  sarif: "application/sarif+json; charset=utf-8",
};

/** File name from the package name and date, reduced to characters safe in a header. */
export function dateiname(b: Bericht, format: Format): string {
  const paket =
    b.paket.name
      .replace(/[^A-Za-z0-9._-]+/g, "-")
      .replace(/^[-.]+|[-.]+$/g, "")
      .slice(0, 60) || "paket";
  const datum = /^\d{4}-\d{2}-\d{2}/.test(b.geprueft_am) ? b.geprueft_am.slice(0, 10) : "bericht";
  return `luibui-${paket}-${datum}.${format}`;
}

/** ``status``: finding status by fingerprint (S3-7); only the developer area passes it. */
export function inhalt(b: Bericht, format: Format, status?: Record<string, BefundStatus> | null): string {
  if (format === "csv") return berichtAlsCsv(b, { status });
  if (format === "sarif") return JSON.stringify(berichtAlsSarif(b, status), null, 2);
  return JSON.stringify({ ...b, hinweise: hinweise(b), ...(status ? { befund_status: status } : {}) }, null, 2);
}
