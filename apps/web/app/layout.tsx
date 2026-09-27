import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "@fontsource-variable/bricolage-grotesque/opsz.css";
import "./globals.css";

import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "luibui – Prüfstelle für KI-Skills und MCP-Server",
  description:
    "Prüfstelle für KI-Skills, Plugins, Tools und MCP-Server. Bericht mit Ampeln für Sicherheit und DSGVO.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="de">
      <body className="min-h-screen antialiased">
        <a
          href="#inhalt"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:bg-surface focus:p-2"
        >
          Zum Inhalt
        </a>
        {children}
      </body>
    </html>
  );
}
