"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Kopieren } from "@/components/Kopieren";
import { Meldung } from "@/components/app/Formular";
import { senden } from "@/lib/client-api";
import { datumZeit } from "@/lib/format";

export type WebhookInfo = { aktiv: boolean; url: string; letzter_lauf: string | null; geheimnis?: string | null };

const KNOPF = "inline-flex h-10 w-fit items-center rounded-[10px] px-4 text-sm font-semibold disabled:opacity-60";

/** Check on push (S5-8): set up, rotate or switch off the webhook of a Git project. */
export function Webhook({ projektId, info }: { projektId: string; info: WebhookInfo }) {
  const router = useRouter();
  const [neu, setNeu] = useState<WebhookInfo | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);
  const pfad = `/projects/${encodeURIComponent(projektId)}/webhook`;
  const einrichten = async () => {
    if (info.aktiv && !window.confirm("Neues Geheimnis erzeugen? Das bisherige gilt dann sofort nicht mehr.")) return;
    setFehler(null);
    const r = await senden<WebhookInfo>(pfad, "POST");
    if (r.ok) {
      setNeu(r.data);
      router.refresh();
    } else setFehler(r.fehler.text);
  };
  return (
    <section aria-labelledby="webhook" className="flex flex-col gap-3 rounded-[14px] border border-linie bg-surface p-6">
      <h2 id="webhook" className="font-display text-xl font-bold">
        Bei jedem Push prüfen
      </h2>
      <p className="text-sm text-muted">
        Ein Webhook startet eine Prüfung, sobald du auf den Standard-Branch pushst oder einen Tag setzt, höchstens eine pro
        Minute. Jede Prüfung kostet wie eine manuelle.
        {info.aktiv ? ` Eingerichtet${info.letzter_lauf ? `, zuletzt ausgelöst am ${datumZeit(info.letzter_lauf)}` : ""}.` : ""}
      </p>
      {neu?.geheimnis ? (
        <div className="flex flex-col gap-3 rounded-lg bg-gelb-bg p-4 text-sm" role="status">
          <p className="font-semibold text-gelb">Jetzt eintragen, das Geheimnis wird nur einmal angezeigt.</p>
          <dl className="grid gap-x-4 gap-y-1 sm:grid-cols-[9rem_1fr]">
            <dt className="text-muted">Payload-URL</dt>
            <dd className="break-all font-mono">{neu.url}</dd>
            <dt className="text-muted">Geheimnis</dt>
            <dd className="break-all font-mono">{neu.geheimnis}</dd>
          </dl>
          <div className="flex flex-wrap gap-2">
            <Kopieren text={neu.url} label="URL kopieren" />
            <Kopieren text={neu.geheimnis} label="Geheimnis kopieren" />
          </div>
          <ul className="list-disc pl-5 text-ink-2">
            <li>
              <span className="font-semibold">GitHub:</span> Settings → Webhooks → Add webhook, Content type
              <span className="font-mono"> application/json</span>, Secret eintragen, Ereignis „Just the push event“.
            </li>
            <li>
              <span className="font-semibold">Codeberg/Forgejo:</span> Einstellungen → Webhooks → Forgejo, Methode POST, Geheimnis
              eintragen, Push-Ereignisse.
            </li>
            <li>
              <span className="font-semibold">GitLab:</span> Settings → Webhooks, Secret token eintragen, „Push events“ und „Tag
              push events“.
            </li>
          </ul>
        </div>
      ) : null}
      <Meldung text={fehler} />
      <div className="flex flex-wrap gap-3">
        <button type="button" className={`${KNOPF} bg-petrol text-white hover:bg-petrol-dunkel`} onClick={einrichten}>
          {info.aktiv ? "Neues Geheimnis erzeugen" : "Webhook einrichten"}
        </button>
        {info.aktiv ? (
          <button
            type="button"
            className={`${KNOPF} border border-rot text-rot`}
            onClick={async () => {
              if (!window.confirm("Webhook abschalten? Pushes lösen dann keine Prüfung mehr aus.")) return;
              const r = await senden(pfad, "DELETE");
              if (r.ok) {
                setNeu(null);
                router.refresh();
              } else setFehler(r.fehler.text);
            }}
          >
            Abschalten
          </button>
        ) : null}
      </div>
    </section>
  );
}
