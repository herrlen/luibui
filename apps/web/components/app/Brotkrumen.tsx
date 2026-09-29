import Link from "next/link";

export type Krume = { text: string; href?: string };

/** Where am I: every level links back, the last one is the current page. */
export function Brotkrumen({ pfad }: { pfad: Krume[] }) {
  return (
    <nav aria-label="Brotkrumen" className="text-sm print:hidden">
      <ol className="flex flex-wrap items-center gap-x-2 gap-y-1 text-muted">
        {pfad.map((k, i) => {
          const letzte = i === pfad.length - 1;
          return (
            <li key={`${i}-${k.text}`} className="flex min-w-0 items-center gap-2">
              {i > 0 ? (
                <span aria-hidden="true" className="text-linie-stark">
                  /
                </span>
              ) : null}
              {k.href && !letzte ? (
                <Link href={k.href} className="break-all hover:text-petrol">
                  {k.text}
                </Link>
              ) : (
                <span aria-current={letzte ? "page" : undefined} className={letzte ? "break-all font-medium text-ink" : ""}>
                  {k.text}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
