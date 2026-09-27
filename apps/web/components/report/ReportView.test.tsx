import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { beispielbericht } from "@/content/beispiel";
import { berichtAlsCsv, zelle } from "@/lib/csv";
import type { Befund, Bericht } from "@/lib/types";

import { ReportView } from "./ReportView";

const DSGVO_BEFUND: Befund = {
  rule_id: "LB-G07-personenbezogene-daten",
  ebene: "G",
  schwere: "M",
  achse: "dsgvo",
  titel: "Datei enthält personenbezogene Daten",
  erklaerung: "Beispiel",
  datei: "kunden.csv",
  zeile: null,
  beleg: null,
  nachweisgrad: "statisch_erkannt",
  normbezug: ["DSGVO-Art-5"],
  fix: "Entfernen",
  fix_prompt: "Entferne die Daten.",
};

function mitDsgvo(): Bericht {
  const b = beispielbericht();
  return { ...b, ampeln: { ...b.ampeln, dsgvo: "gelb" }, befunde: [...b.befunde, DSGVO_BEFUND] };
}

describe("ReportView", () => {
  it("renders the example report with light, grade and release", () => {
    const html = renderToStaticMarkup(<ReportView bericht={beispielbericht()} showDsgvo={false} />);
    expect(html).toContain("Gesperrt");
    expect(html).toContain("24");
    expect(html).toContain("blockiert");
    expect(html).toContain("beispiel/wetter-skill");
    // First finding open, the others collapsed behind a button.
    expect(html.match(/aria-expanded="true"/g)).toHaveLength(1);
    expect(html.match(/aria-expanded="false"/g)).toHaveLength(4);
  });

  it("shows evidence with <script> as text, never as HTML", () => {
    const b = beispielbericht();
    const boese = { ...b.befunde[0], beleg: '<script>alert("x")</script><img src=x onerror=1>' };
    const html = renderToStaticMarkup(<ReportView bericht={{ ...b, befunde: [boese] }} />);
    expect(html).not.toContain("<script>");
    expect(html).not.toContain("<img");
    expect(html).toContain("&lt;script&gt;");
  });

  it("renders nothing about DSGVO with showDsgvo={false}", () => {
    const html = renderToStaticMarkup(<ReportView bericht={mitDsgvo()} showDsgvo={false} />);
    expect(html).not.toMatch(/DSGVO|personenbezogen/i);
    const voll = renderToStaticMarkup(<ReportView bericht={mitDsgvo()} />);
    expect(voll).toContain("DSGVO");
  });
});

describe("CSV", () => {
  it("neutralises formulas", () => {
    expect(zelle("=HYPERLINK(1)")).toBe(`"'=HYPERLINK(1)"`);
    expect(zelle("@x")).toBe(`"'@x"`);
    expect(zelle("\tx")).toBe(`"'\tx"`);
    expect(zelle('a "b"')).toBe(`"a ""b"""`);
  });

  it("exports the example without DSGVO rows", () => {
    const csv = berichtAlsCsv(mitDsgvo(), { showDsgvo: false });
    expect(csv.startsWith("﻿")).toBe(true);
    expect(csv.trim().split("\r\n")).toHaveLength(1 + 5);
    expect(csv).not.toContain("dsgvo");
  });
});
