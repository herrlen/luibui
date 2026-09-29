import { PasswortVergessen } from "./PasswortVergessen";

export const metadata = { title: "Passwort vergessen – luibui" };

export default function Page() {
  return (
    <div className="mx-auto max-w-md rounded-[14px] border border-linie bg-surface p-8">
      <h1 className="font-display text-3xl font-bold">Passwort vergessen</h1>
      <p className="mt-1 text-sm text-muted">Wir schicken dir einen Link, mit dem du ein neues Passwort festlegst.</p>
      <div className="mt-6">
        <PasswortVergessen />
      </div>
    </div>
  );
}
