import Link from "next/link";
import type { ReactNode } from "react";

export default function EntwicklerLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <header className="border-b border-linie bg-surface">
        <nav className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3" aria-label="Hauptnavigation">
          <Link href="/" className="font-display text-xl font-bold text-petrol">
            luibui
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
