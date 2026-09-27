import Link from "next/link";
import type { ReactNode } from "react";

import { LogoMarke } from "@/components/Logo";
import { appUrl } from "@/lib/hosts";

const BREITE = "mx-auto w-full max-w-[1440px] px-4 sm:px-8 lg:px-16";

export default async function OeffentlichLayout({ children }: { children: ReactNode }) {
  const anmelden = await appUrl("/anmelden");
  const registrieren = await appUrl("/registrieren");
  return (
    <>
      <header className="border-b border-linie">
        <nav
          className={`${BREITE} flex min-h-[72px] flex-wrap items-center gap-x-6 gap-y-3 py-3 lg:gap-x-10`}
          aria-label="Hauptnavigation"
        >
          <Link href="/" className="flex items-center gap-2.5 text-ink">
            <LogoMarke />
            <span className="font-display text-2xl font-bold tracking-[-0.02em]">luibui</span>
          </Link>
          <Link href="/so-pruefen-wir" className="text-[15px] font-medium text-ink hover:text-petrol">
            So prüfen wir
          </Link>
          <span className="ml-auto flex flex-wrap items-center gap-x-5 gap-y-2">
            <a href={anmelden} className="text-[15px] font-medium text-ink hover:text-petrol">
              Anmelden
            </a>
            <a
              href={registrieren}
              className="inline-flex h-11 items-center rounded-[10px] bg-ink px-[18px] text-[15px] font-semibold text-grund hover:bg-petrol-dunkel"
            >
              Kostenlos registrieren
            </a>
          </span>
        </nav>
      </header>
      <main id="inhalt" className={`${BREITE} pb-24`}>
        {children}
      </main>
      <footer className="border-t border-linie">
        <div className={`${BREITE} flex flex-col gap-10 pb-10 pt-14`}>
          <div className="grid gap-8 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <div className="flex flex-col gap-2.5">
              <span className="font-display text-[22px] font-bold tracking-[-0.02em]">luibui</span>
              <span className="leading-[1.55] text-muted">
                Offene, nicht-kommerzielle Prüfstelle für KI-Skills, Plugins, Tools und MCP-Server.
              </span>
              <span className="text-muted">Quellcode unter AGPL-3.0</span>
            </div>
            <div className="flex flex-col gap-2.5">
              <span className="font-semibold">Prüfen</span>
              <Link href="/so-pruefen-wir" className="text-ink-2 hover:text-petrol">
                So prüfen wir
              </Link>
              <a href={anmelden} className="text-ink-2 hover:text-petrol">
                Anmelden
              </a>
              <a href={registrieren} className="text-ink-2 hover:text-petrol">
                Kostenlos registrieren
              </a>
            </div>
          </div>
          <p className="text-[13px] text-muted">Gehostet in Deutschland</p>
        </div>
      </footer>
    </>
  );
}
