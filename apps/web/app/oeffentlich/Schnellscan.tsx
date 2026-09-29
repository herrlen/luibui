"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { senden } from "@/lib/client-api";

const MAX_DATEI = 2 * 1024 * 1024;

export function Schnellscan() {
  const router = useRouter();
  const [art, setArt] = useState<"git" | "datei">("git");
  const [fehler, setFehler] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);
  return (
    <form method="post"
      id="schnellscan"
      aria-labelledby="schnellscan-titel"
      className="flex flex-col gap-5 rounded-[18px] border border-linie bg-surface p-6 shadow-[0_30px_60px_-30px_rgba(21,23,28,0.35)] sm:p-8"
      onSubmit={async (e) => {
        e.preventDefault();
        setLaeuft(true);
        setFehler(null);
        const f = new FormData(e.currentTarget);
        let body: FormData | Record<string, unknown> = { git_url: f.get("git_url") };
        if (art === "datei") {
          const datei = f.get("datei");
          if (!(datei instanceof File) || !datei.name) {
            setLaeuft(false);
            return setFehler("Bitte eine Datei auswählen.");
          }
          if (datei.size > MAX_DATEI) {
            setLaeuft(false);
            return setFehler("Der Schnellscan nimmt eine Datei bis 2 MB. Größere Pakete prüfst du im Entwicklerbereich.");
          }
          body = new FormData();
          body.append("datei", datei);
        }
        const r = await senden<{ id: string }>("/quickscans", "POST", body);
        setLaeuft(false);
        if (!r.ok) return setFehler(r.fehler.text);
        router.push(`/schnellscan/${r.data.id}`);
      }}
    >
      <div className="flex flex-col gap-2">
        <h2 id="schnellscan-titel" className="font-display text-[28px] font-bold leading-tight tracking-[-0.01em]">
          Schnellscan
        </h2>
        <div role="radiogroup" aria-label="Was prüfen?" className="flex flex-wrap gap-2">
          {(
            [
              ["git", "Öffentliches Repository"],
              ["datei", "Eine Datei oder ein ZIP bis 2 MB"],
            ] as const
          ).map(([wert, text]) => (
            <button
              key={wert}
              type="button"
              role="radio"
              aria-checked={art === wert}
              onClick={() => {
                setArt(wert);
                setFehler(null);
              }}
              className={`rounded-full border px-3 py-1 text-sm ${
                art === wert ? "border-petrol bg-petrol text-white" : "border-linie bg-surface text-ink-2"
              }`}
            >
              {text}
            </button>
          ))}
        </div>
      </div>
      <div className="flex flex-col gap-2 sm:flex-row">
        <div className="flex h-15 min-w-0 flex-1 items-center gap-3 rounded-xl border border-linie-stark bg-surface px-[18px] focus-within:outline-3 focus-within:outline-offset-2 focus-within:outline-petrol">
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#5A5F6A"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            className="shrink-0"
          >
            <path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7" />
            <path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7" />
          </svg>
          {art === "git" ? (
            <input
              id="git_url"
              name="git_url"
              type="url"
              required
              aria-label="Adresse des öffentlichen Repositorys"
              placeholder="https://github.com/besitzer/skill"
              className="min-w-0 flex-1 bg-transparent text-[17px] text-ink outline-none"
            />
          ) : (
            <input
              id="datei"
              name="datei"
              type="file"
              required
              aria-label="Datei oder ZIP bis 2 MB"
              className="min-w-0 flex-1 bg-transparent text-[15px] text-ink outline-none file:mr-3 file:rounded-lg file:border-0 file:bg-grund file:px-3 file:py-1.5"
            />
          )}
        </div>
        <button
          type="submit"
          disabled={laeuft}
          className="h-15 shrink-0 rounded-xl bg-petrol px-[26px] text-base font-semibold text-white hover:bg-petrol-dunkel disabled:opacity-60"
        >
          {laeuft ? (art === "git" ? "Wird geklont …" : "Wird geprüft …") : "Prüfen"}
        </button>
      </div>
      {fehler ? (
        <p role="alert" className="rounded-lg bg-rot-bg px-3 py-2 text-sm text-rot">
          {fehler}
        </p>
      ) : null}
      <p className="text-[13px] leading-[1.55] text-muted">
        {art === "git" ? "GitHub, Codeberg oder GitLab." : "Ein ZIP wird wie ein Paket entpackt und geprüft."} Eingeschränkter
        Umfang, <strong>ohne Gewähr</strong>. Gespeichert wird nur der Bericht, 7 Tage lang. Nichts aus dem Paket wird
        ausgeführt.
      </p>
    </form>
  );
}
