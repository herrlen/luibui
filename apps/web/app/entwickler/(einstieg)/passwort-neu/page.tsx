import { PasswortNeu } from "./PasswortNeu";

export const metadata = { title: "Neues Passwort – luibui" };

export default async function Page({ searchParams }: { searchParams: Promise<{ token?: string }> }) {
  const { token } = await searchParams;
  return (
    <div className="mx-auto max-w-md rounded-[14px] border border-linie bg-surface p-8">
      <h1 className="font-display text-3xl font-bold">Neues Passwort</h1>
      <div className="mt-6">
        {token ? <PasswortNeu token={token} /> : <p>Der Link ist unvollständig. Bitte öffne ihn direkt aus der Mail.</p>}
      </div>
    </div>
  );
}
