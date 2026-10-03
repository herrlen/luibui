"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Feld, Meldung } from "@/components/app/Formular";
import { senden } from "@/lib/client-api";

const KNOPF = "inline-flex h-12 w-fit items-center rounded-[10px] px-[22px] text-[15px] font-semibold disabled:opacity-60";
const PRIMAER = `${KNOPF} bg-petrol text-white hover:bg-petrol-dunkel`;
const CODE = { inputMode: "numeric", autoComplete: "one-time-code", pattern: "[0-9 ]{6,8}" } as const;

/** QR code from the API as rows of "1" and "0", drawn as rectangles (no image, no library). */
export function QrCode({ zeilen }: { zeilen: string[] }) {
  const n = zeilen.length;
  const rand = 4;
  return (
    <svg
      viewBox={`0 0 ${n + 2 * rand} ${n + 2 * rand}`}
      width={200}
      height={200}
      role="img"
      aria-label="QR-Code für die Authenticator-App"
      shapeRendering="crispEdges"
      className="rounded-lg"
    >
      <rect width="100%" height="100%" fill="#fff" />
      {zeilen.flatMap((zeile, y) =>
        [...zeile].map((m, x) =>
          m === "1" ? <rect key={`${x}-${y}`} x={x + rand} y={y + rand} width={1} height={1} fill="#000" /> : null,
        ),
      )}
    </svg>
  );
}

type Einrichtung = { secret: string; uri: string; qr: string[] };

/** Two-factor login: set up with QR code or key, confirm with a first code; switch off with password and code. */
export function ZweiFaktor({ aktiv }: { aktiv: boolean }) {
  const router = useRouter();
  const [einrichtung, setEinrichtung] = useState<Einrichtung | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);

  if (aktiv) {
    return (
      <form
        method="post"
        className="flex flex-col gap-3"
        onSubmit={async (e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          setLaeuft(true);
          const r = await senden("/auth/totp/deaktivieren", "POST", {
            passwort: f.get("passwort"),
            code: String(f.get("code") ?? "").replace(/\s/g, ""),
          });
          setLaeuft(false);
          if (r.ok) router.refresh();
          else setFehler(r.fehler.text);
        }}
      >
        <p className="text-sm text-muted">
          Die Anmeldung braucht neben dem Passwort einen Code aus deiner Authenticator-App.
        </p>
        <Feld label="Passwort" name="passwort" type="password" autoComplete="current-password" required />
        <Feld label="Code aus der Authenticator-App" name="code" {...CODE} required />
        <Meldung text={fehler} />
        <button type="submit" disabled={laeuft} className={`${KNOPF} border border-rot text-rot`}>
          Zwei-Faktor-Anmeldung ausschalten
        </button>
      </form>
    );
  }

  if (!einrichtung) {
    return (
      <div className="flex flex-col gap-3">
        <p className="text-sm text-muted">
          Schützt dein Konto, auch wenn jemand dein Passwort kennt. Du brauchst eine Authenticator-App, etwa die deines
          Passwortmanagers.
        </p>
        <Meldung text={fehler} />
        <button
          type="button"
          disabled={laeuft}
          className={PRIMAER}
          onClick={async () => {
            setLaeuft(true);
            setFehler(null);
            const r = await senden<Einrichtung>("/auth/totp/einrichten", "POST");
            setLaeuft(false);
            if (r.ok) setEinrichtung(r.data);
            else setFehler(r.fehler.text);
          }}
        >
          Zwei-Faktor-Anmeldung einrichten
        </button>
      </div>
    );
  }

  return (
    <form
      method="post"
      className="flex flex-col gap-4"
      onSubmit={async (e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        setLaeuft(true);
        const r = await senden("/auth/totp/bestaetigen", "POST", {
          code: String(f.get("code") ?? "").replace(/\s/g, ""),
        });
        setLaeuft(false);
        if (r.ok) {
          setEinrichtung(null);
          router.refresh();
        } else setFehler(r.fehler.text);
      }}
    >
      <ol className="flex list-decimal flex-col gap-3 pl-5 text-sm">
        <li>
          QR-Code mit der Authenticator-App scannen.
          <div className="mt-2">
            <QrCode zeilen={einrichtung.qr} />
          </div>
          <p className="mt-2 text-muted">Oder den Schlüssel von Hand eingeben:</p>
          <code className="mt-1 block break-all font-mono text-sm">{einrichtung.secret.replace(/(.{4})/g, "$1 ").trim()}</code>
        </li>
        <li>Den sechsstelligen Code aus der App eintragen.</li>
      </ol>
      <Feld label="Code aus der Authenticator-App" name="code" {...CODE} required />
      <Meldung text={fehler} />
      <div className="flex flex-wrap gap-3">
        <button type="submit" disabled={laeuft} className={PRIMAER}>
          Bestätigen und einschalten
        </button>
        <button
          type="button"
          className={`${KNOPF} border border-linie-stark`}
          onClick={() => {
            setEinrichtung(null);
            setFehler(null);
          }}
        >
          Abbrechen
        </button>
      </div>
    </form>
  );
}

