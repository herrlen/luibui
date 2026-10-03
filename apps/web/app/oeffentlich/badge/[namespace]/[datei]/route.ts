import { badgeSvg } from "@/lib/badge";
import { apiGet } from "@/lib/server-api";

// luibui.com/badge/<namespace>/<name>.svg (S5-4): light and grade of the newest version that is
// not withdrawn. Cached for an hour; the nightly re-check does not change it (that waits for the
// disclosure policy).
export async function GET(_req: Request, { params }: { params: Promise<{ namespace: string; datei: string }> }) {
  const { namespace, datei } = await params;
  const name = datei.endsWith(".svg") ? datei.slice(0, -4) : "";
  let ampel: string | null = null;
  let note: number | null = null;
  if (name && /^[a-z0-9-]{1,50}$/.test(name) && /^[a-z0-9-]{1,39}$/.test(namespace)) {
    const r = await apiGet<{ bericht: { ampeln?: { gesamt?: string }; note?: number } | null; zurueckgezogen: boolean }>(
      `/api/v1/register/pakete/${namespace}/${name}/neueste`,
      false,
    );
    if (r.ok && !r.data.zurueckgezogen && r.data.bericht) {
      ampel = r.data.bericht.ampeln?.gesamt ?? null;
      note = typeof r.data.bericht.note === "number" ? r.data.bericht.note : null;
    }
  }
  return new Response(badgeSvg(ampel, note), {
    headers: {
      "Content-Type": "image/svg+xml; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
      "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
