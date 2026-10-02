import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { VerlaufPunkt } from "@/lib/types";

import { Verlauf } from "./Verlauf";

function punkt(i: number, note: number | null, k: number, h: number): VerlaufPunkt {
  return {
    scan_id: `00000000-0000-0000-0000-00000000000${i}`,
    created_at: `2026-10-0${i}T10:00:00Z`,
    note,
    ampel_gesamt: note === null ? null : note > 80 ? "gruen" : "rot",
    pruefumfang: "paket",
    befunde: { K: k, H: h, M: 0, N: 1, I: 1 },
  };
}

describe("project history (S3-5)", () => {
  const punkte = [punkt(1, 20, 2, 1), punkt(2, null, 0, 0), punkt(3, 95, 0, 0)];
  const html = renderToStaticMarkup(<Verlauf punkte={punkte} />);

  it("draws the grade line, a marker per graded check and no NaN", () => {
    expect(html).not.toContain("NaN");
    expect(html.match(/<circle/g)).toHaveLength(2); // the check without a grade has no marker
    expect(html).toContain("<polyline");
  });

  it("has a legend, keyboard targets and the same values as a table", () => {
    for (const t of ["Kritisch", "Hoch", "Mittel", "Niedrig/Info"]) expect(html).toContain(t);
    expect(html.match(/tabindex="0"/g)).toHaveLength(6); // one per check, in both charts
    expect(html).toContain("Als Tabelle");
    expect(html).toContain('href="/pruefungen/00000000-0000-0000-0000-000000000003"');
  });
});
