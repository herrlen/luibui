import { describe, expect, it } from "vitest";

import { healthBody } from "./health";

describe("healthBody", () => {
  it("reports the web service as ok", () => {
    expect(healthBody()).toEqual({ status: "ok", service: "web" });
  });
});
