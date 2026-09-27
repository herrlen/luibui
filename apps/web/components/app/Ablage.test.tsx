import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { Ablage, istArchiv } from "./Ablage";

const f = (name: string, size = 10) => ({ datei: new File(["x".repeat(size)], name), pfad: name });

describe("Ablage", () => {
  it("shows a visible choose button and a drop hint", () => {
    const html = renderToStaticMarkup(<Ablage modus="dateien" auswahl={[]} setAuswahl={() => {}} />);
    expect(html).toContain("Dateien auswählen");
    expect(html).toContain("Hierher ziehen");
    expect(html).toContain('type="file"');
  });

  it("lists the selection with count and a way to clear it", () => {
    const html = renderToStaticMarkup(
      <Ablage modus="ordner" auswahl={[f("skill/SKILL.md"), f("skill/tool.py")]} setAuswahl={() => {}} />,
    );
    expect(html).toContain("2 Dateien");
    expect(html).toContain("skill/SKILL.md");
    expect(html).toContain("Auswahl leeren");
  });

  it("recognises archives", () => {
    expect(istArchiv("paket.zip")).toBe(true);
    expect(istArchiv("paket.tar.gz")).toBe(true);
    expect(istArchiv("SKILL.md")).toBe(false);
  });
});
