// SARIF 2.1.0 export of a report (S2-12) for GitHub Code Scanning and other SARIF viewers.
// Only plain-text message fields are used: package content never reaches a Markdown renderer.
import { statusLabel } from "./format";
import type { BefundStatus, Bericht, Schwere } from "./types";

const SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json";
const PAKET_ANKER = "luibui.json";
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

// SARIF suppressions (§3.35): accepted = the owner keeps the finding on purpose or luibui confirmed
// a false alarm; underReview = disputed, not decided; rejected = luibui kept the finding.
function unterdrueckung(st: BefundStatus | undefined): object[] | undefined {
  if (!st) return undefined;
  const status =
    st.status === "akzeptiert" || st.moderation === "fehlalarm"
      ? "accepted"
      : st.status === "bestritten"
        ? st.moderation === "bestritten"
          ? "rejected"
          : "underReview"
        : null;
  if (!status) return undefined;
  return [{ kind: "external", status, ...(st.begruendung ? { justification: st.begruendung } : {}) }];
}

/** ``status``: the owner's finding status (S3-7), only for downloads from the developer area. */
export function berichtAlsSarif(b: Bericht, status?: Record<string, BefundStatus> | null): object {
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
    const st = x.fingerprint ? status?.[x.fingerprint] : undefined;
    const suppressions = unterdrueckung(st);
    return {
      ...(suppressions ? { suppressions } : {}),
      ruleId: x.rule_id,
      ruleIndex: index,
      level: LEVEL[x.schwere],
      message: { text: `${x.titel}: ${x.erklaerung}` },
      // GitHub Code Scanning rejects results without a location. Findings about the whole
      // package are anchored at its manifest, line 1.
      locations: [
        {
          physicalLocation: {
            artifactLocation: { uri: x.datei ? dateiUri(x.datei) : PAKET_ANKER },
            region: { startLine: x.datei && x.zeile && x.zeile > 0 ? x.zeile : 1 },
          },
        },
      ],
      properties: {
        schwere: x.schwere,
        achse: x.achse,
        nachweisgrad: x.nachweisgrad,
        ...(x.beleg ? { beleg: x.beleg } : {}),
        fix_prompt: x.fix_prompt,
        ...(statusLabel(st) ? { luibui_status: statusLabel(st) } : {}),
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
