"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Feld, Knopf, Meldung } from "@/components/app/Formular";
import { senden } from "@/lib/client-api";

export type NamespaceInfo = { id: string; name: string; created_at: string };

/** Namespaces for the register (S4-1): the "org" in org/paket, several per account. */
export function Namespaces({ namespaces }: { namespaces: NamespaceInfo[] }) {
  const router = useRouter();
  const [fehler, setFehler] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);
  return (
    <section
      id="namespaces"
      aria-labelledby="namespaces-titel"
      className="flex scroll-mt-6 flex-col gap-4 rounded-[14px] border border-linie bg-surface p-6"
    >
      <h2 id="namespaces-titel" className="font-display text-xl font-bold">
        Namespaces
      </h2>
      <p className="text-sm text-muted">
        Unter einem Namespace veröffentlichst du Pakete im Register, zum Beispiel <span className="font-mono">dein-name/paket</span>.
        Namen, die sich mit einem bestehenden oder geschützten Namen verwechseln lassen, sind nicht möglich.
      </p>
      {namespaces.length ? (
        <ul className="flex flex-col divide-y divide-linie text-sm">
          {namespaces.map((n) => (
            <li key={n.id} className="flex items-center gap-4 py-2">
              <span className="font-mono font-semibold">{n.name}</span>
              <button
                type="button"
                className="ml-auto text-sm text-rot underline"
                onClick={async () => {
                  if (!window.confirm(`Namespace „${n.name}“ löschen?`)) return;
                  const r = await senden(`/namespaces/${encodeURIComponent(n.id)}`, "DELETE");
                  if (r.ok) router.refresh();
                  else setFehler(r.fehler.text);
                }}
              >
                Löschen
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      <form
        method="post"
        className="flex flex-wrap items-end gap-3"
        onSubmit={async (e) => {
          e.preventDefault();
          const form = e.currentTarget;
          setFehler(null);
          setLaeuft(true);
          const r = await senden("/namespaces", "POST", { name: new FormData(form).get("name") });
          setLaeuft(false);
          if (r.ok) {
            form.reset();
            router.refresh();
          } else setFehler(typeof r.fehler.text === "string" ? r.fehler.text : "Ungültiger Name.");
        }}
      >
        <Feld label="Neuer Namespace" name="name" placeholder="z. B. acme-tools" maxLength={39} autoComplete="off" required />
        <Knopf disabled={laeuft}>Anlegen</Knopf>
      </form>
      <Meldung text={fehler} />
    </section>
  );
}
