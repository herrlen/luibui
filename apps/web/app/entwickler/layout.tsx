import Link from "next/link";
import type { ReactNode } from "react";

import { LogoMarke } from "@/components/Logo";

export default function EntwicklerLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <header className="border-b border-linie bg-surface">
        <nav className="mx-auto flex min-h-[72px] max-w-5xl items-center gap-6 px-4 py-3" aria-label="Hauptnavigation">
          <Link href="/" className="flex items-center gap-2.5 text-ink">
            <LogoMarke />
            <span className="font-display text-2xl font-bold tracking-[-0.02em]">luibui</span>
          </Link>
          <Link href="/" className="text-sm hover:text-petrol">
            Übersicht
          </Link>
          <Link href="/konto" className="ml-auto text-sm hover:text-petrol">
            Konto
          </Link>
        </nav>
      </header>
      <main id="inhalt" className="mx-auto max-w-5xl px-4 py-8">
        {children}
      </main>
    </>
  );
}
