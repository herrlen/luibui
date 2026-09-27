import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

// A form submitted before React has loaded falls back to the browser's default GET and would put
// passwords and tokens into the address bar and history. Every form therefore says method="post".
function dateien(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = path.join(dir, n);
    return statSync(p).isDirectory() ? dateien(p) : p.endsWith(".tsx") ? [p] : [];
  });
}

describe("forms", () => {
  it("never fall back to GET", () => {
    const root = path.resolve(__dirname, "..");
    const ohne = [...dateien(path.join(root, "app")), ...dateien(path.join(root, "components"))].filter((f) =>
      /<form(?![^>]*method="post")[\s>]/.test(readFileSync(f, "utf8")),
    );
    expect(ohne).toEqual([]);
  });
});
