import { schnellscanDownload } from "@/lib/download";

export const dynamic = "force-dynamic";

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  return schnellscanDownload((await params).id, "csv");
}
