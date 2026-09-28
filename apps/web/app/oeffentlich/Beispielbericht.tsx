import { ReportView } from "@/components/report/ReportView";
import { beispielbericht } from "@/content/beispiel";

const H2 = "font-display text-[32px] font-bold leading-[1.1] tracking-[-0.01em] sm:text-[40px]";

// Landing page (S3-9): a static example report, security axis only. No scan, no fetch.
export function Beispielbericht({ registrieren }: { registrieren: string }) {
  return (
    <section aria-labelledby="beispiel" className="flex flex-col gap-7">
      <div className="flex flex-col gap-2.5">
        <h2 id="beispiel" className={H2}>
          So sieht ein luibui-Prüfbericht aus
        </h2>
        <p className="w-fit rounded-md bg-tag px-3 py-1.5 text-[15px] font-medium text-ink">
          Beispielbericht – fiktives Paket, entschärfte Befunde.
        </p>
      </div>
      <ReportView bericht={beispielbericht()} showDsgvo={false} />
      <div className="flex flex-wrap items-center gap-3">
        <a
          href="/beispielbericht.csv"
          download
          className="inline-flex h-12 items-center rounded-[10px] border border-linie-stark bg-surface px-[22px] text-[15px] font-medium text-ink hover:border-petrol"
        >
          Beispiel als CSV
        </a>
        <button
          type="button"
          disabled
          aria-describedby="pdf-folgt"
          className="inline-flex h-12 cursor-not-allowed items-center rounded-[10px] border border-linie bg-flaeche-2 px-[22px] text-[15px] font-medium text-muted"
        >
          Beispiel als PDF
        </button>
        <span id="pdf-folgt" className="text-sm text-muted">
          PDF folgt
        </span>
      </div>
      <div className="flex flex-wrap gap-3">
        <a
          href="#schnellscan"
          className="inline-flex h-12 items-center rounded-[10px] bg-petrol px-[22px] text-[15px] font-semibold text-white hover:bg-petrol-dunkel"
        >
          Eigenes Repository prüfen – Schnellscan
        </a>
        <a
          href={registrieren}
          className="inline-flex h-12 items-center rounded-[10px] bg-ink px-[22px] text-[15px] font-semibold text-grund hover:bg-petrol-dunkel"
        >
          Kostenlos registrieren für den Intensivscan
        </a>
      </div>
    </section>
  );
}
