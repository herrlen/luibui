// Shapes of the API responses (apps/api/luibui_api, spec/report.schema.json).

export type AmpelSicherheit = "gruen" | "gelb" | "rot" | "gesperrt";
export type AmpelDsgvo = "gruen" | "gelb" | "rot" | "nicht_bewertet";
export type Schwere = "K" | "H" | "M" | "N" | "I";

export type Befund = {
  rule_id: string;
  ebene: string;
  schwere: Schwere;
  achse: "sicherheit" | "dsgvo";
  titel: string;
  erklaerung: string;
  datei: string | null;
  zeile: number | null;
  beleg: string | null;
  nachweisgrad: string;
  normbezug: string[];
  fix: string;
  fix_prompt: string;
  /** Set when the correlation raised the finding (S2-5). */
  hochgestuft_von?: Schwere;
  fingerprint?: string;
};

export type Bericht = {
  scan_art: "schnell" | "intensiv" | "lokal";
  pruefumfang: "paket" | "auswahl" | "einzeldatei";
  geprueft_am: string;
  engine_version: string;
  paket: { name: string; version?: string | null; quelle: string; dateien?: number; bytes?: number };
  ampeln: { sicherheit: AmpelSicherheit; dsgvo: AmpelDsgvo; gesamt: AmpelSicherheit };
  note: number;
  freigabe: "freigegeben" | "pruefung_noetig" | "blockiert";
  befunde: Befund[];
  nicht_geprueft: { pruefung: string; grund: string }[];
  hinweise: string[];
  /** Missing in reports from before S2-1. */
  abdeckung?: { dateiart: string; dateien: number; geprueft: string[]; offen: string[] }[];
};

export type ScanStatus = {
  id: string;
  project_id: string | null;
  status: "wartend" | "laeuft" | "fertig" | "fehlgeschlagen";
  scan_art: string;
  pruefumfang: string;
  ampeln: { sicherheit: string; dsgvo: string; gesamt: string } | null;
  note: number | null;
  freigabe: string | null;
  fehler: string | null;
  created_at: string;
  finished_at: string | null;
  bericht: Bericht | null;
  /** A share link is active (S2-12). */
  geteilt?: boolean;
  /** Owner view of a project check (S3-7): status per fingerprint. */
  befund_status?: Record<string, BefundStatus>;
  /** Owner view of a project check: findings of the previous check that are gone now. */
  behoben?: BehobenerBefund[];
};

export type Pruefungskurz = {
  id: string;
  status: ScanStatus["status"];
  pruefumfang: string;
  ampel_gesamt: AmpelSicherheit | null;
  note: number | null;
  freigabe: string | null;
  created_at: string;
  finished_at: string | null;
};

export type Projekt = {
  id: string;
  name: string;
  typ: string;
  quelle: string;
  git_url: string | null;
  nach_pruefung_loeschen: boolean;
  created_at: string;
  letzte_pruefung: Pruefungskurz | null;
  /** Open critical and high findings of the last finished check (S2-8). */
  offen_k?: number;
  offen_h?: number;
};

export type Version = {
  id: string;
  nummer: number;
  angelegt: string;
  dateien: number;
  bytes: number;
  commit_sha: string | null;
  dateien_geloescht: boolean;
  pruefung: Pruefungskurz | null;
};

export type OffenerBefund = {
  project_id: string;
  projekt: string;
  scan_id: string;
  rule_id: string;
  schwere: "K" | "H";
  titel: string;
  datei: string | null;
  zeile: number | null;
};

export type Ich = { id: string; email: string; totp_aktiv: boolean; email_bestaetigt: boolean; admin?: boolean };

/** Status of a finding within a project (S3-7). "behoben" is derived, never set by hand. */
export type BefundStatus = {
  fingerprint: string;
  status: "offen" | "behoben" | "akzeptiert" | "bestritten";
  begruendung: string | null;
  moderation: "fehlalarm" | "bestritten" | null;
  updated_at: string;
};

export type BehobenerBefund = {
  fingerprint: string;
  rule_id: string;
  schwere: string;
  titel: string;
  datei: string | null;
  zeile: number | null;
};

export type Einspruch = {
  id: string;
  rule_id: string | null;
  titel: string | null;
  datei: string | null;
  zeile: number | null;
  begruendung: string | null;
  updated_at: string;
  moderation: "fehlalarm" | "bestritten" | null;
  moderiert_am: string | null;
};

export type Fehler = { code: string; text: string; pfad?: string | null; felder?: string[] };

export type Einzel = {
  id: string;
  name: string;
  status: ScanStatus["status"];
  pruefumfang: string;
  ampel_gesamt: AmpelSicherheit | null;
  note: number | null;
  created_at: string;
};

export type Guthaben = {
  aktiv: boolean;
  stand: number;
  email_bestaetigt: boolean;
  pakete: { id: string; pruefungen: number; preis_cent: number; preis_text: string }[];
  kaeufe: { id: string; belegnummer: number | null; pruefungen: number; betrag_cent: number; status: string; bezahlt_am: string | null }[];
};

export type Beleg = {
  belegnummer: number;
  datum: string;
  kaeufer_email: string | null;
  beschreibung: string;
  betrag_cent: number;
  waehrung: string;
  paypal_transaktion: string | null;
};
