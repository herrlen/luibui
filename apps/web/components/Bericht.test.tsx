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

describe("finding status in the developer area (S3-7)", () => {
  const b = beispielbericht();
  const fp = "f".repeat(64);
  const mitFp = { ...b, befunde: b.befunde.map((x, i) => (i === 0 ? { ...x, fingerprint: fp } : x)) };
  const projektScan: ScanStatus = {
    ...SCAN,
    scan_art: "intensiv",
    project_id: "11111111-1111-1111-1111-111111111111",
    bericht: mitFp,
    befund_status: {
      [fp]: {
        fingerprint: fp,
        status: "bestritten",
        begruendung: "<script>alert(1)</script> nur Doku",
        moderation: null,
        updated_at: "2026-10-01T08:00:00Z",
      },
    },
    behoben: [{ fingerprint: "e".repeat(64), rule_id: "LB-B01-x", schwere: "H", titel: "Alter Befund", datei: "a.md", zeile: 3 }],
  };

  it("shows the status, the reason as text, the form and what was fixed", () => {
    const html = renderToStaticMarkup(<Bericht scan={projektScan} downloads="bereich" />);
    expect(html).toContain("Bestritten, wird geprüft");
    expect(html).toContain("&lt;script&gt;alert(1)&lt;/script&gt; nur Doku");
    expect(html).not.toContain("<script>alert(1)");
    expect(html).toContain("Status speichern");
    expect(html).toContain("Seit der letzten Prüfung behoben: 1");
    expect(html).toContain("Alter Befund");
  });

  it("never offers the status on public pages", () => {
    const html = renderToStaticMarkup(<Bericht scan={projektScan} downloads="schnellscan" />);
    expect(html).not.toContain("Status speichern");
    expect(html).not.toContain("Bestritten");
    expect(html).not.toContain("Seit der letzten Prüfung behoben");
  });
});
