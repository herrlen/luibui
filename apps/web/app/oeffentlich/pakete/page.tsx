import type { Metadata } from "next";
import Link from "next/link";

import { Ampel } from "@/components/Ampel";
import { datumZeit } from "@/lib/format";
import { apiGet } from "@/lib/server-api";

export const metadata: Metadata = {
  title: "Register – luibui",
  description: "Geprüfte KI-Skills, Plugins, Tools und MCP-Server mit Ampel, Note und Rechte-Label.",
  alternates: { canonical: "/pakete" },
};
export const dynamic = "force-dynamic";

type Eintrag = {
  paket: string;
  version: string;
  beschreibung: string | null;
  typ: string | null;
  ziele: string[];
  rechte: string[];
  ampel: string | null;
  note: number | null;
  veroeffentlicht_am: string;
};

const TYPEN: [string, string][] = [["skill", "Skill"], ["mcp-server", "MCP-Server"], ["plugin", "Plugin"], ["tool", "Tool"]];
const ZIELE: [string, string][] = [
  ["claude", "Claude"],
  ["chatgpt", "ChatGPT"],
  ["gemini", "Gemini"],
  ["mistral", "Mistral"],
  ["openwebui", "Open WebUI"],
  ["mcp", "MCP-Clients"],
];
const AMPELN: [string, string][] = [["gruen", "Grün"], ["gelb", "Gelb"], ["rot", "Rot"]];
const RECHTE: [string, string][] = [
  ["netzwerk", "Netzwerk"],
  ["dateien", "Dateien"],
  ["shell", "Shell"],
  ["zugangsdaten", "Zugangsdaten"],
  ["drittland", "Drittland"],
];
const FELD = "h-11 rounded-[10px] border border-linie-stark bg-surface px-3 text-[15px]";

type Suche = { q?: string; typ?: string; ziel?: string; ampel?: string; ohne?: string | string[] };

function Auswahl({ name, text, optionen, wert }: { name: string; text: string; optionen: [string, string][]; wert?: string }) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="font-semibold">{text}</span>
      <select name={name} defaultValue={wert ?? ""} className={FELD}>
        <option value="">alle</option>
        {optionen.map(([w, t]) => (
          <option key={w} value={w}>
            {t}
          </option>
        ))}
      </select>
    </label>
  );
}

export default async function Register({ searchParams }: { searchParams: Promise<Suche> }) {
  const suche = await searchParams;
  const ohne = Array.isArray(suche.ohne) ? suche.ohne : suche.ohne ? [suche.ohne] : [];
  const params = new URLSearchParams();
  for (const k of ["q", "typ", "ziel", "ampel"] as const) {
    const w = suche[k];
    if (typeof w === "string" && w) params.set(k, w.slice(0, 100));
  }
  for (const o of ohne) params.append("ohne", o);
  const r = await apiGet<Eintrag[]>(`/api/v1/register/pakete?${params.toString()}`, false);
  const pakete = r.ok ? r.data : [];
  const gefiltert = params.toString() !== "";
  return (
    <div className="flex max-w-5xl flex-col gap-6 pt-10">
      <h1 className="font-display text-4xl font-bold">Register</h1>
      <p className="max-w-3xl text-lg text-ink-2">
        Pakete, die ihre Autoren nach einer Prüfung bei luibui veröffentlicht haben. Jede Version ist signiert und zeigt
        den Bericht, mit dem sie veröffentlicht wurde. Grün heißt „keine bekannten Befunde“, nie „sicher“.
      </p>
      <form method="get" role="search" className="flex flex-col gap-4 rounded-[14px] border border-linie bg-surface p-5">
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex min-w-[220px] flex-1 flex-col gap-1 text-sm">
            <span className="font-semibold">Suche</span>
            <input type="search" name="q" defaultValue={suche.q ?? ""} maxLength={100} placeholder="Name oder Beschreibung" className={FELD} />
          </label>
          <Auswahl name="typ" text="Typ" optionen={TYPEN} wert={suche.typ} />
          <Auswahl name="ziel" text="Für" optionen={ZIELE} wert={suche.ziel} />
          <Auswahl name="ampel" text="Ampel" optionen={AMPELN} wert={suche.ampel} />
        </div>
        <fieldset className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
          <legend className="mb-1 font-semibold">Ohne diese Rechte (laut luibui.json)</legend>
          {RECHTE.map(([w, t]) => (
            <label key={w} className="flex items-center gap-2">
              <input type="checkbox" name="ohne" value={w} defaultChecked={ohne.includes(w)} />
              {t}
            </label>
          ))}
        </fieldset>
        <div className="flex gap-3">
          <button type="submit" className="inline-flex h-11 items-center rounded-[10px] bg-petrol px-5 text-[15px] font-semibold text-white hover:bg-petrol-dunkel">
            Suchen
          </button>
          {gefiltert ? (
            <Link href="/pakete" className="inline-flex h-11 items-center px-2 text-sm text-petrol underline">
              Filter zurücksetzen
            </Link>
          ) : null}
        </div>
      </form>
      {!r.ok ? (
        <p className="rounded-[14px] border border-linie bg-surface p-6 text-ink-2">Das Register antwortet gerade nicht.</p>
      ) : pakete.length === 0 ? (
        <p className="rounded-[14px] border border-linie bg-surface p-6 text-ink-2">
          {gefiltert ? "Keine Pakete passen zu diesen Filtern." : "Noch keine Pakete veröffentlicht."}
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {pakete.map((p) => (
            <li key={p.paket}>
              <Link
                href={`/pakete/${p.paket}`}
                className="flex flex-wrap items-start gap-x-6 gap-y-2 rounded-[14px] border border-linie bg-surface p-5 hover:border-petrol"
              >
                <span className="flex min-w-0 flex-1 flex-col gap-1">
                  <span className="break-all font-mono text-lg font-semibold">{p.paket}</span>
                  {p.beschreibung ? <span className="text-sm text-ink-2">{p.beschreibung}</span> : null}
                  <span className="text-xs text-muted">
                    {p.typ ? `${p.typ} · ` : ""}Version {p.version} · {datumZeit(p.veroeffentlicht_am)}
                  </span>
                  <span className="flex flex-wrap gap-1.5 pt-1">
                    {p.rechte.length ? (
                      p.rechte.map((x) => (
                        <span key={x} className="rounded-md bg-gelb-bg px-2 py-0.5 text-xs text-gelb">
                          {RECHTE.find(([w]) => w === x)?.[1] ?? x}
                        </span>
                      ))
                    ) : (
                      <span className="rounded-md bg-tag px-2 py-0.5 text-xs text-ink-2">keine besonderen Rechte</span>
                    )}
                  </span>
                </span>
                <span className="flex items-center gap-3">
                  {p.ampel ? (
                    <span className="w-[104px]">
                      <Ampel wert={p.ampel} />
                    </span>
                  ) : null}
                  {p.note !== null ? <span className="font-display text-2xl font-bold tabular-nums">{p.note}</span> : null}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
