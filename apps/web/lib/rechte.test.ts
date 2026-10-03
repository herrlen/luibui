import { describe, expect, it } from "vitest";

import { rechte } from "./rechte";

describe("rechte", () => {
  it("reads the label from luibui.json", () => {
    const r = rechte({
      rechte: { netzwerk: true, dateien: { lesen: ["~/x"], schreiben: [] }, shell: false, zugangsdaten: false, umgebungsvariablen: ["API_KEY"] },
      endpunkte: [
        { host: "api.wetter.example", land: "DE" },
        { host: "a.example", land: "us" },
        { host: "b.example", land: "US" },
      ],
    });
    expect(Object.fromEntries(r.map((x) => [x.name, x.an]))).toEqual({
      Netzwerk: true,
      Dateien: true,
      Shell: false,
      Zugangsdaten: true,
      Drittland: true,
    });
    expect(r.find((x) => x.name === "Drittland")?.detail).toBe("US");
  });

  it("treats a broken manifest as no rights", () => {
    expect(rechte({}).every((x) => !x.an)).toBe(true);
    expect(rechte({ rechte: "kaputt", endpunkte: "auch" }).every((x) => !x.an)).toBe(true);
  });
});
