import { beispielbericht } from "@/content/beispiel";
import { berichtAlsCsv } from "@/lib/csv";

// Built once at build time from the static fixture; no scan, no API call.
export const dynamic = "force-static";

export function GET() {
  return new Response(berichtAlsCsv(beispielbericht(), { showDsgvo: false }), {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": 'attachment; filename="luibui-beispielbericht.csv"',
      "X-Content-Type-Options": "nosniff",
    },
  });
}
