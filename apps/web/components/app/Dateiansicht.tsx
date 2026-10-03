import { SCHWERE_TEXT } from "@/lib/format";
import { SCHWERE_STIL } from "@/lib/schwere";
import { teile, zeilen } from "@/lib/sichtbar";
import type { DateiAnsicht } from "@/lib/types";

const RANG = ["K", "H", "M", "N", "I"];
const ZEILE_STIL: Record<string, string> = {
  K: "bg-rot-bg",
  H: "bg-rot-bg",
  M: "bg-gelb-bg",
  N: "bg-tag",
  I: "bg-tag",
};

/** A package file as text: line numbers, findings at their line, invisible characters as
 *  visible markers. Never rendered as HTML or Markdown (CLAUDE.md rule 6). */
export function Dateiansicht({ datei, download }: { datei: DateiAnsicht; download: string }) {
  const anZeile = new Map<number, DateiAnsicht["befunde"]>();
  for (const b of datei.befunde) {
    if (b.zeile !== null) anZeile.set(b.zeile, [...(anZeile.get(b.zeile) ?? []), b]);
  }
  const ganzeDatei = datei.befunde.filter((b) => b.zeile === null);
  const liste = datei.text === null ? [] : zeilen(datei.text);
  const ausserhalb = [...anZeile.keys()].filter((z) => z > liste.length);
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="min-w-0 break-all font-mono text-xl font-bold">{datei.path}</h1>
        <a
          href={download}
          download
          className="ml-auto inline-flex h-10 items-center rounded-[10px] border border-linie-stark bg-surface px-4 text-sm font-semibold hover:border-petrol"
        >
          Herunterladen
        </a>
      </div>
      <p className="break-all text-xs text-muted">
        SHA-256 {datei.sha256} · {datei.size.toLocaleString("de-DE")} Bytes
      </p>
      {ganzeDatei.length ? (
        <ul className="flex flex-col gap-1.5" aria-label="Befunde zur ganzen Datei">
          {ganzeDatei.map((b, i) => (
            <li key={i} className="flex items-start gap-2 text-sm">
              <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${SCHWERE_STIL[b.schwere] ?? ""}`}>
                {SCHWERE_TEXT[b.schwere] ?? b.schwere}
              </span>
              <span>
                {b.titel} <span className="font-mono text-xs text-muted">{b.rule_id}</span>
              </span>
            </li>
          ))}
        </ul>
      ) : null}
      {datei.text === null ? (
        <p className="rounded-[14px] border border-linie bg-surface p-6 text-ink-2">
          Binärdatei oder kein UTF-8-Text: Die Datei wird nicht angezeigt, nur zum Herunterladen angeboten.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-[14px] border border-linie bg-surface">
          <table className="w-full border-collapse font-mono text-[13px] leading-[1.55]">
            <tbody>
              {liste.map((zeile, i) => {
                const n = i + 1;
                const befunde = anZeile.get(n);
                const schwerste = befunde?.map((b) => b.schwere).sort((a, b) => RANG.indexOf(a) - RANG.indexOf(b))[0];
                return (
                  <tr key={n} id={`z${n}`} className={`scroll-mt-24 align-top ${schwerste ? ZEILE_STIL[schwerste] : ""}`}>
                    <td className="select-none border-r border-linie px-3 text-right text-muted tabular-nums">
                      <a href={`#z${n}`} className="hover:text-petrol">
                        {n}
                      </a>
                    </td>
                    <td className="whitespace-pre px-3">
                      {teile(zeile).map((t, j) =>
                        t.unsichtbar ? (
                          <span key={j} className="rounded bg-gesperrt px-1 text-[11px] text-white" title="Unsichtbares Zeichen">
                            {t.text}
                          </span>
                        ) : (
                          t.text
                        ),
                      )}
                      {befunde ? (
                        <span className="mt-1 flex flex-col gap-1 whitespace-normal pb-1 font-sans">
                          {befunde.map((b, j) => (
                            <span key={j} className="flex items-start gap-2 text-xs">
                              <span className={`rounded-md px-1.5 py-0.5 font-semibold ${SCHWERE_STIL[b.schwere] ?? ""}`}>
                                {SCHWERE_TEXT[b.schwere] ?? b.schwere}
                              </span>
                              <span>
                                {b.titel} <span className="font-mono text-muted">{b.rule_id}</span>
                              </span>
                            </span>
                          ))}
                        </span>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {datei.gekuerzt ? (
        <p className="text-sm text-muted">Angezeigt ist der Anfang der Datei (1 MB). Die ganze Datei gibt es zum Herunterladen.</p>
      ) : null}
      {datei.text !== null && ausserhalb.length ? (
        <p className="text-sm text-muted">Befunde in Zeile {ausserhalb.join(", ")} liegen außerhalb des angezeigten Teils.</p>
      ) : null}
    </div>
  );
}
