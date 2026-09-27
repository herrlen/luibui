"use client";

import { useState } from "react";

import { senden } from "@/lib/client-api";

import { aufladen } from "./Aufladen";

export function AufladenKnopf({ label = "Guthaben aufladen" }: { label?: string }) {
  return (
    <button
      type="button"
      onClick={() => aufladen()}
      className="inline-flex h-10 items-center rounded-[10px] bg-petrol px-4 text-sm font-semibold text-white hover:bg-petrol-dunkel"
    >
      {label}
    </button>
  );
}

export function BestaetigungSenden() {
  const [text, setText] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);
  return (
    <span className="flex flex-wrap items-center gap-3">
      <button
        type="button"
        disabled={laeuft}
        onClick={async () => {
          setLaeuft(true);
          const r = await senden("/auth/bestaetigung-senden", "POST");
          setLaeuft(false);
          setText(r.ok ? "Mail ist unterwegs. Bitte schau auch im Spam-Ordner nach." : r.fehler.text);
        }}
        className="text-sm font-semibold text-petrol underline"
      >
        Bestätigungsmail erneut senden
      </button>
      {text ? (
        <span className="text-sm" aria-live="polite">
          {text}
        </span>
      ) : null}
    </span>
  );
}
