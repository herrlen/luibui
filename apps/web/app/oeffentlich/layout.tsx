import Link from "next/link";
import type { ReactNode } from "react";

import { appUrl } from "@/lib/hosts";

const QUELLE = "https://github.com/herrlen/luibui";

export default async function OeffentlichLayout({ children }: { children: ReactNode }) {
  const anmelden = await appUrl("/anmelden");
  const registrieren = await appUrl("/registrieren");
  return (
    <>
      <header>
        <nav className="mx-auto flex max-w-6xl flex-wrap items-center gap-5 px-4 py-5" aria-label="Hauptnavigation">
          <Link href="/" className="font-display text-2xl font-bold text-petrol">
            luibui
          </Link>
          <Link href="/so-pruefen-wir" className="text-sm hover:text-petrol">
            So prüfen wir
          </Link>
          <a href={`${QUELLE}/blob/main/docs/luibui_Pruefkatalog.md`} className="text-sm hover:text-petrol">
            Prüfkatalog
          </a>
          <a href={QUELLE} className="text-sm hover:text-petrol">
            Quellcode
          </a>
          <span className="ml-auto flex items-center gap-3">
            <a href={anmelden} className="text-sm font-semibold hover:text-petrol">
              Anmelden
            </a>
            <a href={registrieren} className="rounded-[10px] bg-petrol px-4 py-2 text-sm font-semibold text-white hover:bg-petrol-dunkel">
              Kostenlos registrieren
            </a>
          </span>
        </nav>
      </header>
      <main id="inhalt" className="mx-auto max-w-6xl px-4 pb-16">
        {children}
      </main>
      <footer className="border-t border-linie">
        <div className="mx-auto flex max-w-6xl flex-wrap gap-4 px-4 py-6 text-sm text-muted">
          <span>luibui · offene, nicht-kommerzielle Prüfstelle</span>
          <span>Quellcode unter AGPL-3.0</span>
          <span>Gehostet in Deutschland</span>
        </div>
      </footer>
    </>
  );
}
