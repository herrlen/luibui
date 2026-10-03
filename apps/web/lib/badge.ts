// The README badge (S5-4): "luibui | Gelb · 80". Only the light and the grade go into the SVG,
// never text from the package, so nothing in it can be injected. Plain colours for contrast with
// white text (WCAG AA at this size), independent of the site theme.

const FARBE: Record<string, string> = {
  gruen: "#17613c",
  gelb: "#7a5200",
  rot: "#a3261b",
  gesperrt: "#5c1a13",
};
const WORT: Record<string, string> = { gruen: "Grün", gelb: "Gelb", rot: "Rot", gesperrt: "Gesperrt" };

function breite(text: string): number {
  return Math.round(text.length * 6.6 + 12);
}

export function badgeSvg(ampel: string | null, note: number | null): string {
  const links = "luibui";
  const rechts =
    ampel && WORT[ampel] ? `${WORT[ampel]}${Number.isInteger(note) ? ` · ${note}` : ""}` : "nicht gefunden";
  const farbe = (ampel && FARBE[ampel]) || "#6b6b6b";
  const bl = breite(links);
  const br = breite(rechts);
  const titel = `luibui: ${rechts}`;
  return [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${bl + br}" height="20" role="img" aria-label="${titel}">`,
    `<title>${titel}</title>`,
    `<rect width="${bl}" height="20" fill="#1f2328"/>`,
    `<rect x="${bl}" width="${br}" height="20" fill="${farbe}"/>`,
    `<g fill="#fff" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11">`,
    `<text x="${bl / 2}" y="14" text-anchor="middle">${links}</text>`,
    `<text x="${bl + br / 2}" y="14" text-anchor="middle">${rechts}</text>`,
    `</g></svg>`,
  ].join("");
}
