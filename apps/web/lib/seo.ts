// robots.txt and sitemap for the two hosts. luibui.com is indexed; app.luibui.com (developer area,
// sign-in) never is. Quick-scan results and shared reports carry their own noindex.

export const OEFFENTLICHE_SEITEN = [
  "/",
  "/so-pruefen-wir",
  "/doku",
  "/impressum",
  "/datenschutz",
  "/nutzungsbedingungen",
  "/widerruf",
  "/kontakt",
] as const;

export function basisUrl(host: string, proto: string | null): string {
  const h = host.toLowerCase();
  return `${proto ?? (h.startsWith("localhost") ? "http" : "https")}://${h}`;
}

export function robotsTxt(host: string, proto: string | null): string {
  if (host.toLowerCase().startsWith("app.")) {
    return "User-agent: *\nDisallow: /\n";
  }
  return [
    "User-agent: *",
    "Allow: /",
    "Disallow: /schnellscan/",
    "Disallow: /bericht/",
    "Disallow: /api/",
    "",
    `Sitemap: ${basisUrl(host, proto)}/sitemap.xml`,
    "",
  ].join("\n");
}

export function sitemapXml(basis: string): string {
  const eintraege = OEFFENTLICHE_SEITEN.map(
    (pfad) => `  <url><loc>${basis}${pfad === "/" ? "/" : pfad}</loc></url>`,
  );
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...eintraege,
    "</urlset>",
    "",
  ].join("\n");
}
