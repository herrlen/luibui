import type { Bericht } from "@/lib/types";

import daten from "./beispielbericht.json";

// Build date instead of a fixed date: the example always looks current. Validated against
// spec/report.schema.json and scoring.py in spec/tests/test_schemas.py.
const BUILD = new Date().toISOString();

export function beispielbericht(): Bericht {
  return { ...(daten as Bericht), geprueft_am: BUILD };
}
