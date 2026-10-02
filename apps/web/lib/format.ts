// Formatting in one place (ENTWICKLERREGELN B): German locale, Europe/Berlin.

const DATUM = new Intl.DateTimeFormat("de-DE", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "Europe/Berlin",
});
const TAG = new Intl.DateTimeFormat("de-DE", { dateStyle: "long", timeZone: "Europe/Berlin" });

export function datumZeit(iso: string): string {
  return DATUM.format(new Date(iso));
}

export function datum(iso: string): string {
  return TAG.format(new Date(iso));
}

export function groesse(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toLocaleString("de-DE", { maximumFractionDigits: 1 })} KB`;
  return `${(kb / 1024).toLocaleString("de-DE", { maximumFractionDigits: 1 })} MB`;
}

export const AMPEL_TEXT: Record<string, string> = {
  gruen: "Grün",
  gelb: "Gelb",
  rot: "Rot",
  gesperrt: "Gesperrt",
  nicht_bewertet: "nicht bewertet",
};

export const FREIGABE_TEXT: Record<string, string> = {
  freigegeben: "freigegeben",
  pruefung_noetig: "Prüfung nötig",
  blockiert: "blockiert",
};

export const SCHWERE_TEXT: Record<string, string> = {
  K: "Kritisch",
  H: "Hoch",
  M: "Mittel",
  N: "Niedrig",
  I: "Info",
};

export const UMFANG_TEXT: Record<string, string> = {
  paket: "Paket",
  auswahl: "Dateiauswahl ohne Manifest",
  einzeldatei: "Einzeldatei",
};

export const STATUS_TEXT: Record<string, string> = {
  wartend: "wartet",
  laeuft: "läuft",
  fertig: "fertig",
  fehlgeschlagen: "fehlgeschlagen",
};

/** S3-7: the status of a finding as the owner set it, or as the next check found it. */
export const BEFUND_STATUS_TEXT: Record<string, string> = {
  offen: "Offen",
  behoben: "Behoben",
  akzeptiert: "Akzeptiert",
  bestritten: "Bestritten",
};

/** luibui's decision on a dispute (Konzept §6). */
/** One label for a finding's status, as the developer area shows it; "" for an open finding. */
export function statusLabel(st: { status: string; moderation: string | null } | null | undefined): string {
  if (!st || st.status === "offen") return "";
  return st.moderation ? (MODERATION_TEXT[st.moderation] ?? st.moderation) : (BEFUND_STATUS_TEXT[st.status] ?? st.status);
}

export const MODERATION_TEXT: Record<string, string> = {
  bestritten: "Vom Autor bestritten",
  fehlalarm: "Fehlalarm, Regel angepasst",
};
