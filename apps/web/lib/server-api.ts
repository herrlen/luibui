import "server-only";

import { cookies } from "next/headers";

import type { Fehler } from "./types";

// Server components talk to the API directly inside the network and forward the browser's cookie.
const API = process.env.API_INTERNAL_URL ?? "http://api:8000";

export type Antwort<T> = { ok: true; data: T } | { ok: false; status: number; fehler: Fehler };

export async function apiGet<T>(path: string, mitCookie = true): Promise<Antwort<T>> {
  const headers: Record<string, string> = { accept: "application/json" };
  if (mitCookie) {
    const cookie = (await cookies()).toString();
    if (cookie) headers.cookie = cookie;
  }
  let res: Response | null = null;
  // Only reads, so retrying is safe: right after an API restart the cluster DNS still returns the
  // old address for about 30 seconds (see lib/api-verbindung.ts); fetch gives up after 10 s.
  const ende = Date.now() + 30_000;
  while (res === null) {
    try {
      res = await fetch(`${API}${path}`, { headers, cache: "no-store" });
    } catch {
      if (Date.now() >= ende) {
        return { ok: false, status: 503, fehler: { code: "api_nicht_erreichbar", text: "Der Dienst antwortet gerade nicht." } };
      }
      await new Promise((r) => setTimeout(r, 500));
    }
  }
  if (res.ok) return { ok: true, data: (await res.json()) as T };
  const body = (await res.json().catch(() => null)) as { detail?: Fehler } | null;
  return {
    ok: false,
    status: res.status,
    fehler: body?.detail ?? { code: "fehler", text: "Unbekannter Fehler" },
  };
}
