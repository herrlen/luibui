import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Kopieren } from "@/components/Kopieren";
import { ReportView } from "@/components/report/ReportView";
import { datumZeit } from "@/lib/format";
import { rechte } from "@/lib/rechte";
import { apiGet } from "@/lib/server-api";
import { teile, zeilen } from "@/lib/sichtbar";
import type { PaketDetail } from "@/lib/types";

// Public package page (S4-3). Everything from the package (name, description, README, findings)
// is shown as text; nothing is rendered as HTML or Markdown (CLAUDE.md rule 6).
export const dynamic = "force-dynamic";

type Params = { params: Promise<{ namespace: string; name: string }>; searchParams: Promise<{ version?: string }> };

async function laden({ params, searchParams }: Params) {
  const { namespace, name } = await params;
  const { version } = await searchParams;
  const pfad = `${encodeURIComponent(namespace)}/${encodeURIComponent(name)}/${encodeURIComponent(version ?? "neueste")}`;
  return apiGet<PaketDetail>(`/api/v1/register/pakete/${pfad}`, false);
}

export async function generateMetadata(p: Params): Promise<Metadata> {
  const r = await laden(p);
  if (!r.ok) return { title: "Paket – luibui" };
  const beschreibung = typeof r.data.manifest.beschreibung === "string" ? r.data.manifest.beschreibung : undefined;
  return {
    title: `${r.data.paket} – luibui`,
    description: beschreibung?.slice(0, 200),
    alternates: { canonical: `/pakete/${r.data.paket}` },
  };
}

