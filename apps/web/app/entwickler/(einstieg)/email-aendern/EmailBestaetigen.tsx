"use client";

import { useEffect, useState } from "react";

import { senden } from "@/lib/client-api";

export function EmailBestaetigen({ token }: { token: string }) {
  const [stand, setStand] = useState<"laeuft" | "ok" | "fehler">("laeuft");
  const [text, setText] = useState("");
  useEffect(() => {
    void (async () => {
      const r = await senden<{ email: string }>("/auth/email-bestaetigen", "POST", { token });
      if (r.ok) {
        setStand("ok");
        setText(r.data.email);
      } else {
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
      <p className="text-lg">
        Erledigt. Du meldest dich ab jetzt mit <span className="font-semibold">{text}</span> an.
      </p>
      <a href="/konto" className="inline-flex h-12 w-fit items-center rounded-[10px] bg-petrol px-[22px] font-semibold text-white">
        Zum Konto
      </a>
    </div>
  );
}
