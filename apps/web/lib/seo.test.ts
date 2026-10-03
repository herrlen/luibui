import { readdirSync, statSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { OEFFENTLICHE_SEITEN, robotsTxt, sitemapXml } from "./seo";

describe("robots.txt", () => {
  it("keeps the developer area out of search engines", () => {
    expect(robotsTxt("app.luibui.com", "https")).toBe("User-agent: *\nDisallow: /\n");
    expect(robotsTxt("APP.localhost:3000", null)).toContain("Disallow: /\n");
  });

  it("allows the public site, hides results and points to the sitemap", () => {
    const text = robotsTxt("luibui.com", "https");
    expect(text).toContain("Allow: /\n");
    expect(text).toContain("Disallow: /schnellscan/");
    expect(text).toContain("Disallow: /bericht/");
    expect(text).toContain("Sitemap: https://luibui.com/sitemap.xml");
    expect(robotsTxt("localhost:3000", null)).toContain("Sitemap: http://localhost:3000/sitemap.xml");
  });
});

describe("sitemap", () => {
  it("lists every public page once", () => {
    const xml = sitemapXml("https://luibui.com");
    expect(xml).toContain("<loc>https://luibui.com/</loc>");
    expect(xml).toContain("<loc>https://luibui.com/doku</loc>");
    expect(xml.match(/<loc>/g)).toHaveLength(OEFFENTLICHE_SEITEN.length);
  });

  it("contains exactly the static public pages that exist", () => {
    const wurzel = path.resolve(__dirname, "../app/oeffentlich");
    const vorhanden = readdirSync(wurzel)
      .filter((n) => statSync(path.join(wurzel, n)).isDirectory() && !n.includes("["))
      .filter((n) => {
        try {
          return statSync(path.join(wurzel, n, "page.tsx")).isFile();
        } catch {
          return false;
        }
      })
      .map((n) => `/${n}`);
    expect([...OEFFENTLICHE_SEITEN].sort()).toEqual(["/", ...vorhanden].sort());
  });
});

describe("sitemap with packages", () => {
  it("adds package pages after the static ones", () => {
    const xml = sitemapXml("https://luibui.com", ["/pakete/acme/wetter"]);
    expect(xml).toContain("<loc>https://luibui.com/pakete/acme/wetter</loc>");
    expect(xml.match(/<loc>/g)).toHaveLength(OEFFENTLICHE_SEITEN.length + 1);
  });
});