/** New password with the current one (and code). Other sessions end, this one stays. */
export function PasswortAendern({ totp }: { totp: boolean }) {
  const [fehler, setFehler] = useState<string | null>(null);
  const [erledigt, setErledigt] = useState(false);
  const [laeuft, setLaeuft] = useState(false);
  return (
    <form
      method="post"
      className="flex flex-col gap-3"
      onSubmit={async (e) => {
        e.preventDefault();
        const form = e.currentTarget;
        const f = new FormData(form);
        setFehler(null);
        setErledigt(false);
        if (f.get("neu") !== f.get("wiederholung")) {
          setFehler("Die beiden neuen Passwörter stimmen nicht überein.");
          return;
        }
        setLaeuft(true);
        const r = await senden("/konto/passwort", "POST", {
          passwort: f.get("passwort"),
          neu: f.get("neu"),
          code: String(f.get("code") ?? "").replace(/\s/g, "") || undefined,
        });
        setLaeuft(false);
        if (r.ok) {
          setErledigt(true);
          form.reset();
        } else setFehler(r.fehler.text ?? "Das Passwort wurde nicht geändert.");
      }}
    >
      <Feld label="Aktuelles Passwort" name="passwort" type="password" autoComplete="current-password" required />
      <Feld
        label="Neues Passwort (mindestens 12 Zeichen)"
        name="neu"
        type="password"
        autoComplete="new-password"
        minLength={12}
        maxLength={256}
        required
      />
      <Feld
        label="Neues Passwort wiederholen"
        name="wiederholung"
        type="password"
        autoComplete="new-password"
        minLength={12}
        maxLength={256}
        required
      />
      {totp ? <Feld label="Code aus der Authenticator-App" name="code" {...CODE} required /> : null}
      <Meldung text={fehler} />
      {erledigt ? (
        <p role="status" className="text-sm text-gruen">
          Passwort geändert. Alle anderen Sitzungen sind abgemeldet.
        </p>
      ) : null}
      <button type="submit" disabled={laeuft} className={PRIMAER}>
        Passwort ändern
      </button>
    </form>
  );
}

/** New address: a link goes to it; the account changes only after the click. */
export function EmailAendern({ totp }: { totp: boolean }) {
  const [fehler, setFehler] = useState<string | null>(null);
  const [hinweis, setHinweis] = useState<string | null>(null);
  const [laeuft, setLaeuft] = useState(false);
  return (
    <form
      method="post"
      className="flex flex-col gap-3"
      onSubmit={async (e) => {
        e.preventDefault();
        const form = e.currentTarget;
        const f = new FormData(form);
        setFehler(null);
        setHinweis(null);
        setLaeuft(true);
        const r = await senden<{ hinweis: string }>("/konto/email", "POST", {
          neu: f.get("neu"),
          passwort: f.get("passwort"),
          code: String(f.get("code") ?? "").replace(/\s/g, "") || undefined,
        });
        setLaeuft(false);
        if (r.ok) {
          setHinweis(r.data.hinweis);
          form.reset();
        } else setFehler(r.status === 422 ? "Keine gültige E-Mail-Adresse." : r.fehler.text);
      }}
    >
      <Feld label="Neue E-Mail-Adresse" name="neu" type="email" autoComplete="email" maxLength={320} required />
      <Feld label="Passwort" name="passwort" type="password" autoComplete="current-password" required />
      {totp ? <Feld label="Code aus der Authenticator-App" name="code" {...CODE} required /> : null}
      <Meldung text={fehler} />
      {hinweis ? (
        <p role="status" className="text-sm text-gruen">
          {hinweis}
        </p>
      ) : null}
      <button type="submit" disabled={laeuft} className={PRIMAER}>
        Link an die neue Adresse schicken
      </button>
    </form>
  );
}
