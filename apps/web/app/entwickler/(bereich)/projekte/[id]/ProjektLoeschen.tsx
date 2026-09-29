"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Meldung } from "@/components/app/Formular";
import { senden } from "@/lib/client-api";

/** The name has to be typed to confirm: deleting removes all versions, files and reports. */
export function ProjektLoeschen({ id, name }: { id: string; name: string }) {
  const router = useRouter();
  const [eingabe, setEingabe] = useState("");
  const [fehler, setFehler] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);
  return (
    <form
      method="post"
      className="flex flex-col gap-3"
      onSubmit={async (e) => {
        e.preventDefault();
        setLaeuft(true);
        const r = await senden(`/projects/${id}`, "DELETE");
        setLaeuft(false);
        if (!r.ok) return setFehler(r.fehler.text);
        router.push("/projekte");
        router.refresh();
      }}
    >
      <label className="flex flex-col gap-1 text-sm">
        <span>
          Zum Bestätigen den Projektnamen <strong className="break-all">{name}</strong> eintippen
        </span>
        <input
          value={eingabe}
          onChange={(e) => setEingabe(e.target.value)}
          autoComplete="off"
          className="h-11 max-w-sm rounded-xl border border-linie-stark bg-surface px-4 text-base focus:border-rot"
        />
      </label>
      <Meldung text={fehler} />
      <div>
        <button
          type="submit"
          disabled={eingabe.trim() !== name || laeuft}
          className="inline-flex h-11 items-center rounded-[10px] bg-rot px-5 text-[15px] font-semibold text-white disabled:opacity-40"
        >
          {laeuft ? "Wird gelöscht …" : "Projekt endgültig löschen"}
        </button>
      </div>
    </form>
  );
}
