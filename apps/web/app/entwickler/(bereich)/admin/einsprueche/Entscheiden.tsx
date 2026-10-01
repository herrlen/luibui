"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Meldung } from "@/components/app/Formular";
import { senden } from "@/lib/client-api";

const KNOPF =
  "inline-flex h-10 items-center rounded-[10px] border border-linie-stark bg-surface px-4 text-[15px] font-medium text-ink hover:border-petrol disabled:opacity-60";

export function Entscheiden({ id }: { id: string }) {
  const router = useRouter();
  const [fehler, setFehler] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);

  async function entscheiden(entscheidung: "fehlalarm" | "bestritten") {
    setLaeuft(true);
    const r = await senden(`/admin/einsprueche/${encodeURIComponent(id)}/entscheidung`, "POST", { entscheidung });
    setLaeuft(false);
    if (!r.ok) return setFehler(r.fehler.text);
    router.refresh();
  }

  return (
    <div className="flex flex-col gap-2">
      <Meldung text={fehler} />
      <div className="flex flex-wrap gap-3">
        <button type="button" className={KNOPF} disabled={laeuft} onClick={() => void entscheiden("fehlalarm")}>
          Fehlalarm, Regel anpassen
        </button>
        <button type="button" className={KNOPF} disabled={laeuft} onClick={() => void entscheiden("bestritten")}>
          Befund bleibt (vom Autor bestritten)
        </button>
      </div>
    </div>
  );
}
