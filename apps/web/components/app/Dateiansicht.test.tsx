import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { DateiAnsicht } from "@/lib/types";

import { Dateiansicht } from "./Dateiansicht";

const DATEI: DateiAnsicht = {
  id: "f",
  path: "scripts/tool.py",
  size: 60,
  sha256: "ab".repeat(32),
  text: "import os\r\nos.system('echo') # ‮<script>alert(1)</script>\nx = 1\n",
  gekuerzt: false,
  befunde: [
    { zeile: 2, schwere: "H", titel: "Shell-Aufruf", rule_id: "LB-C01-shell", fingerprint: "a" },
    { zeile: null, schwere: "N", titel: "Ganze Datei", rule_id: "LB-X", fingerprint: "b" },
    { zeile: 9, schwere: "M", titel: "Weit hinten", rule_id: "LB-Y", fingerprint: "c" },
  ],
};

describe("Dateiansicht", () => {
  const html = renderToStaticMarkup(<Dateiansicht datei={DATEI} download="/dl" />);

  it("renders package text as text and invisible characters as markers", () => {
    expect(html).not.toContain("<script>");
    expect(html).toContain("&lt;script&gt;alert(1)&lt;/script&gt;");
    expect(html).toContain("&lt;U+202E&gt;");
    expect(html).not.toContain("‮");
    expect(html).not.toContain("&lt;U+000D&gt;"); // CRLF is not a finding
  });

  it("marks findings at their line, lists whole-file findings and out-of-range lines", () => {
    expect(html.match(/<tr id="z\d+"/g)).toHaveLength(3);
    expect(html).toMatch(/<tr id="z2" class="[^"]*bg-rot-bg/);
    expect(html).toContain("Shell-Aufruf");
    expect(html).toContain("Ganze Datei");
    expect(html).toContain("Befunde in Zeile 9 liegen außerhalb");
  });

  it("offers binary files only as download", () => {
    const bin = renderToStaticMarkup(<Dateiansicht datei={{ ...DATEI, text: null }} download="/dl" />);
    expect(bin).toContain("nur zum Herunterladen");
    expect(bin).toContain('href="/dl"');
    expect(bin).not.toContain("<table");
  });
});
