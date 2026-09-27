# Gutartiger Korpus

Realistische, harmlose Pakete. `luibui scan corpus/benign/<paket>` darf **keine K- oder H-Befunde**
liefern (Definition of Done Sprint 1, Test `packages/engine/tests/test_corpus.py`). Jedes Paket prüft
eine typische Fehlalarm-Quelle mit: Emojis, Umlaute, arabische und persische Schrift (ZWNJ),
Shell-Befehle in Code-Blöcken, zitierte Angriffsformulierungen, Plugins ohne Hooks, feste Versionen
ohne bekannte Lücken (Stand 2026-09-27; eine neue Lücke in `mcp`, `httpx`, `pydantic`, `zod` oder
`@modelcontextprotocol/sdk` macht diese Pakete berechtigt rot und muss hier nachgezogen werden).

Endpunkte liegen unter `.example`, nichts davon ist erreichbar.
