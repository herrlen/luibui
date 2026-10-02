import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

// A server component that imports a constant from a "use client" module gets a client reference,
// not the value: SCHWERE_STIL[...] was silently undefined on the moderation pages (02.10.2026).
// Components may cross the boundary, constants (UPPER_CASE names) may not.
const ROOT = path.resolve(__dirname, "..");

function dateien(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = path.join(dir, n);
    if (n === "node_modules" || n === ".next") return [];
    return statSync(p).isDirectory() ? dateien(p) : /\.tsx?$/.test(n) ? [p] : [];
  });
}

function istClient(datei: string): boolean {
  return /^\s*["']use client["']/.test(readFileSync(datei, "utf8"));
}

function aufloesen(von: string, spec: string): string | null {
  const basis = spec.startsWith("@/") ? path.join(ROOT, spec.slice(2)) : path.resolve(path.dirname(von), spec);
  for (const e of [".tsx", ".ts", "/index.tsx", "/index.ts"]) if (existsSync(basis + e)) return basis + e;
  return null;
}

describe("server/client boundary", () => {
  it("server components import no constants from client modules", () => {
    const fehler: string[] = [];
    for (const datei of [...dateien(path.join(ROOT, "app")), ...dateien(path.join(ROOT, "components"))]) {
      if (istClient(datei) || datei.endsWith(".test.tsx")) continue;
      const text = readFileSync(datei, "utf8");
      for (const m of text.matchAll(/import\s*\{([^}]+)\}\s*from\s*"([^"]+)"/g)) {
        const ziel = m[2].startsWith(".") || m[2].startsWith("@/") ? aufloesen(datei, m[2]) : null;
        if (!ziel || !istClient(ziel)) continue;
        const namen = m[1].split(",").map((n) => n.trim().replace(/^type\s+/, ""));
        for (const n of namen) if (/^[A-Z][A-Z0-9_]+$/.test(n)) fehler.push(`${path.relative(ROOT, datei)}: ${n}`);
      }
    }
    expect(fehler).toEqual([]);
  });
});
