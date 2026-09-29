import { Zurueck } from "./Zurueck";

export const metadata = { title: "Zahlung – luibui" };

function lokal(pfad: string | undefined): string {
  return pfad && pfad.startsWith("/") && !pfad.startsWith("//") && !pfad.includes("\\") ? pfad : "/";
}

export default async function Seite({
  searchParams,
}: {
  searchParams: Promise<{ token?: string; weiter?: string; abgebrochen?: string }>;
}) {
  const p = await searchParams;
  return (
    <div className="flex max-w-2xl flex-col gap-4">
      <h1 className="font-display text-3xl font-bold">Guthaben aufladen</h1>
      <Zurueck orderId={p.token} weiter={lokal(p.weiter)} abgebrochen={p.abgebrochen === "1"} />
    </div>
  );
}
