"use client";

import { useId, useState } from "react";

import { SCHWERE_TEXT } from "@/lib/format";
import type { Befund, BefundStatus } from "@/lib/types";

import { BefundStatusSteuerung, StatusMarke } from "../app/BefundStatus";
import { Kopieren } from "../Kopieren";

// Everything from the package (title, path, evidence) is rendered as plain text; React escapes it.
// Never dangerouslySetInnerHTML, never Markdown (CLAUDE.md rule 6).
export const SCHWERE_STIL: Record<string, string> = {
  K: "bg-gesperrt text-white",
  H: "bg-rot-bg text-rot",
  M: "bg-gelb-bg text-gelb",
  N: "bg-tag text-ink-2",
  I: "bg-tag text-ink-2",
};

export function ort(b: Befund): string {
  return b.datei ? `${b.datei}${b.zeile ? `:${b.zeile}` : ""}` : "ganzes Paket";
}

/** Engine texts mark names with backticks. Shown in code type, still as plain text. */
export function MitCode({ text }: { text: string }) {
  return (
    <>
      {text.split(/`([^`\n]+)`/).map((teil, i) =>
        i % 2 ? (
          <code key={i} className="rounded bg-grund px-1 font-mono text-[0.9em]">
            {teil}
          </code>
        ) : (
          teil
        ),
      )}
    </>
  );
}

/** ``scanId``: the owner's check in a project, where the status can be changed (S3-7). */
export function BefundKarte({
  b,
  offen = false,
  status,
  scanId,
}: {
  b: Befund;
  offen?: boolean;
  status?: BefundStatus;
  scanId?: string;
}) {
  const [auf, setAuf] = useState(offen);
  const id = useId();
  return (
    <article className="rounded-[14px] border border-linie bg-surface">
      <h3 className="m-0">
        <button
          type="button"
          aria-expanded={auf}
          aria-controls={id}
          onClick={() => setAuf(!auf)}
          className="flex w-full flex-wrap items-center gap-x-3 gap-y-1.5 rounded-[14px] p-5 text-left"
        >
          <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${SCHWERE_STIL[b.schwere]}`}>
            {SCHWERE_TEXT[b.schwere]}
          </span>
          <StatusMarke status={status} />
          <span className="min-w-0 flex-1 text-base font-semibold">{b.titel}</span>
          <span aria-hidden="true" className="text-lg leading-none text-muted sm:order-last">
            {auf ? "−" : "+"}
          </span>
          <span className="w-full break-all font-mono text-xs text-muted sm:w-auto">{ort(b)}</span>
        </button>
      </h3>
      <div id={id} hidden={!auf} className="border-t border-linie px-5 pb-5 pt-4">
        <p className="font-mono text-xs text-muted">
          {b.rule_id} · {b.achse === "dsgvo" ? "DSGVO" : "Sicherheit"}
          {b.hochgestuft_von ? ` · hochgestuft von ${SCHWERE_TEXT[b.hochgestuft_von]}` : ""}
        </p>
        <p className="mt-3 text-[15px] leading-[1.6] text-ink-2">
          <MitCode text={b.erklaerung} />
        </p>
        {b.beleg ? (
          <figure className="mt-3">
            <figcaption className="text-xs text-muted">Beleg aus {ort(b)}</figcaption>
            <pre className="mt-1 overflow-x-auto whitespace-pre rounded-lg bg-grund p-3 font-mono text-xs">
              {b.beleg}
            </pre>
          </figure>
        ) : null}
        <p className="mt-3 text-sm">
          <span className="font-semibold">So behebst du es: </span>
          <MitCode text={b.fix} />
        </p>
        {b.fix_prompt ? (
          <div className="mt-3 flex flex-col gap-2">
            <span className="text-xs text-muted">Prompt für Claude Code oder andere Coding-Agents:</span>
            <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg bg-grund p-3 font-mono text-xs">
              {b.fix_prompt}
            </pre>
            <div>
              <Kopieren text={b.fix_prompt} label="Fix-Prompt kopieren" />
            </div>
          </div>
        ) : null}
        {scanId && b.fingerprint ? (
          <BefundStatusSteuerung scanId={scanId} fingerprint={b.fingerprint} status={status} />
        ) : null}
      </div>
    </article>
  );
}
