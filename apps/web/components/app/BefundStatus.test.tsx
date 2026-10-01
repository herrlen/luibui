import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type { BefundStatus } from "@/lib/types";

import { BefundStatusSteuerung, StatusMarke } from "./BefundStatus";

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: () => undefined }) }));

const status = (s: Partial<BefundStatus>): BefundStatus => ({
  status: "offen",
  begruendung: null,
  geaendert_am: "2026-10-01T10:00:00Z",
  moderation: null,
  moderation_notiz: null,
  moderiert_am: null,
  ...s,
});

const steuerung = (s?: BefundStatus) =>
  renderToStaticMarkup(<BefundStatusSteuerung scanId="s" fingerprint={"a".repeat(64)} status={s} />);

describe("BefundStatus", () => {
  it("offers accepting and disputing an open finding", () => {
    const html = steuerung();
    expect(html).toContain("Akzeptieren");
    expect(html).toContain("Fehlalarm melden");
    expect(html).not.toContain("Wieder öffnen");
    expect(renderToStaticMarkup(<StatusMarke status={undefined} />)).toBe("");
  });

  it("shows the reason as text and offers reopening", () => {
    const html = steuerung(status({ status: "akzeptiert", begruendung: "<script>x</script>" }));
    expect(html).toContain("&lt;script&gt;");
    expect(html).not.toContain("<script>");
    expect(html).toContain("Wieder öffnen");
  });

  it("shows a pending dispute and the moderation's decision", () => {
    expect(steuerung(status({ status: "bestritten", begruendung: "Platzhalter" }))).toContain("wird von luibui geprüft");
    const entschieden = status({ status: "bestritten", begruendung: "x", moderation: "fehlalarm" });
    expect(steuerung(entschieden)).toContain("Fehlalarm, Regel angepasst");
    expect(renderToStaticMarkup(<StatusMarke status={entschieden} />)).toContain("Fehlalarm, Regel angepasst");
  });

  it("offers nothing for a fixed finding", () => {
    const html = steuerung(status({ status: "behoben" }));
    expect(html).toContain("nicht mehr enthalten");
    expect(html).not.toContain("<button");
  });
});
