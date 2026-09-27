import { AMPEL_TEXT } from "@/lib/format";

// The traffic light never relies on colour alone (ENTWICKLERREGELN A5/F6): word and shape always.
const STIL: Record<string, string> = {
  gruen: "bg-gruen-bg text-gruen",
  gelb: "bg-gelb-bg text-gelb",
  rot: "bg-rot-bg text-rot",
  gesperrt: "bg-gesperrt text-white",
  nicht_bewertet: "bg-linie text-ink-2",
};
const FORM: Record<string, string> = { gruen: "●", gelb: "▲", rot: "■", gesperrt: "✕", nicht_bewertet: "○" };

export function Ampel({ wert, gross = false }: { wert: string; gross?: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold ${STIL[wert] ?? STIL.nicht_bewertet} ${
        gross ? "px-4 py-1.5 text-base" : "px-2.5 py-0.5 text-sm"
      }`}
    >
      <span aria-hidden="true">{FORM[wert] ?? "○"}</span>
      {AMPEL_TEXT[wert] ?? wert}
    </span>
  );
}
