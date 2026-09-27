"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { senden } from "@/lib/client-api";

export function EinzelLoeschen({ id, name }: { id: string; name: string }) {
  const router = useRouter();
  const [laeuft, setLaeuft] = useState(false);
  return (
    <button
      type="button"
      disabled={laeuft}
      aria-label={`Prüfung ${name} löschen`}
      onClick={async () => {
        if (!window.confirm(`Bericht „${name}“ endgültig löschen?`)) return;
        setLaeuft(true);
        const r = await senden(`/scans/${id}`, "DELETE");
        setLaeuft(false);
        if (r.ok) router.refresh();
        else window.alert(r.fehler.text);
      }}
      className="text-sm text-muted underline hover:text-rot"
    >
      Löschen
    </button>
  );
}
