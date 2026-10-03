import { describe, expect, it } from "vitest";

import { teile, zeilen } from "./sichtbar";

describe("teile", () => {
  it("shows bidi overrides, Unicode tags and control characters as markers", () => {
    const zeile = "if admin‮ { } \u{E0041}\u0007\tende";
    expect(teile(zeile)).toEqual([
      { text: "if admin", unsichtbar: false },
      { text: "<U+202E>", unsichtbar: true },
      { text: " { } ", unsichtbar: false },
      { text: "<U+E0041>", unsichtbar: true },
      { text: "<U+0007>", unsichtbar: true },
      { text: "\tende", unsichtbar: false },
    ]);
  });

  it("leaves umlauts, emoji and tabs alone", () => {
    expect(teile("Größe 👍\tok")).toEqual([{ text: "Größe 👍\tok", unsichtbar: false }]);
  });
});

describe("zeilen", () => {
  it("splits LF and CRLF and drops the empty last line", () => {
    expect(zeilen("a\r\nb\n")).toEqual(["a", "b"]);
    expect(zeilen("a\r")).toEqual(["a"]);
    expect(zeilen("")).toEqual([""]);
  });
});
