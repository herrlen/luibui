"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Knopf, Meldung } from "@/components/app/Formular";
import { senden } from "@/lib/client-api";

type Art = "dateien" | "ordner" | "zip" | "text" | "git";
const ARTEN: [Art, string][] = [
  ["dateien", "Datei(en)"],
  ["ordner", "Ordner"],
  ["zip", "ZIP"],
  ["text", "Text einfügen"],
  ["git", "Git-Repository"],
];

export function Upload({ projektId }: { projektId: string }) {
  const router = useRouter();
  const [art, setArt] = useState<Art>("dateien");
  const [fehler, setFehler] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);

  async function absenden(form: HTMLFormElement) {
    const eingabe = new FormData(form);
    const daten = new FormData();
    const dateien = (form.querySelector('input[type="file"]') as HTMLInputElement | null)?.files;
    if (art === "text") {
      daten.set("art", "text");
      daten.set("text", String(eingabe.get("text") ?? ""));
    } else if (art === "git") {
      daten.set("art", "git");
      daten.set("git_url", String(eingabe.get("git_url") ?? ""));
    } else if (art === "zip") {
      if (!dateien?.length) return setFehler("Bitte ein ZIP-Archiv wählen.");
      daten.set("art", "zip");
      daten.append("dateien", dateien[0]);
    } else {
      if (!dateien?.length) return setFehler("Bitte mindestens eine Datei wählen.");
      if (art === "dateien" && dateien.length === 1) {
        daten.set("art", "datei");
        daten.append("dateien", dateien[0]);
      } else {
        daten.set("art", "auswahl");
        for (const d of Array.from(dateien)) {
          daten.append("dateien", d);
          daten.append("pfade", d.webkitRelativePath || d.name);
        }
      }
    }
    setLaeuft(true);
    setFehler(null);
    const r = await senden<{ id: string }>(`/projects/${projektId}/scans`, "POST", daten);
    setLaeuft(false);
    if (!r.ok) return setFehler(r.fehler.pfad ? `${r.fehler.text} (${r.fehler.pfad})` : r.fehler.text);
    router.push(`/pruefungen/${r.data.id}`);
  }

  return (
    <form
      className="flex flex-col gap-4 rounded-[14px] border border-linie bg-surface p-6"
      onSubmit={(e) => {
        e.preventDefault();
        void absenden(e.currentTarget);
      }}
    >
      <h2 className="font-display text-xl font-bold">Neue Version prüfen</h2>
      <div role="radiogroup" aria-label="Art der Eingabe" className="flex flex-wrap gap-2">
        {ARTEN.map(([wert, text]) => (
          <button
            key={wert}
            type="button"
            role="radio"
            aria-checked={art === wert}
            onClick={() => setArt(wert)}
            className={`rounded-full border px-3 py-1 text-sm ${
              art === wert ? "border-petrol bg-petrol text-white" : "border-linie bg-surface"
            }`}
          >
            {text}
          </button>
        ))}
      </div>
      {art === "text" ? (
        <textarea
          name="text"
          rows={10}
          maxLength={200_000}
          required
          placeholder="Inhalt der SKILL.md oder einer Tool-Beschreibung"
          className="rounded-lg border border-linie p-3 font-mono text-sm"
        />
      ) : art === "git" ? (
        <input
          name="git_url"
          type="url"
          required
          placeholder="https://github.com/besitzer/repository"
          className="rounded-lg border border-linie px-3 py-2"
        />
      ) : (
        <input
          key={art}
          type="file"
          multiple={art !== "zip"}
          accept={art === "zip" ? ".zip,application/zip" : undefined}
          {...(art === "ordner" ? { webkitdirectory: "", directory: "" } : {})}
          className="text-sm"
        />
      )}
      <p className="text-xs text-muted">
        Grenzen: Einzeldatei 10 MB, Auswahl 1.000 Dateien und 50 MB, ZIP 50 MB, Text 200 KB. Nichts aus dem Paket wird
        ausgeführt. Git: öffentliche Repositories auf GitHub, Codeberg oder GitLab.
      </p>
      <Meldung text={fehler} />
      <div>
        <Knopf disabled={laeuft}>{laeuft ? "Wird hochgeladen …" : "Prüfen"}</Knopf>
      </div>
    </form>
  );
}
