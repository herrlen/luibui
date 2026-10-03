import { describe, expect, it } from "vitest";

import { herkunftAnzeige } from "./herkunft";

describe("origin check display", () => {
  it("marks a mismatch in red and a match in green", () => {
    expect(herkunftAnzeige({ status: "abweichend", hinweis: "2 Dateien …" })).toMatchObject({ ton: "rot", text: "2 Dateien …" });
    expect(herkunftAnzeige({ status: "uebereinstimmend", tag: "v1.0.0" })).toMatchObject({
      ton: "gruen",
      titel: "Stimmt mit dem Git-Tag v1.0.0 überein",
    });
  });

  it("is neutral without a repository or for older versions", () => {
    expect(herkunftAnzeige({ status: "keine_angabe" }).ton).toBe("neutral");
    expect(herkunftAnzeige(null).titel).toBe("Herkunft nicht geprüft");
    expect(herkunftAnzeige({ status: "kein_tag" }).ton).toBe("gelb");
  });
});
