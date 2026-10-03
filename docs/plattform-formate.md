# Erweiterungsformate der Zielplattformen (Recherche für S5-1)

Stand: 2026-10-03. Die Quellen wurden an diesem Tag abgerufen; die meisten Doku-Seiten tragen
kein Datum („o. D.“). Nicht Verifiziertes ist ausdrücklich markiert. Vor der Umsetzung eines
Adapters die jeweilige Quelle erneut prüfen.

**Kernaussage:** Alle vier Plattformen kennen inzwischen Skills im Agent-Skills-Format
(`SKILL.md` mit YAML-Frontmatter `name`, `description`). Ein luibui-Paket vom Typ `skill` lässt
sich überall fast unverändert installieren; es unterscheidet sich nur das Ziel (Ordner auf der
Platte oder Upload in der Weboberfläche).

## ChatGPT / OpenAI

- **Arten:** Skills (Agent Skills, seit Juli 2026 allgemein für Business/Enterprise/Edu,
  laut Drittquelle auch Plus/Pro – *nicht verifiziert*); Plugins (Bündel aus Skills, MCP, Apps);
  Apps/Custom Connectors (Apps SDK = MCP, Developer Mode); Custom GPTs mit Actions (veraltet).
- **Formate:** Skill = Ordner mit `SKILL.md`, optional `scripts/`, `references/`, `assets/`,
  `agents/openai.yaml`. Plugin = `plugin.json` (`name`, `version`, `description`, `author`,
  `license`, `extensions["com.openai"]`) mit `skills/`, `mcp.json`, `assets/`.
- **Lokal:** ChatGPT Web nur Upload einer `.zip` von Hand. Codex: `~/.agents/skills/<name>/`
  (Projekt `.agents/skills/`). Desktop-App liest `~/.agents/plugins/marketplace.json`.
  MCP nur als entfernter HTTPS-Server, kein stdio/localhost.
- **Sicherheit:** `scripts/` laufen bei Codex lokal beim Nutzer.
- Quellen: developers.openai.com/plugins/build/plugins.md, …/skills.md (o. D.);
  letsdatascience.com „OpenAI Adds Skills Support“ (Juli 2026).

## Google Gemini

- **Arten:** Gemini-App-Skills (Gems werden ab 17.11.2026 zu Skills migriert; Workspace ab
  März 2027); Gemini Enterprise Skills; Gemini CLI/Antigravity: Agent Skills und Extensions.
- **Formate:** App-Skill = `SKILL.md` im Wurzelverzeichnis (Name klein mit Bindestrichen),
  Upload als Datei oder `.zip` bis 100 MB, nur Textdateien. CLI-Extension =
  `gemini-extension.json` (`name`, `version`, `description`; optional `mcpServers`,
  `contextFileName`, `excludeTools`, `settings[].envVar`, …) mit `skills/`, `commands/*.toml`,
  `hooks/hooks.json`.
- **Lokal:** `~/.gemini/skills/<name>/` oder `~/.agents/skills/<name>/`; Extensions unter
  `~/.gemini/extensions/<name>/`. App nur Upload von Hand.
- **Sicherheit:** App-Skripte in Googles Sandbox ohne Netz; CLI-Extensions starten lokale
  MCP-Prozesse und Hooks (echte Codeausführung), Umgebung gefiltert bis auf `settings[].envVar`.
- Quellen: support.google.com/gemini/answer/17094296, geminicli.com/docs/extensions/reference.md,
  geminicli.com/docs/cli/using-agent-skills (o. D.).

## Mistral (Le Chat, Vibe)

- **Arten:** Le Chat: Connector-Verzeichnis, Custom MCP Connectors (nur entfernte URL), Agents.
  Vibe (CLI): Skills. Skills in Le Chat *nicht gefunden*.
- **Formate:** Vibe-Skill = `SKILL.md` (`name`, `description`; optional `user-invocable`,
  `allowed-tools`, `license`, `compatibility`). Custom Connector = Name, Server-URL, Beschreibung.
- **Lokal:** `~/.vibe/skills/<name>/` (Projekt `.vibe/skills/` oder `.agents/skills/`).
  Le Chat nur von Hand, MCP-Server muss öffentlich erreichbar sein.
- Quellen: docs.mistral.ai/vibe/code/cli/skills (o. D.),
  help.mistral.ai/en/articles/393572-configuring-a-custom-connector (o. D.),
  mistral.ai/news/connectors (22.05.2026).

## Open WebUI

- **Arten:** Workspace Tools und Functions (Pipe, Filter, Action) in Python; Workspace Skills
  (Markdown); MCP nativ seit v0.6.31, nur Streamable HTTP (stdio über mcpo); OpenAPI-Tool-Server.
- **Formate:** Tool = eine `.py`-Datei mit Docstring-Kopf (`title`, `author`, `description`,
  `version`, `license`, `requirements`) und `class Tools` mit `Valves`. Skill = Markdown mit
  optionalem Frontmatter, Import als `.md`.
- **Lokal:** kein Verzeichnis; alles liegt in der Datenbank. Import in der Oberfläche oder per
  REST (`POST /api/v1/tools/create`, Schema *nicht verifiziert*, im Code
  `backend/open_webui/routers/tools.py` prüfen).
- **Sicherheit (kritisch):** Tools und Functions laufen im Serverprozess („equivalent to giving
  them shell access to the server“); `requirements` werden beim Import per pip installiert, außer
  `ENABLE_PIP_INSTALL_FRONTMATTER_REQUIREMENTS=False`. Tools können `__user__`,
  `__oauth_token__`, `__messages__`, `__files__` erhalten – relevant für die DSGVO-Ampel.
- Quellen: docs.openwebui.com/features/extensibility/plugin/tools.md,
  …/tools/development, docs.openwebui.com/features/workspace/skills.md,
  docs.openwebui.com/features/mcp (o. D.).

## Empfehlung für `luibui-install`

| Plattform | Zuerst | Aktion des Installers | Aufwand |
|---|---|---|---|
| Gemini | Agent Skill (CLI/Antigravity) | Ordner nach `~/.gemini/skills/<name>/`; für die App eine Upload-`.zip` mit `SKILL.md` im Wurzelverzeichnis und Anleitung. MCP später als `gemini-extension.json` | S, Extension M |
| ChatGPT | Skill | Codex: `~/.agents/skills/<name>/`; ChatGPT Web: Upload-`.zip` und Anleitung. MCP nur als Anleitung (entfernte HTTPS-URL) | S, Plugin M |
| Mistral | Vibe-Skill | `~/.vibe/skills/<name>/`; Le Chat nur Anleitung, wenn `endpunkte` eine öffentliche HTTPS-MCP-URL nennt | S |
| Open WebUI | Skill, dann MCP; Python-Tools zurückstellen | Skill als `.md` erzeugen, optional per API importieren (URL und Token vom Nutzer); MCP als Anleitung | S, MCP M, Tools L |

Umsetzungsidee: ein gemeinsamer Adapter „Agent-Skill-Ordner“ mit Zielpfad je Plattform
(Claude, Codex, Gemini CLI, Vibe) plus ein Ausgabeformat „Upload-ZIP“ für ChatGPT Web und die
Gemini-App. Pakete mit `ziele: openwebui` und `typ: tool` brauchen vorher eine eigene Prüfung
(Frontmatter-`requirements`, gefährliche Imports), weil der Code beim Nutzer als Servercode läuft.
