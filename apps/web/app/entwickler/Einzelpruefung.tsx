"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Ablage, type Eintrag, istArchiv } from "@/components/app/Ablage";
import { zahlungNoetig } from "@/components/app/Aufladen";
import { Meldung } from "@/components/app/Formular";
import { BestaetigungSenden } from "@/components/app/KontoKnoepfe";
import { senden } from "@/lib/client-api";

// Drag and drop on the overview: the check starts right away, without a project. The files are
// not kept; the report stays in the list below until it is deleted.
export function Einzelpruefung() {
  const router = useRouter();
  const [auswahl, setAuswahl] = useState<Eintrag[]>([]);
  const [fehler, setFehler] = useState<string | null>(null);
  const [unbestaetigt, setUnbestaetigt] = useState(false);
  const [laeuft, setLaeuft] = useState(false);

  async function starten(eintraege: Eintrag[]) {
    setAuswahl(eintraege);
    if (!eintraege.length || laeuft) return;
    const daten = new FormData();
    const einzeln = eintraege.length === 1 && !eintraege[0].pfad.includes("/");
    if (einzeln) {
      daten.set("art", istArchiv(eintraege[0].pfad) ? "zip" : "datei");
      daten.append("dateien", eintraege[0].datei);
    } else {
      daten.set("art", "auswahl");
      for (const e of eintraege) {
        daten.append("dateien", e.datei);
        daten.append("pfade", e.pfad);
      }
    }
    setLaeuft(true);
    setFehler(null);
    setUnbestaetigt(false);
    const r = await senden<{ id: string }>("/scans", "POST", daten);
    setLaeuft(false);
    if (zahlungNoetig(r)) return setAuswahl([]);
    if (!r.ok) setUnbestaetigt(r.fehler.code === "email_unbestaetigt");
    if (!r.ok) return setFehler(r.fehler.pfad ? `${r.fehler.text} (${r.fehler.pfad})` : r.fehler.text);
    router.push(`/pruefungen/${r.data.id}`);
  }

  return (
    <section aria-labelledby="einzel" className="flex flex-col gap-3 rounded-[14px] border border-linie bg-surface p-6">
      <div>
        <h2 id="einzel" className="font-display text-xl font-bold">
          Schnell prüfen, ohne Projekt
        </h2>
        <p className="mt-1 text-sm text-muted">
          Datei, Ordner oder Archiv hineinziehen, die Prüfung startet sofort. Die Dateien werden nicht gespeichert, nur
          der Bericht.
        </p>
      </div>
      <Ablage modus="dateien" auswahl={auswahl} setAuswahl={(e) => void starten(e)} />
      {laeuft ? (
        <p className="text-sm text-petrol" aria-live="polite">
          Wird hochgeladen und geprüft …
        </p>
      ) : null}
      <Meldung text={fehler} />
      {unbestaetigt ? <BestaetigungSenden /> : null}
    </section>
  );
}
