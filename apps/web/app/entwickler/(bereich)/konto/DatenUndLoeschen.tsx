"use client";

import { useState } from "react";

import { Feld, Meldung } from "@/components/app/Formular";
import { senden } from "@/lib/client-api";
import type { Fehler } from "@/lib/types";

const KNOPF = "inline-flex h-12 w-fit items-center rounded-[10px] px-[22px] text-[15px] font-semibold disabled:opacity-60";

function Nachweis({ totp }: { totp: boolean }) {
  return (
    <>
      <Feld label="Passwort" name="passwort" type="password" autoComplete="current-password" required />
      {totp ? <Feld label="Code aus der Authenticator-App" name="code" inputMode="numeric" autoComplete="one-time-code" required /> : null}
    </>
  );
}

/** DSGVO Art. 15 and 20: everything about the account as one ZIP, stored files decrypted. */
export function DatenExport({ totp }: { totp: boolean }) {
  const [fehler, setFehler] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);
  return (
    <form
      method="post"
      className="flex flex-col gap-3"
      onSubmit={async (e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        setLaeuft(true);
        setFehler(null);
        try {
          const res = await fetch("/api/v1/konto/export", {
            method: "POST",
            credentials: "same-origin",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ passwort: f.get("passwort"), code: f.get("code") || undefined }),
          });
          if (!res.ok) {
            const j = (await res.json().catch(() => null)) as { detail?: Fehler } | null;
            setFehler(j?.detail?.text ?? "Der Export ist fehlgeschlagen.");
            return;
          }
          const url = URL.createObjectURL(await res.blob());
          const a = document.createElement("a");
          a.href = url;
          a.download = `luibui-export-${new Date().toISOString().slice(0, 10)}.zip`;
          a.click();
          URL.revokeObjectURL(url);
        } catch {
          setFehler("Keine Verbindung. Bitte später erneut versuchen.");
        } finally {
          setLaeuft(false);
        }
      }}
    >
      <Nachweis totp={totp} />
      <Meldung text={fehler} />
      <button type="submit" disabled={laeuft} className={`${KNOPF} bg-petrol text-white hover:bg-petrol-dunkel`}>
        {laeuft ? "Wird zusammengestellt …" : "Alle Daten herunterladen"}
      </button>
    </form>
  );
}

/** DSGVO Art. 17. Receipts stay for ten years (§ 147 AO), without the account link. */
export function KontoLoeschen({ totp }: { totp: boolean }) {
  const [fehler, setFehler] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);
  return (
    <form
      method="post"
      className="flex flex-col gap-3"
      onSubmit={async (e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        setLaeuft(true);
        const r = await senden("/konto/loeschen", "POST", {
          passwort: f.get("passwort"),
          code: f.get("code") || undefined,
          bestaetigung: f.get("bestaetigung"),
        });
        setLaeuft(false);
        if (r.ok) window.location.assign(window.location.origin.replace("//app.", "//"));
        else setFehler(r.fehler.text);
      }}
    >
      <Nachweis totp={totp} />
      <Feld label="Zur Bestätigung LÖSCHEN eintippen" name="bestaetigung" autoComplete="off" required />
      <Meldung text={fehler} />
      <button type="submit" disabled={laeuft} className={`${KNOPF} bg-rot text-white`}>
        Konto endgültig löschen
      </button>
    </form>
  );
}
