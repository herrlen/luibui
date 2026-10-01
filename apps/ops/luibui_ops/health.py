"""Health checks: api, web and the public site, every few minutes.

A target counts as down after two failed checks in a row, so a rollout (a few seconds) or one slow
answer does not wake anybody. One mail when it goes down, one when it is back.
"""

import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field

AUSFALL_NACH = 2
TIMEOUT = 10

Pruefer = Callable[[str], str | None]
"""Returns None when healthy, else a short reason."""


def pruefen(url: str) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": "luibui-ops"})  # noqa: S310 - http(s) only, checked in settings
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # noqa: S310
            if r.status != 200:
                return f"HTTP {r.status}"
            body = r.read(4096).decode(errors="replace")
    except urllib.error.HTTPError as exc:
        return f"HTTP {exc.code}"
    except (OSError, ValueError) as exc:
        return type(exc).__name__
    if '"status":"ok"' not in body.replace(" ", ""):
        return "Antwort ohne status ok"
    return None


@dataclass
class Waechter:
    urls: tuple[str, ...]
    fehler_in_folge: dict[str, int] = field(default_factory=dict)
    gemeldet: set[str] = field(default_factory=set)

    def runde(self, pruefer: Pruefer = pruefen) -> list[tuple[str, str]]:
        """One round; returns the alarms to send as (subject, text)."""
        alarme: list[tuple[str, str]] = []
        for url in self.urls:
            grund = pruefer(url)
            if grund is None:
                self.fehler_in_folge[url] = 0
                if url in self.gemeldet:
                    self.gemeldet.discard(url)
                    alarme.append((f"Wieder erreichbar: {url}", f"{url} antwortet wieder normal."))
                continue
            n = self.fehler_in_folge.get(url, 0) + 1
            self.fehler_in_folge[url] = n
            if n >= AUSFALL_NACH and url not in self.gemeldet:
                self.gemeldet.add(url)
                alarme.append(
                    (
                        f"Nicht erreichbar: {url}",
                        f"{url} hat {n}-mal hintereinander nicht richtig geantwortet ({grund}).\n"
                        "Container-Logs im mStudio ansehen; nach der Behebung kommt eine "
                        "Entwarnung.",
                    )
                )
        return alarme
