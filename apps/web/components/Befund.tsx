import { SCHWERE_TEXT } from "@/lib/format";
import type { Befund as BefundT } from "@/lib/types";

import { Kopieren } from "./Kopieren";

// Everything from the package (title, path, evidence) is rendered as plain text; React escapes it.
// Never dangerouslySetInnerHTML, never Markdown (CLAUDE.md rule 6).
const SCHWERE_STIL: Record<string, string> = {
  K: "bg-gesperrt text-white",
  H: "bg-rot-bg text-rot",
  M: "bg-gelb-bg text-gelb",
  N: "bg-linie text-ink-2",
  I: "bg-linie text-ink-2",
};

export function Befund({ b }: { b: BefundT }) {
  const ort = b.datei ? `${b.datei}${b.zeile ? `:${b.zeile}` : ""}` : "ganzes Paket";
  return (
    <article className="rounded-[14px] border border-linie bg-surface p-5">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${SCHWERE_STIL[b.schwere]}`}>
          {SCHWERE_TEXT[b.schwere]}
        </span>
        <h3 className="text-base font-semibold">{b.titel}</h3>
      </div>
      <p className="mt-1 font-mono text-xs text-muted">
        {b.rule_id} · {ort} · {b.achse === "dsgvo" ? "DSGVO" : "Sicherheit"}
      </p>
      <p className="mt-3 text-sm text-ink-2">{b.erklaerung}</p>
      {b.beleg ? (
        <pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-all rounded-lg bg-grund p-3 font-mono text-xs">
          {b.beleg}
        </pre>
      ) : null}
      <p className="mt-3 text-sm">
        <span className="font-semibold">So behebst du es: </span>
        {b.fix}
      </p>
      {b.fix_prompt ? (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <span className="text-xs text-muted">Prompt für Claude Code oder andere Coding-Agents:</span>
          <Kopieren text={b.fix_prompt} label="Fix-Prompt kopieren" />
        </div>
      ) : null}
    </article>
  );
}
