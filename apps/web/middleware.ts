import { NextResponse, type NextRequest } from "next/server";

// One Next.js app, two hosts (CLAUDE.md, Konzept §3): app.luibui.com is the developer area, every
// other host (luibui.com) the public site. Internally the pages live under /entwickler and
// /oeffentlich; those prefixes are never reachable directly.
const BEREICHE = ["/entwickler", "/oeffentlich"];

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (BEREICHE.some((b) => pathname === b || pathname.startsWith(`${b}/`))) {
    return new NextResponse("Nicht gefunden", { status: 404 });
  }
  const host = (req.headers.get("host") ?? "").toLowerCase();
  const bereich = host.startsWith("app.") ? "/entwickler" : "/oeffentlich";
  const url = req.nextUrl.clone();
  url.pathname = bereich + (pathname === "/" ? "" : pathname);
  return NextResponse.rewrite(url);
}

export const config = {
  // Files from public/ are served as they are, on both hosts.
  matcher: ["/((?!_next/|api/|healthz|favicon\\.(?:ico|svg)|apple-touch-icon\\.png|beispielbericht\\.pdf|robots\\.txt).*)"],
};
