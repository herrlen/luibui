"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { LogoMarke } from "@/components/Logo";
import { senden } from "@/lib/client-api";

// The developer area is laid out like an explorer: the main areas on the left, the items of the
// current area next to them, the work on the right (Len, 29.09.2026).

export type ProjektEintrag = { id: string; name: string; ampel: string | null; offenK: number; offenH: number };

const BEREICHE = [
  { href: "/", text: "Übersicht", aktiv: (p: string) => p === "/" },
  { href: "/projekte", text: "Projekte", aktiv: (p: string) => p.startsWith("/projekte") },
  { href: "/pruefungen", text: "Einzelprüfungen", aktiv: (p: string) => p === "/pruefungen" },
  { href: "/register", text: "Register", aktiv: (p: string) => p.startsWith("/register") },
  { href: "/konto", text: "Konto", aktiv: (p: string) => p.startsWith("/konto") || p.startsWith("/guthaben") },
];

const RECHTLICHES = [
  ["/impressum", "Impressum"],
  ["/datenschutz", "Datenschutz"],
  ["/nutzungsbedingungen", "Nutzungsbedingungen"],
  ["/kontakt", "Kontakt"],
] as const;

async function abmelden() {
  await senden("/auth/abmelden", "POST");
  window.location.assign("/anmelden");
}

const MODERATION = { href: "/moderation", text: "Moderation", aktiv: (p: string) => p.startsWith("/moderation") };

export function Hauptleiste({ email, moderation = false }: { email: string; moderation?: boolean }) {
  const pfad = usePathname();
  const bereiche = moderation ? [...BEREICHE, MODERATION] : BEREICHE;
  return (
    <aside className="flex flex-col bg-ink text-white print:hidden lg:sticky lg:top-0 lg:h-screen">
      <Link href="/" className="flex items-center gap-2.5 px-5 pb-2 pt-5 lg:pb-6 lg:pt-6">
        <LogoMarke />
        <span className="font-display text-2xl font-bold tracking-[-0.01em]">luibui</span>
      </Link>
      <nav aria-label="Bereiche" className="overflow-x-auto px-3 pb-3 lg:pb-0">
        <ul className="flex gap-1 lg:flex-col">
          {bereiche.map((b) => {
            const aktiv = b.aktiv(pfad);
            return (
              <li key={b.href}>
                <Link
                  href={b.href}
                  aria-current={aktiv ? "page" : undefined}
                  className={`block whitespace-nowrap rounded-lg px-3 py-2.5 text-[15px] ${
                    aktiv ? "bg-white/12 font-semibold text-white" : "text-white/75 hover:bg-white/6 hover:text-white"
                  }`}
                >
                  {b.text}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="mt-auto hidden flex-col gap-3 border-t border-white/10 px-5 py-5 text-sm lg:flex">
        <p className="break-all text-white/75">{email}</p>
        <button type="button" onClick={() => void abmelden()} className="self-start text-white/90 hover:text-white">
          Abmelden
        </button>
        <nav aria-label="Rechtliches" className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-white/55">
          {RECHTLICHES.map(([href, text]) => (
            <Link key={href} href={href} className="hover:text-white">
              {text}
            </Link>
          ))}
        </nav>
      </div>
    </aside>
  );
}

const PUNKT: Record<string, string> = { gruen: "bg-gruen", gelb: "bg-[#c48a00]", rot: "bg-rot", gesperrt: "bg-gesperrt" };

function Ueberschrift({ children }: { children: string }) {
  return <p className="px-3 pb-2 pt-5 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">{children}</p>;
}

function Eintrag({ href, aktiv, children }: { href: string; aktiv: boolean; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      aria-current={aktiv ? "page" : undefined}
      className={`flex items-center gap-2 rounded-lg px-3 py-2 text-[15px] ${
        aktiv ? "bg-tag font-semibold text-ink" : "text-ink-2 hover:bg-tag/60"
      }`}
    >
      {children}
    </Link>
  );
}

const KONTO = [
  ["#profil", "Profil"],
  ["#passwort", "Passwort"],
  ["#zwei-faktor", "Zwei-Faktor-Anmeldung"],
  ["#email", "E-Mail-Adresse"],
  ["#guthaben", "Guthaben"],
  ["#benachrichtigungen", "Benachrichtigungen"],
  ["#namespaces", "Namespaces"],
  ["#tokens", "API-Tokens"],
  ["#export", "Deine Daten"],
  ["#loeschen", "Konto löschen"],
] as const;

export function Explorer({ projekte }: { projekte: ProjektEintrag[] }) {
  const pfad = usePathname();
  if (pfad.startsWith("/konto") || pfad.startsWith("/guthaben")) {
    return (
      <nav aria-label="Konto" className="hidden border-r border-linie bg-flaeche-2 px-3 print:hidden lg:block">
        <Ueberschrift>Konto</Ueberschrift>
        <ul className="flex flex-col gap-0.5">
          {KONTO.map(([href, text]) => (
            <li key={href}>
              <Eintrag href={`/konto${href}`} aktiv={false}>
                {text}
              </Eintrag>
            </li>
          ))}
        </ul>
      </nav>
    );
  }
  return (
    <nav
      aria-label="Projekte"
      className="hidden border-r border-linie bg-flaeche-2 px-3 print:hidden lg:sticky lg:top-0 lg:block lg:h-screen lg:overflow-y-auto"
    >
      <Ueberschrift>Projekte</Ueberschrift>
      <ul className="flex flex-col gap-0.5">
        {projekte.map((p) => (
          <li key={p.id}>
            <Eintrag href={`/projekte/${p.id}`} aktiv={pfad === `/projekte/${p.id}`}>
              <span
                aria-hidden="true"
                className={`h-2 w-2 shrink-0 rounded-full ${p.ampel ? (PUNKT[p.ampel] ?? "bg-linie-stark") : "bg-linie-stark"}`}
              />
              <span className="min-w-0 flex-1 truncate">{p.name}</span>
              {p.offenK || p.offenH ? (
                <span className={`text-xs font-semibold ${p.offenK ? "text-rot" : "text-gelb"}`}>
                  {p.offenK + p.offenH}
                  <span className="sr-only"> offene kritische oder hohe Befunde</span>
                </span>
              ) : null}
            </Eintrag>
          </li>
        ))}
      </ul>
      {projekte.length === 0 ? <p className="px-3 text-sm text-muted">Noch keine Projekte.</p> : null}
      <Link href="/projekte#neu" className="mt-2 block px-3 py-2 text-sm font-semibold text-petrol hover:underline">
        + Neues Projekt
      </Link>
      <Ueberschrift>Ohne Projekt</Ueberschrift>
      <Eintrag href="/pruefungen" aktiv={pfad === "/pruefungen"}>
        Einzelprüfungen
      </Eintrag>
    </nav>
  );
}
