"use client";

export function Drucken() {
  return (
    <button
      type="button"
      onClick={() => window.print()}
      className="inline-flex h-10 items-center rounded-[10px] border border-linie-stark px-4 text-sm font-semibold"
    >
      Drucken oder als PDF speichern
    </button>
  );
}
