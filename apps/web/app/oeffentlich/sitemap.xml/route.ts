import { headers } from "next/headers";

import { basisUrl, sitemapXml } from "@/lib/seo";
import { apiGet } from "@/lib/server-api";

// Only on luibui.com: the middleware maps app.luibui.com/sitemap.xml to /entwickler, where it does not exist.
export async function GET() {
  const h = await headers();
  // Published packages (S4-4); if the register does not answer, the static pages still go out.
  const pakete = await apiGet<{ paket: string }[]>("/api/v1/register/pakete", false);
  const weitere = pakete.ok ? pakete.data.map((p) => `/pakete/${p.paket.split("/").map(encodeURIComponent).join("/")}`) : [];
  const xml = sitemapXml(basisUrl(h.get("host") ?? "luibui.com", h.get("x-forwarded-proto")), weitere);
  return new Response(xml, { headers: { "Content-Type": "application/xml; charset=utf-8" } });
}
