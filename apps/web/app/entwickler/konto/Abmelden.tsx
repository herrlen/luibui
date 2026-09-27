"use client";

import { senden } from "@/lib/client-api";

export function Abmelden() {
  return (
    <button
      type="button"
      className="rounded-[10px] border border-linie bg-surface px-4 py-2 font-semibold hover:border-petrol"
      onClick={async () => {
        await senden("/auth/abmelden", "POST");
        window.location.assign("/anmelden");
      }}
    >
      Abmelden
    </button>
  );
}
