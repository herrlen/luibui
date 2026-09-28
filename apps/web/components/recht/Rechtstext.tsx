import type { ReactNode } from "react";

export const KONTAKT = "hallo@luibui.com";

export function Rechtstext({ titel, stand, children }: { titel: string; stand: string; children: ReactNode }) {
  return (
    <article className="flex max-w-3xl flex-col gap-8 pb-8 pt-10 text-[15px] leading-[1.65] text-ink-2 [&_a]:text-petrol [&_a]:underline [&_h2]:font-display [&_h2]:text-2xl [&_h2]:font-bold [&_h2]:tracking-[-0.01em] [&_h2]:text-ink [&_h3]:font-semibold [&_h3]:text-ink [&_section]:flex [&_section]:flex-col [&_section]:gap-3 [&_ul]:list-disc [&_ul]:pl-6">
      <h1 className="font-display text-4xl font-bold tracking-[-0.01em] text-ink sm:text-5xl">{titel}</h1>
      {children}
      <p className="text-sm text-muted">Stand: {stand}</p>
    </article>
  );
}

export function Zeilen({ zeilen }: { zeilen: [string, ReactNode][] }) {
  return (
    <dl className="flex flex-col divide-y divide-linie rounded-[14px] border border-linie bg-surface">
      {zeilen.map(([was, text]) => (
        <div key={was} className="grid gap-1 p-4 sm:grid-cols-[200px_1fr] sm:gap-4">
          <dt className="font-semibold text-ink">{was}</dt>
          <dd>{text}</dd>
        </div>
      ))}
    </dl>
  );
}
