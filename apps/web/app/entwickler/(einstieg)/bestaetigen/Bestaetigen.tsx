"use client";

import { useEffect, useState } from "react";

import { senden } from "@/lib/client-api";

export function Bestaetigen({ token }: { token: string }) {
  const [stand, setStand] = useState<"laeuft" | "ok" | "fehler">("laeuft");
  const [text, setText] = useState("");
  useEffect(() => {
    void (async () => {
      const r = await senden<{ bestaetigt: boolean }>("/auth/bestaetigen", "POST", { token });
      if (r.ok) setStand("ok");
      else {
        setStand("fehler");
        setText(r.fehler.text);
      }
    })();
  }, [token]);
  if (stand === "laeuft") return <p aria-live="polite">Wird bestätigt …</p>;
  if (stand === "fehler")
    return (
      <p role="alert" className="rounded-lg bg-rot-bg px-4 py-3 text-rot">
        {text}
      </p>
    );
  return (
    <div className="flex flex-col gap-4" role="status">
      <p className="text-lg">Danke, deine E-Mail-Adresse ist bestätigt. Du hast ein Projekt und drei Prüfungen gratis.</p>
      <a href="/" className="inline-flex h-12 w-fit items-center rounded-[10px] bg-petrol px-[22px] font-semibold text-white">
        Zur Übersicht
      </a>
    </div>
  );
}
