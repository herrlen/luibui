import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { Teilen } from "./Teilen";

describe("Teilen", () => {
  it("offers a link when the report is not shared", () => {
    const html = renderToStaticMarkup(<Teilen scanId="a" geteilt={false} />);
    expect(html).toContain("Link zum Teilen erzeugen");
    expect(html).not.toContain("Teilen beenden");
  });

  it("offers a new link and ending the share when it is shared, without showing a link", () => {
    const html = renderToStaticMarkup(<Teilen scanId="a" geteilt={true} />);
    expect(html).toContain("Neuen Link erzeugen");
    expect(html).toContain("Teilen beenden");
    expect(html).not.toContain("/bericht/");
  });
});
