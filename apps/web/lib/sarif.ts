// SARIF 2.1.0 export of a report (S2-12) for GitHub Code Scanning and other SARIF viewers.
// Only plain-text message fields are used: package content never reaches a Markdown renderer.
import type { Bericht, Schwere } from "./types";

const SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json";
export const OHNE_GEWAEHR = "Schnellscan: eingeschränkter Umfang, ohne Gewähr.";

const LEVEL: Record<Schwere, "error" | "warning" | "note"> = {
  K: "error",
  H: "error",
  M: "warning",
  N: "note",
  I: "note",
};

// GitHub sorts security alerts by this score (critical ≥ 9, high ≥ 7, medium ≥ 4, low > 0).
const SECURITY_SEVERITY: Record<Schwere, string> = { K: "9.5", H: "7.5", M: "5.0", N: "2.0", I: "0.1" };

export function berichtAlsSarif(b: Bericht): object {
  const regeln = new Map<string, number>();
  const rules: object[] = [];
  const results = b.befunde.map((x) => {
    let index = regeln.get(x.rule_id);
    if (index === undefined) {
      index = rules.length;
      regeln.set(x.rule_id, index);
      rules.push({
        id: x.rule_id,
        shortDescription: { text: x.titel },
        fullDescription: { text: x.erklaerung },
        help: { text: x.fix },
        properties: {
          tags: [x.achse, `ebene-${x.ebene}`, ...x.normbezug],
          "security-severity": SECURITY_SEVERITY[x.schwere],
        },
      });
    }
    return {
      ruleId: x.rule_id,
      ruleIndex: index,
      level: LEVEL[x.schwere],
      message: { text: `${x.titel}: ${x.erklaerung}` },
      ...(x.datei
        ? {
            locations: [
              {
                physicalLocation: {
                  artifactLocation: { uri: dateiUri(x.datei) },
                  ...(x.zeile && x.zeile > 0 ? { region: { startLine: x.zeile } } : {}),
                },
              },
            ],
          }
        : {}),
      properties: {
        schwere: x.schwere,
        achse: x.achse,
        nachweisgrad: x.nachweisgrad,
        ...(x.beleg ? { beleg: x.beleg } : {}),
        fix_prompt: x.fix_prompt,
      },
    };
  });
  return {
    $schema: SCHEMA,
    version: "2.1.0",
    runs: [
      {
        tool: {
          driver: {
            name: "luibui",
            version: b.engine_version,
            informationUri: "https://luibui.com",
            rules,
          },
        },
        results,
        properties: {
          scan_art: b.scan_art,
          pruefumfang: b.pruefumfang,
          paket: b.paket.name,
          geprueft_am: b.geprueft_am,
          ampeln: b.ampeln,
          note: b.note,
          freigabe: b.freigabe,
          hinweise: hinweise(b),
        },
      },
    ],
  };
}

/** Report hints, with the quick-scan disclaimer first (CLAUDE.md rule 12). */
export function hinweise(b: Bericht): string[] {
  return b.scan_art === "schnell" && !b.hinweise.includes(OHNE_GEWAEHR) ? [OHNE_GEWAEHR, ...b.hinweise] : b.hinweise;
}

// SARIF wants a relative URI reference: encode each path segment, keep the slashes.
function dateiUri(pfad: string): string {
  return pfad
    .replace(/^\/+/, "")
    .split("/")
    .map((teil) => encodeURIComponent(teil))
    .join("/");
}
