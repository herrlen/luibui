// The rights label of a package (Konzept §7): what luibui.json declares. Whether the code keeps to
// it is what the GDPR axis of the report checks (G03, G04).

const EWR = new Set(
  "AT BE BG CY CZ DE DK EE ES FI FR GR HR HU IE IT LT LU LV MT NL PL PT RO SE SI SK IS LI NO".split(" "),
);

export type Recht = { name: string; an: boolean; detail?: string };

function liste(wert: unknown): string[] {
  return Array.isArray(wert) ? wert.filter((x): x is string => typeof x === "string") : [];
}

export function rechte(manifest: Record<string, unknown>): Recht[] {
  const r = (manifest.rechte ?? {}) as Record<string, unknown>;
  const dateien = (r.dateien ?? {}) as Record<string, unknown>;
  const lesen = liste(dateien.lesen);
  const schreiben = liste(dateien.schreiben);
  const endpunkte = Array.isArray(manifest.endpunkte) ? (manifest.endpunkte as Record<string, unknown>[]) : [];
  const laender = [
    ...new Set(
      endpunkte.map((e) => String(e.land ?? "").toUpperCase()).filter((l) => l && !EWR.has(l)),
    ),
  ].sort();
  const umgebung = liste(r.umgebungsvariablen);
  return [
    { name: "Netzwerk", an: r.netzwerk === true, detail: endpunkte.length ? `${endpunkte.length} Endpunkt(e)` : undefined },
    {
      name: "Dateien",
      an: lesen.length + schreiben.length > 0,
      detail: lesen.length + schreiben.length ? `lesen ${lesen.length}, schreiben ${schreiben.length}` : undefined,
    },
    { name: "Shell", an: r.shell === true },
    { name: "Zugangsdaten", an: r.zugangsdaten === true || umgebung.length > 0, detail: umgebung.length ? `${umgebung.length} Umgebungsvariable(n)` : undefined },
    { name: "Drittland", an: laender.length > 0, detail: laender.length ? laender.join(", ") : undefined },
  ];
}
