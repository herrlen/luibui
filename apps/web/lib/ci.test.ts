import { describe, expect, it } from "vitest";

import { ciWorkflow } from "./ci";

describe("CI workflow snippet", () => {
  it("names the project, reads the token from a secret and uploads SARIF", () => {
    const yml = ciWorkflow("0b9e6c1e-1111-4222-8333-444455556666");
    expect(yml).toContain("projekt: 0b9e6c1e-1111-4222-8333-444455556666");
    expect(yml).toContain("token: ${{ secrets.LUIBUI_TOKEN }}");
    expect(yml).toContain("github/codeql-action/upload-sarif");
    expect(yml).toContain("security-events: write");
    expect(yml).not.toMatch(/lb_/);
  });
});
