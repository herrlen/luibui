"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Meldung } from "@/components/app/Formular";
import { senden } from "@/lib/client-api";

const KNOPF =
  "inline-flex h-10 items-center rounded-[10px] border border-linie-stark bg-surface px-4 text-[15px] font-medium text-ink hover:border-petrol disabled:opacity-60";

/** The decision on a dispute. The owner sees it with the note at the finding. */
export function Entscheiden({ id }: { id: string }) {
  const router = useRouter();
  const [notiz, setNotiz] = useState("");
  const [fehler, setFehler] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);

  async function entscheiden(ergebnis: "bestritten" | "fehlalarm") {
    setLaeuft(true);
    const r = await senden(`/moderation/einsprueche/${encodeURIComponent(id)}/entscheidung`, "POST", {
      ergebnis,
      notiz: notiz || null,
    });
    setLaeuft(false);
    if (!r.ok) return setFehler(r.fehler.text);
    router.push("/moderation");
    router.refresh();
  }

  return (
    <section className="flex flex-col gap-3 rounded-[14px] border border-linie bg-surface p-5">
      <h2 className="font-display text-lg font-bold">Entscheidung</h2>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-semibold">Notiz an den Autor (optional)</span>
        <textarea
          maxLength={2000}
          rows={3}
          value={notiz}
          onChange={(e) => setNotiz(e.target.value)}
          className="rounded-xl border border-linie-stark bg-surface px-3 py-2 text-base focus:border-petrol"
        />
      </label>
      <div className="flex flex-wrap gap-2">
        <button type="button" disabled={laeuft} onClick={() => void entscheiden("fehlalarm")} className={KNOPF}>
          Fehlalarm, Regel wird angepasst
        </button>
        <button type="button" disabled={laeuft} onClick={() => void entscheiden("bestritten")} className={KNOPF}>
          Befund bleibt: vom Autor bestritten
        </button>
      </div>
      <p className="text-xs text-muted">
        „Fehlalarm“ heißt: die Regel wird angepasst, danach fällt der Befund bei der nächsten Prüfung weg. Bericht, Ampel
        und Note ändern sich durch die Entscheidung nicht.
      </p>
      <Meldung text={fehler} />
    </section>
  );
}
