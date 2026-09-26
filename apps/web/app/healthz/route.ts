import { healthBody } from "@/lib/health";

// Liveness of the web container. /api/* is reserved for the API proxy on app.luibui.com (S2-6).
export const dynamic = "force-dynamic";

export function GET() {
  return Response.json(healthBody());
}
