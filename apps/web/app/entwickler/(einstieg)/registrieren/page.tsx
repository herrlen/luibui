import { Registrieren } from "./Registrieren";

export const metadata = { title: "Registrieren – luibui" };

export default function Page() {
  return (
    <div className="mx-auto max-w-md rounded-[14px] border border-linie bg-surface p-8">
      <h1 className="font-display text-3xl font-bold">Kostenlos registrieren</h1>
      <p className="mt-1 text-sm text-muted">
        Eigener, privater Bereich für deine Pakete. Dateien liegen verschlüsselt in Deutschland.
      </p>
      <div className="mt-6">
        <Registrieren />
      </div>
    </div>
  );
}
