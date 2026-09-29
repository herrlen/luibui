import { berichtDownload } from "@/lib/download";

export const dynamic = "force-dynamic";

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  return berichtDownload((await params).id, "json");
}
