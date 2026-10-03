"use client";

import { useState } from "react";

import { Kopieren } from "@/components/Kopieren";
import { Meldung } from "@/components/app/Formular";
import { ciWorkflow } from "@/lib/ci";
import { senden } from "@/lib/client-api";

/** CI (S5-5): a project token and the GitHub Actions workflow that uses it. */
export function CiAnbindung({ projektId, projektName }: { projektId: string; projektName: string }) {
  const [token, setToken] = useState<string | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);
  const yml = ciWorkflow(projektId);
  return (
    <section aria-labelledby="ci" className="flex flex-col gap-3 rounded-[14px] border border-linie bg-surface p-6">
      <h2 id="ci" className="font-display text-xl font-bold">
        In der CI prüfen
      </h2>
      <p className="text-sm text-muted">
        Die GitHub Action lädt das Paket bei jedem Push hoch, wartet auf den Bericht, legt die Befunde als SARIF in GitHub Code
        Scanning ab und lässt den Lauf ab der gewählten Ampel fehlschlagen. Sie braucht einen Projekt-Token: Er darf nur
        Prüfungen dieses Projekts starten und lesen. Jede Prüfung kostet wie eine manuelle.
      </p>
      {token ? (
        <div className="flex flex-col gap-2 rounded-lg bg-gelb-bg p-4 text-sm" role="status">
          <p className="font-semibold text-gelb">
            Jetzt als Repository-Secret <span className="font-mono">LUIBUI_TOKEN</span> eintragen (Settings → Secrets and
            variables → Actions). Der Token wird nur einmal angezeigt und gilt ein Jahr.
          </p>
          <p className="break-all font-mono">{token}</p>
          <div>
            <Kopieren text={token} label="Token kopieren" />
          </div>
        </div>
      ) : null}
      <Meldung text={fehler} />
      <button
        type="button"
        className="inline-flex h-10 w-fit items-center rounded-[10px] bg-petrol px-4 text-sm font-semibold text-white hover:bg-petrol-dunkel"
        onClick={async () => {
          setFehler(null);
          const r = await senden<{ token: string }>("/tokens", "POST", {
            name: `CI ${projektName}`.slice(0, 100),
            project_id: projektId,
            gueltig_tage: 365,
          });
          if (r.ok) setToken(r.data.token);
          else setFehler(r.fehler.text);
        }}
      >
        Projekt-Token erzeugen
      </button>
      <p className="text-sm text-ink-2">
        Workflow als <span className="font-mono">.github/workflows/luibui.yml</span> anlegen; <span className="font-mono">pfad</span>{" "}
        ist der Ordner des Pakets. Geprüft werden nur eingecheckte Dateien.
      </p>
      <pre className="overflow-x-auto rounded-[14px] border border-linie bg-flaeche-2 p-4 font-mono text-xs">{yml}</pre>
      <div>
        <Kopieren text={yml} label="Workflow kopieren" />
      </div>
      <p className="text-xs text-muted">Projekt-Tokens widerrufst du im Konto unter API-Tokens.</p>
    </section>
  );
}
