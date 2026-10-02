import { headers } from "next/headers";

import { basisUrl, sitemapXml } from "@/lib/seo";

// Only on luibui.com: the middleware maps app.luibui.com/sitemap.xml to /entwickler, where it does not exist.
export async function GET() {
  const h = await headers();
  const xml = sitemapXml(basisUrl(h.get("host") ?? "luibui.com", h.get("x-forwarded-proto")));
  return new Response(xml, { headers: { "Content-Type": "application/xml; charset=utf-8" } });
}
