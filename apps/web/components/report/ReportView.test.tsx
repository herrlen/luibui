import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { beispielbericht } from "@/content/beispiel";
import { berichtAlsCsv, zelle } from "@/lib/csv";
import type { Befund, Bericht } from "@/lib/types";

import { MitCode } from "./BefundKarte";
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
    expect(html).toContain("27");
    expect(html).toContain("blockiert");
    expect(html).toContain("beispiel/wetter-skill");
    // First finding open, the others collapsed behind a button.
    expect(html.match(/aria-expanded="true"/g)).toHaveLength(1);
    expect(html.match(/aria-expanded="false"/g)).toHaveLength(5);
  });

  it("shows evidence with <script> as text, never as HTML", () => {
    const b = beispielbericht();
    const boese = { ...b.befunde[0], beleg: '<script>alert("x")</script><img src=x onerror=1>' };
    const html = renderToStaticMarkup(<ReportView bericht={{ ...b, befunde: [boese] }} />);
    expect(html).not.toContain("<script>");
    expect(html).not.toContain("<img");
    expect(html).toContain("&lt;script&gt;");
  });

  it("shows a Markdown image link in evidence, explanation and fix as text", () => {
    const b = beispielbericht();
    const md = "![x](https://sammler.invalid/p.png?d=1) [klick](javascript:alert(1))";
    const boese = { ...b.befunde[0], beleg: md, erklaerung: md, fix: md };
    const html = renderToStaticMarkup(<ReportView bericht={{ ...b, befunde: [boese] }} />);
    expect(html).not.toContain("<img");
    expect(html).not.toMatch(/<a [^>]*href="(https:\/\/sammler|javascript)/);
    expect(html).toContain("![x](https://sammler.invalid/p.png?d=1)");
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
    expect(zelle("+1+1")).toBe(`"'+1+1"`);
    expect(zelle("-2+3")).toBe(`"'-2+3"`);
    expect(zelle("\rx")).toBe(`"'\rx"`);
    expect(zelle("\tx")).toBe(`"'\tx"`);
    expect(zelle('a "b"')).toBe(`"a ""b"""`);
  });

  it("exports the example without DSGVO rows", () => {
    const csv = berichtAlsCsv(mitDsgvo(), { showDsgvo: false });
    expect(csv.startsWith("﻿")).toBe(true);
    expect(csv.trim().split("\r\n")).toHaveLength(1 + 6);
    expect(csv).not.toContain("dsgvo");
  });
});

describe("MitCode", () => {
  it("shows backtick names in code type and still escapes everything", () => {
    const html = renderToStaticMarkup(<MitCode text={"Die Datei heißt `.md`, ist aber `<b>x</b>`."} />);
    expect(html).toBe(
      'Die Datei heißt <code class="rounded bg-grund px-1 font-mono text-[0.9em]">.md</code>, ist aber ' +
        '<code class="rounded bg-grund px-1 font-mono text-[0.9em]">&lt;b&gt;x&lt;/b&gt;</code>.',
    );
    expect(renderToStaticMarkup(<MitCode text="ein ` einzelnes" />)).toBe("ein ` einzelnes");
  });
});

describe("Abdeckung", () => {
  it("shows what ran per kind of file and escapes it", () => {
    const b = beispielbericht();
    const html = renderToStaticMarkup(<ReportView bericht={b} showDsgvo={false} />);
    expect(html).toContain("Was geprüft wurde");
    expect(html).toContain("Was der Code tut");
    const boese = { ...b, abdeckung: [{ dateiart: "<b>x</b>", dateien: 1, geprueft: [], offen: ["<i>y</i>"] }] };
    const roh = renderToStaticMarkup(<ReportView bericht={boese} showDsgvo={false} />);
    expect(roh).not.toContain("<b>x</b>");
    expect(roh).toContain("&lt;i&gt;y&lt;/i&gt;");
  });

  it("is left out for reports from before S2-1", () => {
    const alt = { ...beispielbericht(), abdeckung: undefined };
    expect(renderToStaticMarkup(<ReportView bericht={alt} showDsgvo={false} />)).not.toContain("Was geprüft wurde");
  });
});

describe("Hochgestufte Befunde", () => {
  it("names the original severity", () => {
    const b = beispielbericht();
    const erster = { ...b.befunde[0], schwere: "K" as const, hochgestuft_von: "H" as const };
    const html = renderToStaticMarkup(<ReportView bericht={{ ...b, befunde: [erster] }} showDsgvo={false} />);
    expect(html).toContain("hochgestuft von Hoch");
  });
});

describe("Abdeckung", () => {
  it("comes last, and without the DSGVO axis it lists no DSGVO checks", () => {
    const html = renderToStaticMarkup(<ReportView bericht={beispielbericht()} showDsgvo={false} />);
    expect(html.indexOf("Was geprüft wurde")).toBeGreaterThan(html.lastIndexOf("aria-expanded"));
    expect(html).not.toContain("DSGVO: Endpunkte");
    const mit = renderToStaticMarkup(<ReportView bericht={beispielbericht()} />);
    expect(mit).toContain("DSGVO: Endpunkte");
  });
});
