import type { Bericht } from "@/lib/types";

/** What ran for which kind of file. Everything is plain text from the engine; React escapes it. */
export function Abdeckung({ abdeckung }: { abdeckung: NonNullable<Bericht["abdeckung"]> }) {
  if (!abdeckung.length) return null;
  return (
    <section aria-labelledby="abdeckung" className="flex flex-col gap-3">
      <div>
        <h2 id="abdeckung" className="font-display text-xl font-bold">
          Was geprüft wurde
        </h2>
        <p className="mt-1 text-sm text-muted">
          Nicht jede Prüfung passt zu jeder Datei. Keine Befunde heißt: keine bekannten Befunde in dem, was hier als
          geprüft steht.
        </p>
      </div>
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {abdeckung.map((a) => (
          <li key={a.dateiart} className="rounded-[14px] border border-linie bg-surface p-4">
            <p className="font-semibold">
              {a.dateiart} <span className="font-normal text-muted">· {a.dateien} {a.dateien === 1 ? "Datei" : "Dateien"}</span>
            </p>
            <ul className="mt-2 flex flex-col gap-1 text-sm">
              {a.geprueft.map((g) => (
                <li key={g} className="flex gap-2">
                  <span aria-hidden="true" className="text-gruen">
                    ✓
                  </span>
                  <span>
                    <span className="sr-only">Geprüft: </span>
                    {g}
                  </span>
                </li>
              ))}
              {a.offen.map((o) => (
                <li key={o} className="flex gap-2 text-muted">
                  <span aria-hidden="true">–</span>
                  <span>
                    <span className="sr-only">Nicht geprüft: </span>
                    {o}
                  </span>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </section>
  );
}