export default async function PaketSeite(p: Params) {
  const r = await laden(p);
  if (!r.ok) notFound();
  const d = r.data;
  const m = d.manifest;
  const text = (k: string) => (typeof m[k] === "string" ? (m[k] as string) : null);
  const archiv = `/api/v1/register/pakete/${d.paket}/${encodeURIComponent(d.version)}/archiv.zip`;
  return (
    <article className="flex max-w-5xl flex-col gap-6 pt-10">
      <header className="flex flex-col gap-2">
        <p className="text-sm text-muted">
          <Link href="/pakete" className="hover:text-petrol">
            Register
          </Link>{" "}
          / {d.paket.split("/")[0]}
        </p>
        <h1 className="break-all font-mono text-3xl font-bold">{d.paket}</h1>
        {text("beschreibung") ? <p className="max-w-3xl text-lg text-ink-2">{text("beschreibung")}</p> : null}
        <p className="text-sm text-muted">
          Version <span className="font-mono">{d.version}</span> · veröffentlicht am {datumZeit(d.veroeffentlicht_am)}
          {text("lizenz") ? <> · Lizenz {text("lizenz")}</> : null}
          {text("typ") ? <> · {text("typ")}</> : null}
        </p>
        {d.zurueckgezogen ? (
          <p role="alert" className="rounded-lg bg-rot-bg px-4 py-3 text-rot">
            Diese Version wurde vom Autor zurückgezogen und wird nicht mehr zur Installation angeboten.
          </p>
        ) : null}
      </header>

      {d.vorversion ? (
        <section
          aria-labelledby="neu"
          className={`flex flex-col gap-2 rounded-[14px] border p-5 ${d.aenderungen.length ? "border-gelb bg-gelb-bg" : "border-linie bg-surface"}`}
        >
          <h2 id="neu" className="font-display text-lg font-bold">
            Neu gegenüber {d.vorversion}
          </h2>
          {d.aenderungen.length ? (
            <ul className="list-disc pl-5 text-sm">
              {d.aenderungen.map((a, i) => (
                <li key={i}>{a.text}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-ink-2">Keine neuen Rechte, Endpunkte oder Datenkategorien laut luibui.json.</p>
          )}
        </section>
      ) : null}

      <section aria-labelledby="rechte" className="flex flex-col gap-3">
        <h2 id="rechte" className="font-display text-xl font-bold">
          Rechte laut luibui.json
        </h2>
        <ul className="flex flex-wrap gap-2">
          {rechte(m).map((x) => (
            <li
              key={x.name}
              className={`rounded-full border px-3 py-1.5 text-sm ${x.an ? "border-gelb bg-gelb-bg text-gelb" : "border-linie text-muted"}`}
            >
              <span className="font-semibold">{x.name}</span>: {x.an ? "ja" : "nein"}
              {x.detail ? <span className="text-xs"> ({x.detail})</span> : null}
            </li>
          ))}
        </ul>
        <p className="text-sm text-muted">
          Das sind die Angaben des Autors. Ob der Code dazu passt, prüft luibui; Abweichungen stehen unten als Befunde.
        </p>
      </section>

      {d.bericht ? (
        <section aria-labelledby="pruefung" className="flex flex-col gap-3">
          <h2 id="pruefung" className="font-display text-xl font-bold">
            Prüfbericht dieser Version
          </h2>
          <ReportView bericht={d.bericht} />
        </section>
      ) : null}

      {d.readme !== null ? (
        <section aria-labelledby="readme" className="flex flex-col gap-3">
          <h2 id="readme" className="font-display text-xl font-bold">
            {d.readme_datei}
          </h2>
          <pre className="max-h-[600px] overflow-auto whitespace-pre-wrap break-words rounded-[14px] border border-linie bg-surface p-5 font-mono text-[13px] leading-[1.55]">
            {zeilen(d.readme).map((z, i) => (
              <span key={i}>
                {teile(z).map((t, j) =>
                  t.unsichtbar ? (
                    <span key={j} className="rounded bg-gesperrt px-1 text-[11px] text-white">
                      {t.text}
                    </span>
                  ) : (
                    t.text
                  ),
                )}
                {"\n"}
              </span>
            ))}
          </pre>
          <p className="text-xs text-muted">Als Text angezeigt, nicht formatiert. Unsichtbare Zeichen erscheinen als &lt;U+…&gt;.</p>
        </section>
      ) : null}

      <section aria-labelledby="herunterladen" className="flex flex-col gap-3 rounded-[14px] border border-linie bg-surface p-6">
        <h2 id="herunterladen" className="font-display text-xl font-bold">
          Herunterladen und prüfen
        </h2>
        {d.zurueckgezogen ? null : (
          <a
            href={archiv}
            download
            className="inline-flex h-11 w-fit items-center rounded-[10px] bg-petrol px-5 text-[15px] font-semibold text-white hover:bg-petrol-dunkel"
          >
            Archiv herunterladen ({(d.archiv_bytes / 1024).toLocaleString("de-DE", { maximumFractionDigits: 1 })} KB)
          </a>
        )}
        <dl className="grid gap-2 text-sm sm:grid-cols-[10rem_1fr]">
          <dt className="text-muted">SHA-256</dt>
          <dd className="break-all font-mono text-xs">{d.archiv_sha256}</dd>
          <dt className="text-muted">Signatur (Ed25519)</dt>
          <dd className="break-all font-mono text-xs">{d.signatur}</dd>
        </dl>
        <p className="text-sm text-muted">
          luibui signiert zu jeder Version, was geprüft wurde: Archiv, Bericht, Ampel und Note. Den öffentlichen Schlüssel gibt es
          unter <a href="/api/v1/register/schluessel" className="text-petrol underline">/api/v1/register/schluessel</a>.
        </p>
      </section>

      <section aria-labelledby="badge" className="flex flex-col gap-3">
        <h2 id="badge" className="font-display text-xl font-bold">
          Badge für die README
        </h2>
        {/* eslint-disable-next-line @next/next/no-img-element -- our own SVG from the same host */}
        <img src={`/badge/${d.paket}.svg`} alt={`luibui-Prüfung von ${d.paket}`} height={20} className="h-5 w-fit" />
        <pre className="overflow-x-auto rounded-[14px] border border-linie bg-surface p-4 font-mono text-xs">
          {`[![luibui](https://luibui.com/badge/${d.paket}.svg)](https://luibui.com/pakete/${d.paket})`}
        </pre>
        <div>
          <Kopieren
            text={`[![luibui](https://luibui.com/badge/${d.paket}.svg)](https://luibui.com/pakete/${d.paket})`}
            label="Markdown kopieren"
          />
        </div>
      </section>

      {d.versionen.length > 1 ? (
        <section aria-labelledby="versionen" className="flex flex-col gap-3">
          <h2 id="versionen" className="font-display text-xl font-bold">
            Versionen
          </h2>
          <ul className="flex flex-col divide-y divide-linie rounded-[14px] border border-linie bg-surface text-sm">
            {d.versionen.map((v) => (
              <li key={v.version} className="flex flex-wrap items-center gap-x-4 px-5 py-2.5">
                <Link href={`/pakete/${d.paket}?version=${encodeURIComponent(v.version)}`} className="font-mono font-semibold text-petrol underline">
                  {v.version}
                </Link>
                <span className="text-muted">{datumZeit(v.veroeffentlicht_am)}</span>
                {v.zurueckgezogen ? <span className="text-rot">zurückgezogen</span> : null}
                {v.version === d.version ? <span className="ml-auto text-muted">angezeigt</span> : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </article>
  );
}
