import type { Herkunft } from "./types";

// How the origin check (S5-7, H03) is shown: never blocking, but a mismatch is marked as visibly
// as new rights are. Texts are fixed; repository, tag and paths are shown as text by the caller.
export type HerkunftAnzeige = { ton: "gruen" | "gelb" | "rot" | "neutral"; titel: string; text: string };

export function herkunftAnzeige(h: Herkunft | null | undefined): HerkunftAnzeige {
  switch (h?.status) {
    case "uebereinstimmend":
      return {
        ton: "gruen",
        titel: `Stimmt mit dem Git-Tag ${h.tag ?? ""} überein`.trim(),
        text: "Alle Dateien des Pakets liegen genau so im angegebenen Repository.",
      };
    case "abweichend":
      return {
        ton: "rot",
        titel: "Weicht vom Git-Repository ab",
        text: h.hinweis ?? "Das Paket stimmt nicht mit dem angegebenen Repository überein.",
      };
    case "kein_tag":
      return {
        ton: "gelb",
        titel: "Kein passender Git-Tag",
        text: h.hinweis ?? "Im Repository gibt es keinen Tag zu dieser Version.",
      };
    case "nicht_pruefbar":
      return { ton: "gelb", titel: "Herkunft nicht prüfbar", text: h.hinweis ?? "Das Repository ließ sich nicht abgleichen." };
    case "keine_angabe":
      return { ton: "neutral", titel: "Kein Repository angegeben", text: "luibui.json nennt kein Git-Repository." };
    default:
      return { ton: "neutral", titel: "Herkunft nicht geprüft", text: "Diese Version wurde vor dem Herkunftsabgleich veröffentlicht." };
  }
}
