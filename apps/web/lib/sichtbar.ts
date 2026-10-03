// Invisible and control characters in package files, made visible for the file view (S4-8).
// Same categories as the engine's `visible()` (Cc, Cf, Co, Cn, Zl, Zp; tab stays): otherwise a
// file could hide text from the very view that is meant to show it (bidi overrides, Unicode tags).

const UNSICHTBAR = /[\p{Cc}\p{Cf}\p{Co}\p{Cn}\p{Zl}\p{Zp}]/u;

export type Teil = { text: string; unsichtbar: boolean };

/** One line split into plain text and visible markers such as `<U+202E>`. */
export function teile(zeile: string): Teil[] {
  const out: Teil[] = [];
  let puffer = "";
  for (const c of zeile) {
    if (c !== "\t" && UNSICHTBAR.test(c)) {
      if (puffer) out.push({ text: puffer, unsichtbar: false });
      puffer = "";
      out.push({ text: `<U+${c.codePointAt(0)!.toString(16).toUpperCase().padStart(4, "0")}>`, unsichtbar: true });
    } else puffer += c;
  }
  if (puffer) out.push({ text: puffer, unsichtbar: false });
  return out;
}

/** Lines of a text file; a trailing CR of Windows line ends is not shown as a marker. */
export function zeilen(text: string): string[] {
  const z = text.split("\n").map((l) => (l.endsWith("\r") ? l.slice(0, -1) : l));
  if (z.length > 1 && z[z.length - 1] === "") z.pop();
  return z;
}
