import "server-only";

import { headers } from "next/headers";

// Links from the public site to the developer area: same scheme, "app." in front of the host.
export async function appUrl(pfad: string): Promise<string> {
  const h = await headers();
  const host = (h.get("host") ?? "luibui.com").replace(/^app\./, "");
  const proto = h.get("x-forwarded-proto") ?? (host.startsWith("localhost") ? "http" : "https");
  return `${proto}://app.${host}${pfad}`;
}
