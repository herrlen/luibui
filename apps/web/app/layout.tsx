import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "luibui – Prüfstelle für KI-Skills und MCP-Server",
  description:
    "Offene, nicht-kommerzielle Prüfstelle für KI-Skills, Plugins, Tools und MCP-Server. Bericht mit Ampeln für Sicherheit und DSGVO.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="de">
      <body>{children}</body>
    </html>
  );
}
