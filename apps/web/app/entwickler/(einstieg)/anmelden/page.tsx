import { Anmelden } from "./Anmelden";

export const metadata = { title: "Anmelden – luibui" };

export default function Page() {
  return (
    <div className="mx-auto max-w-md rounded-[14px] border border-linie bg-surface p-8">
      <h1 className="font-display text-3xl font-bold">Anmelden</h1>
      <p className="mt-1 text-sm text-muted">Zu deinen Projekten und Prüfberichten.</p>
      <div className="mt-6">
        <Anmelden />
      </div>
    </div>
  );
}
