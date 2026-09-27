import { describe, expect, it } from "vitest";

import { AMPEL_TEXT, datum, groesse } from "./format";

describe("format", () => {
  it("formats sizes in German", () => {
    expect(groesse(512)).toBe("512 B");
    expect(groesse(1536)).toBe("1,5 KB");
    expect(groesse(5 * 1024 * 1024)).toBe("5 MB");
  });
  it("formats dates in Europe/Berlin", () => {
    expect(datum("2026-09-27T22:30:00Z")).toBe("28. September 2026");
  });
  it("never calls green safe", () => {
    expect(Object.values(AMPEL_TEXT).join(" ").toLowerCase()).not.toContain("sicher");
  });
});
