import { redirect } from "next/navigation";

import { apiGet } from "@/lib/server-api";
import Link from "next/link";

import { Brotkrumen } from "@/components/app/Brotkrumen";
import { AufladenKnopf } from "@/components/app/KontoKnoepfe";
import { datumZeit } from "@/lib/format";
import type { Guthaben, Ich } from "@/lib/types";

import { Abmelden } from "./Abmelden";
import { DatenExport, KontoLoeschen } from "./DatenUndLoeschen";
import { type NamespaceInfo, Namespaces } from "./Namespaces";
import { EmailAendern, PasswortAendern, ZweiFaktor } from "./Sicherheit";
import { type TokenInfo, Tokens } from "./Tokens";

export const metadata = { title: "Konto – luibui" };
export const dynamic = "force-dynamic";

export default async function Konto() {
  const ich = await apiGet<Ich>("/api/v1/auth/ich");
  if (!ich.ok) redirect("/anmelden");
  const tokens = await apiGet<TokenInfo[]>("/api/v1/tokens");
  const guthaben = await apiGet<Guthaben>("/api/v1/guthaben");
  const speicher = await apiGet<{ belegt: number; grenze: number }>("/api/v1/konto/speicher");
  const namespaces = await apiGet<NamespaceInfo[]>("/api/v1/namespaces");
  return (
    <div className="flex flex-col gap-6">
      <Brotkrumen pfad={[{ text: "Übersicht", href: "/" }, { text: "Konto" }]} />
      <h1 className="font-display text-3xl font-bold">Konto</h1>
      <section id="profil" className="scroll-mt-6 rounded-[14px] border border-linie bg-surface p-6 text-sm">
        <p>
          <span className="font-semibold">E-Mail:</span> {ich.data.email}
        </p>
        <p className="mt-1">
          <span className="font-semibold">Zwei-Faktor-Anmeldung:</span> {ich.data.totp_aktiv ? "aktiv" : "nicht aktiv"}
        </p>
        {speicher.ok ? <SpeicherAnzeige belegt={speicher.data.belegt} grenze={speicher.data.grenze} /> : null}
      </section>
      <div className="grid gap-6 lg:grid-cols-2">
        <section aria-labelledby="passwort" className="flex flex-col gap-3 rounded-[14px] border border-linie bg-surface p-6">
          <h2 id="passwort" className="scroll-mt-6 font-display text-xl font-bold">
            Passwort ändern
          </h2>
          <PasswortAendern totp={ich.data.totp_aktiv} />
        </section>
        <section
          id="zwei-faktor"
          aria-labelledby="zwei-faktor-titel"
          className="flex scroll-mt-6 flex-col gap-3 rounded-[14px] border border-linie bg-surface p-6"
        >
          <h2 id="zwei-faktor-titel" className="font-display text-xl font-bold">
            Zwei-Faktor-Anmeldung
          </h2>
          <ZweiFaktor aktiv={ich.data.totp_aktiv} />
        </section>
        <section
          id="email"
          aria-labelledby="email-titel"
          className="flex scroll-mt-6 flex-col gap-3 rounded-[14px] border border-linie bg-surface p-6"
        >
          <h2 id="email-titel" className="font-display text-xl font-bold">
            E-Mail-Adresse ändern
          </h2>
          <p className="text-sm text-muted">
            Die bisherige Adresse gilt, bis du den Link in der Mail an die neue Adresse anklickst. Danach bekommt die
            bisherige Adresse eine Nachricht.
          </p>
          <EmailAendern totp={ich.data.totp_aktiv} />
        </section>
      </div>
      {guthaben.ok && guthaben.data.aktiv ? (
        <section aria-labelledby="guthaben" className="flex flex-col gap-3 rounded-[14px] border border-linie bg-surface p-6">
          <div className="flex flex-wrap items-center gap-4">
            <h2 id="guthaben" className="font-display text-xl font-bold">
              Guthaben: {guthaben.data.stand} Prüfungen
            </h2>
            <span className="ml-auto">
              <AufladenKnopf />
            </span>
          </div>
          {guthaben.data.kaeufe.length ? (
            <ul className="flex flex-col divide-y divide-linie text-sm">
              {guthaben.data.kaeufe.map((k) => (
                <li key={k.id} className="flex flex-wrap items-center gap-4 py-2">
                  <span>{k.bezahlt_am ? datumZeit(k.bezahlt_am) : ""}</span>
                  <span>{k.pruefungen} Prüfungen</span>
                  <span>
                    {Math.floor(k.betrag_cent / 100)},{String(k.betrag_cent % 100).padStart(2, "0")} €
                  </span>
                  <Link href={`/konto/beleg/${k.id}`} className="ml-auto text-petrol underline">
                    Beleg
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted">Noch keine Käufe.</p>
          )}
        </section>
      ) : null}
      <Namespaces namespaces={namespaces.ok ? namespaces.data : []} />
      <Tokens tokens={tokens.ok ? tokens.data : []} />
      <section aria-labelledby="export" className="flex flex-col gap-3 rounded-[14px] border border-linie bg-surface p-6">
        <h2 id="export" className="font-display text-xl font-bold">
          Deine Daten
        </h2>
        <p className="text-sm text-muted">
          Ein ZIP mit allem, was luibui zu deinem Konto speichert: Kontodaten, Tokens (ohne Schlüssel), Guthaben, Käufe,
          Protokoll, Projekte mit allen Berichten und die gespeicherten Dateien.
        </p>
        <DatenExport totp={ich.data.totp_aktiv} />
      </section>
      <section aria-labelledby="loeschen" className="flex flex-col gap-3 rounded-[14px] border border-rot bg-surface p-6">
        <h2 id="loeschen" className="font-display text-xl font-bold">
          Konto löschen
        </h2>
        <p className="text-sm text-muted">
          Löscht dein Konto mit allen Projekten, Dateien, Berichten und Tokens sofort und endgültig. Kaufbelege bewahren
          wir zehn Jahre auf, wie das Steuerrecht es verlangt (§ 147 AO), dann ohne Verbindung zu einem Konto.
        </p>
        <KontoLoeschen totp={ich.data.totp_aktiv} />
      </section>
      <div>
        <Abmelden />
      </div>
    </div>
  );
}

function SpeicherAnzeige({ belegt, grenze }: { belegt: number; grenze: number }) {
  const anteil = grenze > 0 ? Math.min(1, belegt / grenze) : 0;
  return (
    <div className="mt-4 flex max-w-md flex-col gap-1.5">
      <p>
        <span className="font-semibold">Speicher:</span> {megabyte(belegt)} von {megabyte(grenze)} belegt
      </p>
      <div
        role="meter"
        aria-label="Belegter Speicher"
        aria-valuemin={0}
        aria-valuemax={grenze}
        aria-valuenow={belegt}
        aria-valuetext={`${Math.round(anteil * 100)} Prozent`}
        className="h-2 overflow-hidden rounded-full bg-flaeche-2"
      >
        <div className={`h-full ${anteil >= 0.9 ? "bg-rot" : "bg-petrol"}`} style={{ width: `${anteil * 100}%` }} />
      </div>
      <p className="text-muted">Gezählt werden die gespeicherten Projekt-Dateien aller Versionen.</p>
    </div>
  );
}

function megabyte(bytes: number): string {
  const mb = bytes / (1024 * 1024);
  return `${mb < 10 && mb > 0 ? mb.toLocaleString("de-DE", { maximumFractionDigits: 1 }) : Math.round(mb)} MB`;
}
