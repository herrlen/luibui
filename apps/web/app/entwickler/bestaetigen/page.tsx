import { Bestaetigen } from "./Bestaetigen";

export const metadata = { title: "E-Mail bestätigen – luibui" };

export default async function Seite({ searchParams }: { searchParams: Promise<{ token?: string }> }) {
  const { token } = await searchParams;
  return (
    <div className="flex max-w-2xl flex-col gap-4">
      <h1 className="font-display text-3xl font-bold">E-Mail bestätigen</h1>
      {token ? <Bestaetigen token={token} /> : <p>Der Link ist unvollständig. Bitte öffne ihn direkt aus der Mail.</p>}
    </div>
  );
}
