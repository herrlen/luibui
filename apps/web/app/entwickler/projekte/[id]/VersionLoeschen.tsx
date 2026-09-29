"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { senden } from "@/lib/client-api";

export function VersionLoeschen({ projektId, versionId, nummer }: { projektId: string; versionId: string; nummer: number }) {
  const router = useRouter();
  const [laeuft, setLaeuft] = useState(false);
  return (
    <button
      type="button"
      disabled={laeuft}
      aria-label={`Version ${nummer} löschen`}
      onClick={async () => {
        if (!window.confirm(`Dateien von Version ${nummer} endgültig löschen? Der Prüfbericht bleibt.`)) return;
        setLaeuft(true);
        const r = await senden(`/projects/${projektId}/versions/${versionId}`, "DELETE");
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
