# ATR-Regeln (übernommen)

Quelle: https://github.com/Agent-Threat-Rule/agent-threat-rules
Stand: Tag `v4.0.0`, Commit `464548b43dc5f99c446a6d092d4fc92940ce170d`. Lizenz: MIT (siehe `LICENSE`).
Die Namen „ATR“ und „Agent Threat Rules“ sind Marken der Urheber und nicht Teil der
MIT-Lizenz; luibui nennt die Regeln nur sachlich mit ihrer ID.

Erzeugt mit `scripts/vendor_atr.py`. Übernommen werden nur Regeln mit Reifegrad
`stable` oder `experimental`, reinen Regex-Bedingungen auf Textfeldern und bestandenen
eigenen Testfällen unter unserer Regex-Engine.

- übernommen: 155
- nicht geeignet (Reifegrad, Status, Felder, Operatoren): 615
- eigene Testfälle nicht bestanden: 8
- Fehlalarm im gutartigen Vergleichsbestand: 7

## Gutartiger Vergleichsbestand

- `anthropics_skills` Commit `33375500bcea`
- `modelcontextprotocol_servers` Commit `f46d9578190b`
- `modelcontextprotocol_python-sdk` Commit `f1b658908853`
- `corpus/benign/` (eigener Korpus, Stand dieses Repositorys)
- zusammen 1009 Textdateien (Markdown, Text, YAML, JSON, TOML)

## Nicht übernommen wegen Testfällen

- ATR-2026-01774: verpasst: 
- ATR-2026-01601: verpasst: 
- ATR-2026-01602: verpasst: 
- ATR-2026-01610: verpasst: 
- ATR-2026-01613: verpasst: 
- ATR-2026-01614: verpasst: 
- ATR-2026-02102: verpasst: {'tool_name': 'process_task', 'tool_args': 'report.txt<img s
- ATR-2026-02260: verpasst: 

## Nicht übernommen wegen Fehlalarmen

- ATR-2026-00579: schlägt an in `anthropics_skills/skills/claude-api/shared/tool-use-concepts.md`
- ATR-2026-01013: schlägt an in `modelcontextprotocol_python-sdk/i18n/tr/pages/client/identity-assertion.md`
- ATR-2026-01901: schlägt an in `modelcontextprotocol_python-sdk/i18n/ru/instructions.md`
- ATR-2026-00061: schlägt an in `anthropics_skills/THIRD_PARTY_NOTICES.md`
- ATR-2026-00576: schlägt an in `anthropics_skills/skills/claude-api/curl/managed-agents.md`
- ATR-2026-00443: schlägt an in `corpus/benign/seo-skill/SKILL.md` („Underscores join words“, nachgetragen 2026-09-28)
- ATR-2026-00030: schlägt an in `corpus/benign/beratungs-skill/SKILL.md` („acting on behalf of an organization“, fünfmal in claude-skills-main, nachgetragen 2026-09-29)
