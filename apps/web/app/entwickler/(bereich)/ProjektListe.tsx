import Link from "next/link";

import { Ampel } from "@/components/Ampel";
import { datumZeit, STATUS_TEXT } from "@/lib/format";
import type { Projekt } from "@/lib/types";

function OffeneZahl({ k = 0, h = 0 }: { k?: number; h?: number }) {
  if (!k && !h) return null;
  const teile = [k ? `${k} kritisch` : "", h ? `${h} hoch` : ""].filter(Boolean);
  return <span className={k ? "font-semibold text-rot" : "font-semibold text-gelb"}>{teile.join(" · ")} offen</span>;
}

/** Projects as the API sorts them: open critical findings first, then open high ones. */
export function ProjektListe({ projekte }: { projekte: Projekt[] }) {
  if (projekte.length === 0) {
    return (
      <p className="rounded-[14px] border border-dashed border-linie p-8 text-center text-ink-2">
        Noch keine Projekte. Lege eines an und lade dein Paket hoch.
      </p>
    );
  }
  return (
    <ul className="flex flex-col gap-2">
      {projekte.map((p) => (
        <li key={p.id}>
          <Link
            href={`/projekte/${p.id}`}
            className="flex flex-wrap items-center gap-4 rounded-[14px] border border-linie bg-surface px-5 py-4 hover:border-petrol"
          >
            <span className="font-semibold">{p.name}</span>
            <span className="text-sm text-muted">{p.typ}</span>
            <span className="ml-auto flex flex-wrap items-center gap-3 text-sm">
              <OffeneZahl k={p.offen_k} h={p.offen_h} />
              {p.letzte_pruefung?.ampel_gesamt ? (
                <>
                  <Ampel wert={p.letzte_pruefung.ampel_gesamt} />
                  <span>Note {p.letzte_pruefung.note}</span>
                </>
              ) : p.letzte_pruefung ? (
                <span>Prüfung {STATUS_TEXT[p.letzte_pruefung.status]}</span>
              ) : (
                <span className="text-muted">noch nicht geprüft</span>
              )}
              {p.letzte_pruefung ? <span className="text-muted">{datumZeit(p.letzte_pruefung.created_at)}</span> : null}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
