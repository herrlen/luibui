import { redirect } from "next/navigation";

import { apiGet } from "@/lib/server-api";
import type { Ich } from "@/lib/types";

import { Abmelden } from "./Abmelden";
import { type TokenInfo, Tokens } from "./Tokens";

export const metadata = { title: "Konto – luibui" };
export const dynamic = "force-dynamic";

export default async function Konto() {
  const ich = await apiGet<Ich>("/api/v1/auth/ich");
  if (!ich.ok) redirect("/anmelden");
  const tokens = await apiGet<TokenInfo[]>("/api/v1/tokens");
  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-display text-3xl font-bold">Konto</h1>
      <section className="rounded-[14px] border border-linie bg-surface p-6 text-sm">
        <p>
          <span className="font-semibold">E-Mail:</span> {ich.data.email}
        </p>
        <p className="mt-1">
          <span className="font-semibold">Zwei-Faktor-Anmeldung:</span> {ich.data.totp_aktiv ? "aktiv" : "nicht aktiv"}
        </p>
      </section>
      <Tokens tokens={tokens.ok ? tokens.data : []} />
      <div>
        <Abmelden />
      </div>
    </div>
  );
}
