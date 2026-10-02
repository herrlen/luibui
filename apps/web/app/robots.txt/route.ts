import { headers } from "next/headers";

import { robotsTxt } from "@/lib/seo";

// Not rewritten by the middleware: one handler for both hosts, decided by the Host header.
export async function GET() {
  const h = await headers();
  const text = robotsTxt(h.get("host") ?? "luibui.com", h.get("x-forwarded-proto"));
  return new Response(text, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
}
