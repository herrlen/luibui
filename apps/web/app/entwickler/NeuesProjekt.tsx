"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Feld, Knopf, Meldung } from "@/components/app/Formular";
import { senden } from "@/lib/client-api";

const TYPEN = [
  ["skill", "Skill"],
  ["mcp-server", "MCP-Server"],
  ["plugin", "Plugin"],
  ["tool", "Tool"],
  ["einzeldatei", "Einzeldatei"],
] as const;

export function NeuesProjekt() {
  const router = useRouter();
  const [fehler, setFehler] = useState<string | null>(null);
  return (
    <form
      className="grid gap-4 rounded-[14px] border border-linie bg-surface p-6 sm:grid-cols-[1fr_auto_auto] sm:items-end"
      onSubmit={async (e) => {
        e.preventDefault();
        const form = e.currentTarget;
        const f = new FormData(form);
        const r = await senden<{ id: string }>("/projects", "POST", {
          name: f.get("name"),
          typ: f.get("typ"),
          nach_pruefung_loeschen: f.get("loeschen") === "on",
        });
        if (!r.ok) return setFehler(r.fehler.text);
        router.push(`/projekte/${r.data.id}`);
      }}
    >
      <Feld label="Neues Projekt" name="name" placeholder="z. B. wetter-skill" maxLength={200} required />
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-semibold">Typ</span>
        <select name="typ" className="rounded-lg border border-linie bg-surface px-3 py-2 text-base">
          {TYPEN.map(([wert, text]) => (
            <option key={wert} value={wert}>
              {text}
            </option>
          ))}
        </select>
      </label>
      <Knopf>Anlegen</Knopf>
      <label className="flex items-center gap-2 text-sm sm:col-span-3">
        <input type="checkbox" name="loeschen" /> Dateien nach der Prüfung löschen (nur der Bericht bleibt)
      </label>
      <div className="sm:col-span-3">
        <Meldung text={fehler} />
      </div>
    </form>
  );
}
