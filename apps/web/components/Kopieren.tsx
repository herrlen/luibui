"use client";

import { useState } from "react";

export function Kopieren({ text, label = "Kopieren" }: { text: string; label?: string }) {
  const [kopiert, setKopiert] = useState(false);
  return (
    <button
      type="button"
      className="rounded-lg border border-linie bg-surface px-3 py-1 text-sm hover:border-petrol"
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setKopiert(true);
        setTimeout(() => setKopiert(false), 2000);
      }}
    >
      <span aria-live="polite">{kopiert ? "Kopiert" : label}</span>
    </button>
  );
}
