import "server-only";

import { dateiname, type Format, inhalt, TYP } from "./export";
import { type Antwort, apiGet } from "./server-api";
import type { ScanStatus } from "./types";

/**
 * Download of one report. The API checks the owner via the session cookie; a foreign, unknown or
 * unfinished scan gives the same 404 as the report page.
 */
export async function berichtDownload(id: string, format: Format): Promise<Response> {
  return antwort(await apiGet<ScanStatus>(`/api/v1/scans/${encodeURIComponent(id)}`), format);
}

/** Download of a quick scan report: public, the random scan ID is the key; no cookie goes along. */
export async function schnellscanDownload(id: string, format: Format): Promise<Response> {
  return antwort(await apiGet<ScanStatus>(`/api/v1/quickscans/${encodeURIComponent(id)}`, false), format);
}

function antwort(scan: Antwort<ScanStatus>, format: Format): Response {
  if (!scan.ok || !scan.data.bericht) {
    const status = !scan.ok && (scan.status === 401 || scan.status === 503) ? scan.status : 404;
    const text =
      status === 401 ? "Nicht angemeldet" : status === 503 ? "Der Dienst antwortet gerade nicht." : "Nicht gefunden";
    return new Response(text, {
      status,
      headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" },
    });
  }
  const b = scan.data.bericht;
  return new Response(inhalt(b, format), {
    headers: {
      "Content-Type": TYP[format],
      "Content-Disposition": `attachment; filename="${dateiname(b, format)}"`,
      "X-Content-Type-Options": "nosniff",
      "Cache-Control": "private, no-store",
    },
  });
}
