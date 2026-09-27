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
};

export type Bericht = {
  scan_art: "schnell" | "intensiv" | "lokal";
  pruefumfang: "paket" | "auswahl" | "einzeldatei";
  geprueft_am: string;
  engine_version: string;
  paket: { name: string; quelle: string; dateien?: number; bytes?: number };
  ampeln: { sicherheit: AmpelSicherheit; dsgvo: AmpelDsgvo; gesamt: AmpelSicherheit };
  note: number;
  freigabe: "freigegeben" | "pruefung_noetig" | "blockiert";
  befunde: Befund[];
  nicht_geprueft: { pruefung: string; grund: string }[];
  hinweise: string[];
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
};

export type Ich = { id: string; email: string; totp_aktiv: boolean };

export type Fehler = { code: string; text: string; pfad?: string | null; felder?: string[] };
