"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { senden } from "@/lib/client-api";

export function Schnellscan() {
  const router = useRouter();
  const [fehler, setFehler] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);
  return (
    <form
      className="flex flex-col gap-3 rounded-[18px] border border-linie bg-surface p-6 shadow-[0_30px_60px_-30px_rgba(21,23,28,0.35)]"
      onSubmit={async (e) => {
        e.preventDefault();
        setLaeuft(true);
        setFehler(null);
        const f = new FormData(e.currentTarget);
        const r = await senden<{ id: string }>("/quickscans", "POST", { git_url: f.get("git_url") });
        setLaeuft(false);
        if (!r.ok) return setFehler(r.fehler.text);
        router.push(`/schnellscan/${r.data.id}`);
      }}
    >
      <label htmlFor="git_url" className="font-semibold">
        Schnellscan: öffentliches Repository prüfen
      </label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          id="git_url"
          name="git_url"
          type="url"
          required
          placeholder="https://github.com/besitzer/skill"
          className="flex-1 rounded-[10px] border border-linie px-4 py-3 text-base"
        />
        <button
          type="submit"
          disabled={laeuft}
          className="rounded-[10px] bg-petrol px-5 py-3 font-semibold text-white hover:bg-petrol-dunkel disabled:opacity-60"
        >
          {laeuft ? "Wird geklont …" : "Prüfen"}
        </button>
      </div>
      {fehler ? (
        <p role="alert" className="rounded-lg bg-rot-bg px-3 py-2 text-sm text-rot">
          {fehler}
        </p>
      ) : null}
      <p className="text-xs text-muted">
        GitHub, Codeberg oder GitLab. Eingeschränkter Umfang, <strong>ohne Gewähr</strong>. Gespeichert wird nur der
        Bericht, 7 Tage lang. Nichts aus dem Repository wird ausgeführt.
      </p>
    </form>
  );
}
