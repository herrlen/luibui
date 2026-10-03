import { describe, expect, it } from "vitest";

import { badgeSvg } from "./badge";

describe("badgeSvg", () => {
  it("shows light and grade", () => {
    const svg = badgeSvg("gelb", 80);
    expect(svg).toContain(">Gelb · 80<");
    expect(svg).toContain('fill="#7a5200"');
    expect(svg.startsWith("<svg")).toBe(true);
  });

  it("never puts unknown values into the SVG", () => {
    const svg = badgeSvg('"><script>alert(1)</script>', 1.5);
    expect(svg).not.toContain("script");
    expect(svg).toContain(">nicht gefunden<");
    expect(badgeSvg("gruen", null)).toContain(">Grün<");
  });
});
