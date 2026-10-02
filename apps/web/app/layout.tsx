import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";
import "@fontsource/ibm-plex-sans/700.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "./globals.css";

import type { Metadata } from "next";
import type { ReactNode } from "react";

const BESCHREIBUNG =
  "Prüfstelle für KI-Skills, Plugins, Tools und MCP-Server. Bericht mit Ampeln für Sicherheit und DSGVO.";

export const metadata: Metadata = {
  metadataBase: new URL("https://luibui.com"),
  title: "luibui – Prüfstelle für KI-Skills und MCP-Server",
  description: BESCHREIBUNG,
  openGraph: {
    type: "website",
    locale: "de_DE",
    siteName: "luibui",
    title: "luibui – Prüfen, bevor man installiert",
    description: BESCHREIBUNG,
  },
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/favicon.ico", sizes: "any" },
    ],
    apple: "/apple-touch-icon.png",
  },
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
