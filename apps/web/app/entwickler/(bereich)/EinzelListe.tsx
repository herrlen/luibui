import Link from "next/link";

import { Ampel } from "@/components/Ampel";
import { datumZeit, STATUS_TEXT } from "@/lib/format";
import type { Einzel } from "@/lib/types";

import { EinzelLoeschen } from "./EinzelLoeschen";

export function EinzelListe({ pruefungen }: { pruefungen: Einzel[] }) {
  return (
    <ul className="flex flex-col gap-2">
      {pruefungen.map((e) => (
        <li key={e.id} className="flex flex-wrap items-center gap-4 rounded-[14px] border border-linie bg-surface p-4">
          <Link href={`/pruefungen/${e.id}`} className="min-w-0 break-all font-semibold hover:text-petrol">
            {e.name}
          </Link>
          <span className="ml-auto flex items-center gap-3 text-sm">
            {e.ampel_gesamt ? (
              <>
                <Ampel wert={e.ampel_gesamt} />
                <span>Note {e.note}</span>
              </>
            ) : (
              <span>Prüfung {STATUS_TEXT[e.status]}</span>
            )}
            <span className="text-muted">{datumZeit(e.created_at)}</span>
            {e.status === "fertig" || e.status === "fehlgeschlagen" ? <EinzelLoeschen id={e.id} name={e.name} /> : null}
          </span>
        </li>
      ))}
    </ul>
  );
}
