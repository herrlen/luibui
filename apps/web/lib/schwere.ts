// Badge colours per severity. Plain module (no "use client"), so server components can read it.
export const SCHWERE_STIL: Record<string, string> = {
  K: "bg-gesperrt text-white",
  H: "bg-rot-bg text-rot",
  M: "bg-gelb-bg text-gelb",
  N: "bg-tag text-ink-2",
  I: "bg-tag text-ink-2",
};
