import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { beispielbericht } from "@/content/beispiel";
import type { ScanStatus } from "@/lib/types";

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: () => {} }) }));

const { Bericht } = await import("./Bericht");

const SCAN: ScanStatus = {
  id: "6b39d59b-7f1b-4533-9b8a-7db9fac16cb0",
  project_id: null,
  status: "fertig",
  scan_art: "schnell",
  pruefumfang: "einzeldatei",
  ampeln: null,
  note: 27,
  freigabe: "blockiert",
  fehler: null,
  created_at: "2026-09-30T08:00:00Z",
  finished_at: "2026-09-30T08:00:05Z",
  bericht: beispielbericht(),
  geteilt: false,
};

function links(html: string): string[] {
  return [...html.matchAll(/href="([^"]+)"[^>]*download/g)].map((m) => m[1].replaceAll("&amp;", "&"));
}

describe("report downloads", () => {
  it("offers PDF and CSV on the public quick scan page, without share or developer links", () => {
    const html = renderToStaticMarkup(<Bericht scan={SCAN} downloads="schnellscan" />);
    expect(links(html)).toEqual([
      `/api/v1/quickscans/${SCAN.id}/bericht.pdf`,
      `/api/v1/quickscans/${SCAN.id}/bericht.pdf?umfang=detail`,
      `/schnellscan/${SCAN.id}/bericht.csv`,
    ]);
    expect(html).not.toContain("/pruefungen/");
    expect(html).not.toContain("Teilen");
  });

  it("keeps every format in the developer area", () => {
    const html = renderToStaticMarkup(<Bericht scan={{ ...SCAN, scan_art: "intensiv" }} downloads="bereich" />);
    expect(links(html)).toEqual([
      `/api/v1/scans/${SCAN.id}/bericht.pdf`,
      `/api/v1/scans/${SCAN.id}/bericht.pdf?umfang=detail`,
      `/pruefungen/${SCAN.id}/bericht.csv`,
      `/pruefungen/${SCAN.id}/bericht.json`,
      `/pruefungen/${SCAN.id}/bericht.sarif`,
    ]);
  });

  it("shows no downloads when none are asked for", () => {
    expect(links(renderToStaticMarkup(<Bericht scan={SCAN} />))).toEqual([]);
  });
});
