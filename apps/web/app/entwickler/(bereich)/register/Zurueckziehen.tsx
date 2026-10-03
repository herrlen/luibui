"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { senden } from "@/lib/client-api";

export function Zurueckziehen({ id, version }: { id: string; version: string }) {
  const router = useRouter();
  const [fehler, setFehler] = useState<string | null>(null);
  return (
    <span className="flex items-center gap-2">
      {fehler ? <span className="text-rot">{fehler}</span> : null}
      <button
        type="button"
        className="text-rot underline"
        onClick={async () => {
          if (!window.confirm(`Version ${version} zurückziehen? Sie wird nicht mehr zur Installation angeboten; die Nummer bleibt belegt.`)) return;
          const r = await senden(`/register/versionen/${encodeURIComponent(id)}/zurueckziehen`, "POST");
          if (r.ok) router.refresh();
          else setFehler(r.fehler.text);
        }}
      >
        Zurückziehen
      </button>
    </span>
  );
}
