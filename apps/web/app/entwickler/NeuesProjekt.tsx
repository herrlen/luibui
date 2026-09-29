"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Feld, Knopf, Meldung } from "@/components/app/Formular";
import { zahlungNoetig } from "@/components/app/Aufladen";
import { senden } from "@/lib/client-api";

const TYPEN = [
  ["skill", "Skill"],
  ["mcp-server", "MCP-Server"],
  ["plugin", "Plugin"],
  ["tool", "Tool"],
  ["einzeldatei", "Einzeldatei"],
] as const;

const QUELLEN = [
  ["datei", "Datei(en)"],
  ["auswahl", "Ordner"],
  ["zip", "Archiv (ZIP, tar)"],
  ["text", "Eingefügter Text"],
  ["git", "Git-Repository"],
] as const;

const AUSWAHL = "rounded-lg border border-linie bg-surface px-3 py-2 text-base";

export function NeuesProjekt() {
  const router = useRouter();
  const [fehler, setFehler] = useState<string | null>(null);
  const [quelle, setQuelle] = useState<string>("datei");
  return (
    <form method="post"
      className="grid gap-4 rounded-[14px] border border-linie bg-surface p-6 sm:grid-cols-[1fr_auto_auto_auto] sm:items-end"
      onSubmit={async (e) => {
        e.preventDefault();
        const form = e.currentTarget;
        const f = new FormData(form);
        const r = await senden<{ id: string }>("/projects", "POST", {
          name: f.get("name"),
          typ: f.get("typ"),
          quelle,
          git_url: quelle === "git" ? f.get("git_url") : null,
          nach_pruefung_loeschen: f.get("loeschen") === "on",
        });
        if (zahlungNoetig(r)) return;
        if (!r.ok) return setFehler(r.fehler.text);
        router.push(`/projekte/${r.data.id}`);
      }}
    >
      <Feld label="Neues Projekt" name="name" placeholder="z. B. wetter-skill" maxLength={200} required />
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-semibold">Typ</span>
        <select name="typ" className={AUSWAHL}>
          {TYPEN.map(([wert, text]) => (
            <option key={wert} value={wert}>
              {text}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-semibold">Quelle</span>
        <select name="quelle" value={quelle} onChange={(e) => setQuelle(e.target.value)} className={AUSWAHL}>
          {QUELLEN.map(([wert, text]) => (
            <option key={wert} value={wert}>
              {text}
            </option>
          ))}
        </select>
      </label>
      <Knopf>Anlegen</Knopf>
      {quelle === "git" ? (
        <div className="sm:col-span-4">
          <Feld
            label="Adresse des Repositorys"
            name="git_url"
            type="url"
            placeholder="https://github.com/besitzer/repository"
            maxLength={500}
            required
          />
        </div>
      ) : null}
      <label className="flex items-center gap-2 text-sm sm:col-span-4">
        <input type="checkbox" name="loeschen" /> Dateien nach der Prüfung löschen (nur der Bericht bleibt)
      </label>
      <div className="sm:col-span-4">
        <Meldung text={fehler} />
      </div>
    </form>
  );
}
