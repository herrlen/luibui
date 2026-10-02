import { describe, expect, it } from "vitest";

import { beispielbericht } from "@/content/beispiel";

import { dateiname, inhalt } from "./export";
import { berichtAlsSarif, OHNE_GEWAEHR } from "./sarif";
import type { BefundStatus, Bericht } from "./types";

type Sarif = {
  version: string;
  runs: {
    tool: { driver: { name: string; rules: { id: string; properties: Record<string, unknown> }[] } };
    results: {
      ruleId: string;
      ruleIndex: number;
      level: string;
      message: { text: string; markdown?: string };
      locations?: { physicalLocation: { artifactLocation: { uri: string }; region?: { startLine: number } } }[];
      suppressions?: { kind: string; status: string; justification?: string }[];
      properties: Record<string, unknown>;
    }[];
    properties: { hinweise: string[] };
  }[];
};

const sarif = (b: Bericht, status?: Record<string, BefundStatus>) => berichtAlsSarif(b, status) as Sarif;

describe("SARIF", () => {
  it("has one result per finding and one rule per rule id", () => {
    const b = beispielbericht();
    const run = sarif(b).runs[0];
    expect(sarif(b).version).toBe("2.1.0");
    expect(run.tool.driver.name).toBe("luibui");
    expect(run.results).toHaveLength(b.befunde.length);
    expect(new Set(run.tool.driver.rules.map((r) => r.id)).size).toBe(run.tool.driver.rules.length);
    for (const r of run.results) expect(run.tool.driver.rules[r.ruleIndex].id).toBe(r.ruleId);
  });

  it("maps severity to level and security-severity", () => {
    const b = beispielbericht();
    const x = b.befunde[0];
    const run = sarif({ ...b, befunde: [{ ...x, schwere: "K" }, { ...x, rule_id: "LB-A09-x", schwere: "N" }] }).runs[0];
    expect(run.results.map((r) => r.level)).toEqual(["error", "note"]);
    expect(run.tool.driver.rules[0].properties["security-severity"]).toBe("9.5");
  });

  it("uses relative URIs, gives every result a location, and plain text only", () => {
    const b = beispielbericht();
    const x = { ...b.befunde[0], beleg: "<script>x</script>" };
    const run = sarif({
      ...b,
      befunde: [
        { ...x, datei: "/skill/mit leer.md", zeile: 3 },
        { ...x, datei: "a.md", zeile: null },
        { ...x, datei: null, zeile: null },
      ],
    }).runs[0];
    expect(run.results[0].locations?.[0].physicalLocation).toEqual({
      artifactLocation: { uri: "skill/mit%20leer.md" },
      region: { startLine: 3 },
    });
    // GitHub Code Scanning rejects results without a location: unknown line → 1, no file →
    // the package manifest.
    expect(run.results[1].locations?.[0].physicalLocation.region).toEqual({ startLine: 1 });
    expect(run.results[2].locations?.[0].physicalLocation).toEqual({
      artifactLocation: { uri: "luibui.json" },
      region: { startLine: 1 },
    });
    expect(run.results.every((r) => r.message.markdown === undefined)).toBe(true);
  });
});

describe("Quick scan disclaimer in every format", () => {
  const schnell = (): Bericht => ({ ...beispielbericht(), scan_art: "schnell" });

  it("is in SARIF, JSON and CSV", () => {
    expect(sarif(schnell()).runs[0].properties.hinweise[0]).toBe(OHNE_GEWAEHR);
    expect((JSON.parse(inhalt(schnell(), "json")) as Bericht).hinweise[0]).toBe(OHNE_GEWAEHR);
    expect(inhalt(schnell(), "csv")).toContain("ohne Gewähr");
  });

  it("is in the CSV even without findings", () => {
    const zeilen = inhalt({ ...schnell(), befunde: [] }, "csv").trim().split("\r\n");
    expect(zeilen).toHaveLength(2);
    expect(zeilen[1]).toMatch(/^"schnell \(ohne Gewähr\)";/);
    expect(zeilen[1].split(";")).toHaveLength(zeilen[0].split(";").length);
  });

  it("is not added to an intensive scan", () => {
    const b = { ...beispielbericht(), scan_art: "intensiv" as const };
    expect((JSON.parse(inhalt(b, "json")) as Bericht).hinweise).not.toContain(OHNE_GEWAEHR);
  });
});

describe("dateiname", () => {
  it("keeps only safe characters", () => {
    const b = { ...beispielbericht(), paket: { name: 'a"b\r\n/../c ä.zip', quelle: "zip" }, geprueft_am: "2026-09-28T08:00:00Z" };
    expect(dateiname(b, "csv")).toBe("luibui-a-b-..-c-.zip-2026-09-28.csv");
    expect(dateiname({ ...b, paket: { name: "..", quelle: "zip" } }, "sarif")).toBe("luibui-paket-2026-09-28.sarif");
  });
});

describe("finding status in the downloads (S3-7)", () => {
  const fp = "f".repeat(64);
  const mitStatus = (): Bericht => {
    const b = beispielbericht();
    return { ...b, befunde: b.befunde.map((x, i) => (i === 0 ? { ...x, fingerprint: fp } : x)) };
  };
  const st = (status: BefundStatus["status"], moderation: BefundStatus["moderation"] = null): Record<string, BefundStatus> => ({
    [fp]: {
      status,
      begruendung: "=HYPERLINK(\"x\") nur Doku",
      geaendert_am: "2026-10-02T08:00:00Z",
      moderation,
      moderation_notiz: null,
      moderiert_am: null,
    },
  });

  it("CSV has status and reason, the reason guarded against formulas", () => {
    const zeilen = inhalt(mitStatus(), "csv", st("akzeptiert")).trim().split("\r\n");
    expect(zeilen[0]).toContain('"status";"status_begruendung"');
    expect(zeilen[1]).toContain('"Akzeptiert";"\'=HYPERLINK(""x"") nur Doku"');
    expect(zeilen[2].endsWith('"";""')).toBe(true); // a finding without status
    expect(zeilen.every((z) => z.split('";"').length === zeilen[0].split('";"').length)).toBe(true);
  });

  it("JSON carries the status map, SARIF a suppression", () => {
    expect(JSON.parse(inhalt(mitStatus(), "json", st("akzeptiert"))).befund_status[fp].status).toBe("akzeptiert");
    const fall = (s: Record<string, BefundStatus>) => sarif(mitStatus(), s).runs[0].results[0];
    expect(fall(st("akzeptiert")).suppressions).toEqual([
      { kind: "external", status: "accepted", justification: '=HYPERLINK("x") nur Doku' },
    ]);
    expect(fall(st("bestritten")).suppressions?.[0].status).toBe("underReview");
    expect(fall(st("bestritten", "fehlalarm")).suppressions?.[0].status).toBe("accepted");
    expect(fall(st("bestritten", "bestritten")).suppressions?.[0].status).toBe("rejected");
    expect(fall(st("behoben")).suppressions).toBeUndefined();
    expect(fall(st("bestritten", "fehlalarm")).properties.luibui_status).toBe("Fehlalarm, Regel angepasst");
  });

  it("without a status nothing changes (public pages, quick scan)", () => {
    expect(JSON.parse(inhalt(mitStatus(), "json")).befund_status).toBeUndefined();
    expect(sarif(mitStatus()).runs[0].results[0].suppressions).toBeUndefined();
  });
});
