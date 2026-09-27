import type { Fehler } from "./types";

// Browser side: same-origin requests to /api/v1 (proxied to the API on app.luibui.com).

export type Ergebnis<T> = { ok: true; data: T } | { ok: false; status: number; fehler: Fehler };

export async function senden<T>(
  path: string,
  method: "POST" | "DELETE",
  body?: FormData | Record<string, unknown>,
): Promise<Ergebnis<T>> {
  const init: RequestInit = { method, credentials: "same-origin", headers: { accept: "application/json" } };
  if (body instanceof FormData) init.body = body;
  else if (body) {
    init.body = JSON.stringify(body);
    (init.headers as Record<string, string>)["content-type"] = "application/json";
  }
  let res: Response;
  try {
    res = await fetch(`/api/v1${path}`, init);
  } catch {
    return { ok: false, status: 0, fehler: { code: "netzwerk", text: "Keine Verbindung. Bitte später erneut versuchen." } };
  }
  if (res.status === 204) return { ok: true, data: undefined as T };
  const json = (await res.json().catch(() => null)) as (T & { detail?: Fehler }) | null;
  if (res.ok) return { ok: true, data: json as T };
  return { ok: false, status: res.status, fehler: json?.detail ?? { code: "fehler", text: "Unbekannter Fehler" } };
}
