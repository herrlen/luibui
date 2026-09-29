import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { Brotkrumen } from "./Brotkrumen";

describe("Brotkrumen", () => {
  it("links every level but the current one, which is marked as the page", () => {
    const html = renderToStaticMarkup(
      <Brotkrumen pfad={[{ text: "Übersicht", href: "/" }, { text: "Projekte", href: "/projekte" }, { text: "wetter" }]} />,
    );
    expect(html).toContain('href="/"');
    expect(html).toContain('href="/projekte"');
    expect(html).toMatch(/<span aria-current="page"[^>]*>wetter<\/span>/);
    expect(html.match(/<a /g)).toHaveLength(2);
  });

  it("escapes names it shows", () => {
    const html = renderToStaticMarkup(<Brotkrumen pfad={[{ text: "<script>x</script>" }]} />);
    expect(html).not.toContain("<script>");
  });
});
