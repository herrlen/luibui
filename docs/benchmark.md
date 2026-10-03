# Benchmark

Stand `faaeb61+lokal`, gemessen am 2026-10-03 mit `python -m luibui_scan.benchmark` (S3-2). Erzeugt, nicht von Hand ändern. Begründungen der Kalibrierung stehen im Prüfkatalog §14, der Verlauf in `docs/log.md`.

## Ergebnis

| Messung | Wert | Ziel Sprint 3 | |
|---|---|---|---|
| Erkennung, Nachbildungen | 39/39 (100 %) | ≥ 90 % | erreicht |
| Erkennung, Code-Ebene | 4/4 (100 %) | ≥ 95 % | erreicht |
| Fehlalarme, echte Pakete | 0/60 (0 %) | ≤ 5 % | erreicht |
| … ohne Ausnahmen (`berechtigt`) | 5/60 (8 %) | – | zutreffende Befunde, nach Prüfung ausgenommen |
| Fehlalarme, eigener Korpus | 0/37 (0 %) | 0 | |

Erkannt heißt: die erwartete Regel hat angeschlagen und die Gesamtampel ist nicht grün. Fehlalarm heißt: ein gutartiges Paket hat mindestens einen K- oder H-Befund. Bekannte Lücken aus OSV zählen nicht als Fehlalarm und stehen gesondert.

**Grenzen:** Die Nachbildungen sind je eine Datei pro Zeile der Scanner-Matrix, keine vollständigen Pakete, und stammen vom selben Team wie die Regeln. Die Erkennungsrate zeigt daher, ob jede Prüfung greift, nicht wie gut luibui unbekannte Angriffe findet.

## Nicht vollständig gelaufen

- **A08 – Bekannte Schadsoftware:** fehlgeschlagen (ToolError)

## Erkennung je Ebene

| Ebene | Erkannt |
|---|---|
| A | 22/22 (100 %) |
| B | 6/6 (100 %) |
| C | 4/4 (100 %) |
| D | 3/3 (100 %) |
| E | 3/3 (100 %) |
| G | 1/1 (100 %) |

## Nachbildungen

| Matrix | Gruppe | Erwartet | Ampel | Erkannt |
|---|---|---|---|---|
| AGT-01 | Agenten-Konfiguration | `LB-B08` | gesperrt | ja |
| AGT-02 | Agenten-Konfiguration | `LB-B01-unicode-tags` | gesperrt | ja |
| AGT-03 | Agenten-Konfiguration | `LB-B06-kodierter-text` | gesperrt | ja |
| AGT-04 | Agenten-Konfiguration | `LB-E08-werkzeugrechte` | gelb | ja |
| AGT-05 | Agenten-Konfiguration | `LB-A02-claude-hooks` | gesperrt | ja |
| AGT-06 | Agenten-Konfiguration | `LB-E09-fremdes-paket` | rot | ja |
| AGT-08 | Agenten-Konfiguration | `LB-E01-tool-poisoning` | gesperrt | ja |
| AGT-09 | Agenten-Konfiguration | `LB-A02-python-pth` | gesperrt | ja |
| AGT-10 | Agenten-Konfiguration | `LB-D03-namensverwechslung` | rot | ja |
| ARC-02 | Archive und Dateinamen | `LB-A13-git-treiber` | gelb | ja |
| ARC-03 | Archive und Dateinamen | `LB-A14-doppelendung` | gelb | ja |
| BIN-01 | Binärdateien | `LB-A04-installationspaket` | rot | ja |
| BIN-02 | Binärdateien | `LB-A02-python-pth` | gesperrt | ja |
| COD-01 | Code | `LB-C04-zugangsdaten-lesen` | gesperrt | ja |
| COD-03 | Code | `LB-C08-verschleiert` | gesperrt | ja |
| COD-04 | Code | `LB-A03-installationsskript` | gesperrt | ja |
| COD-05 | Code | `LB-A02-python-pth` | gesperrt | ja |
| COD-06 | Code | `LB-A02-setup-py` | gesperrt | ja |
| COD-07 | Code | `LB-A02-devcontainer` | gesperrt | ja |
| COD-08 | Code | `LB-C14-container` | rot | ja |
| COD-09 | Code | `LB-C15-ci-workflow` | rot | ja |
| COD-10 | Code | `LB-A06-kompiliert-ohne-quelle` | gelb | ja |
| DAT-01 | Datendateien | `LB-G07-personenbezogene-daten` | gelb | ja |
| DAT-02 | Datendateien | `LB-A20-formel-in-tabelle` | rot | ja |
| DAT-03 | Datendateien | `LB-B08` | gelb | ja |
| DEP-01 | Abhängigkeiten | `LB-D03-namensverwechslung` | rot | ja |
| DEP-03 | Abhängigkeiten | `LB-A12-fremde-paketquelle` | rot | ja |
| DEP-04 | Abhängigkeiten | `LB-D05-unsichere-quelle` | gelb | ja |
| DOC-01 | Dokumente | `LB-A21-pdf-aktiv` | rot | ja |
| DOC-02 | Dokumente | `LB-A21-office-aktiv` | rot | ja |
| DOC-03 | Dokumente | `LB-B21-aktive-inhalte` | gelb | ja |
| INV-01 | Inventar | `LB-A15-angehaengte-daten` | rot | ja |
| MOD-01 | Modelle | `LB-A16-pickle-code` | gesperrt | ja |
| MOD-02 | Modelle | `LB-A17-keras-lambda` | rot | ja |
| MOD-03 | Modelle | `LB-A17-onnx-externer-pfad` | rot | ja |
| MOD-04 | Modelle | `LB-A16-template-code` | gesperrt | ja |
| MOD-06 | Modelle | `LB-A18-modell-unklar` | gelb | ja |
| MOD-07 | Modelle | `LB-A19-remote-code` | gelb | ja |
| SEC-01 | Secrets | `LB-B20-schluesseldatei` | gesperrt | ja |

## Gutartig, echte Pakete

| Paket | Stand | Ampel | K/H-Befunde | Bekannte Lücken |
|---|---|---|---|---|
| anthropics/skills/skills/algorithmic-art | 8a1541c4a3ff | gelb | – | – |
| anthropics/skills/skills/brand-guidelines | 8a1541c4a3ff | gelb | – | – |
| anthropics/skills/skills/canvas-design | 8a1541c4a3ff | gelb | – | – |
| anthropics/skills/skills/frontend-design | 8a1541c4a3ff | gelb | – | – |
| anthropics/skills/skills/internal-comms | 8a1541c4a3ff | gelb | – | – |
| anthropics/skills/skills/mcp-builder | 8a1541c4a3ff | gelb | – | – |
| anthropics/skills/skills/skill-creator | 8a1541c4a3ff | gelb | – | – |
| anthropics/skills/skills/slack-gif-creator | 8a1541c4a3ff | rot | – | 1 |
| anthropics/skills/skills/theme-factory | 8a1541c4a3ff | gelb | – | – |
| anthropics/skills/skills/web-artifacts-builder | 8a1541c4a3ff | gelb | – | – |
| anthropics/skills/skills/webapp-testing | 8a1541c4a3ff | rot | –<br>berechtigt: `K bandit:B602 scripts/with_server.py` | – |
| anthropics/claude-plugins-official/plugins/agent-sdk-dev | d182ca456ca0 | gelb | – | – |
| anthropics/claude-plugins-official/plugins/claude-md-management | d182ca456ca0 | gelb | – | – |
| anthropics/claude-plugins-official/plugins/code-review | d182ca456ca0 | gelb | – | – |
| anthropics/claude-plugins-official/plugins/code-simplifier | d182ca456ca0 | gelb | – | – |
| anthropics/claude-plugins-official/plugins/commit-commands | d182ca456ca0 | gelb | – | – |
| anthropics/claude-plugins-official/plugins/explanatory-output-style | d182ca456ca0 | gelb | – | – |
| anthropics/claude-plugins-official/plugins/feature-dev | d182ca456ca0 | gelb | – | – |
| anthropics/claude-plugins-official/plugins/hookify | d182ca456ca0 | gelb | – | – |
| anthropics/claude-plugins-official/plugins/mcp-server-dev | d182ca456ca0 | gelb | – | – |
| anthropics/claude-plugins-official/plugins/plugin-dev | d182ca456ca0 | gelb | – | – |
| anthropics/claude-plugins-official/plugins/pr-review-toolkit | d182ca456ca0 | gelb | – | – |
| anthropics/claude-plugins-official/plugins/ralph-loop | d182ca456ca0 | gelb | – | – |
| anthropics/claude-plugins-official/plugins/security-guidance | d182ca456ca0 | gelb | – | – |
| obra/superpowers/skills/brainstorming | 8ca22dba9a94 | rot | –<br>berechtigt: `H LB-C01-shell-mit-eingabe scripts/server.cjs` | – |
| obra/superpowers/skills/executing-plans | 8ca22dba9a94 | gelb | – | – |
| obra/superpowers/skills/finishing-a-development-branch | 8ca22dba9a94 | gelb | – | – |
| obra/superpowers/skills/receiving-code-review | 8ca22dba9a94 | gelb | – | – |
| obra/superpowers/skills/requesting-code-review | 8ca22dba9a94 | gelb | – | – |
| obra/superpowers/skills/subagent-driven-development | 8ca22dba9a94 | gelb | – | – |
| obra/superpowers/skills/systematic-debugging | 8ca22dba9a94 | gelb | – | – |
| obra/superpowers/skills/test-driven-development | 8ca22dba9a94 | gelb | – | – |
| obra/superpowers/skills/using-git-worktrees | 8ca22dba9a94 | gelb | – | – |
| obra/superpowers/skills/writing-plans | 8ca22dba9a94 | gelb | – | – |
| modelcontextprotocol/python-sdk/examples/servers/simple-auth | 2118f14f8a19 | gelb | – | – |
| modelcontextprotocol/python-sdk/examples/servers/simple-pagination | 2118f14f8a19 | gelb | – | – |
| modelcontextprotocol/python-sdk/examples/servers/simple-prompt | 2118f14f8a19 | gelb | – | – |
| modelcontextprotocol/python-sdk/examples/servers/simple-resource | 2118f14f8a19 | gelb | – | – |
| modelcontextprotocol/python-sdk/examples/servers/simple-streamablehttp | 2118f14f8a19 | gelb | – | – |
| modelcontextprotocol/python-sdk/examples/servers/simple-streamablehttp-stateless | 2118f14f8a19 | gelb | – | – |
| modelcontextprotocol/python-sdk/examples/servers/simple-tool | 2118f14f8a19 | gelb | – | – |
| modelcontextprotocol/python-sdk/examples/servers/structured-output-lowlevel | 2118f14f8a19 | gelb | – | – |
| modelcontextprotocol/servers/src/everything | f46d9578190b | rot | –<br>berechtigt: `H LB-E04-ohne-anmeldung transports/sse.ts`, `H LB-E04-ohne-anmeldung transports/streamableHttp.ts` | – |
| modelcontextprotocol/servers/src/fetch | f46d9578190b | rot | – | 2 |
| modelcontextprotocol/servers/src/filesystem | f46d9578190b | gelb | – | – |
| modelcontextprotocol/servers/src/git | f46d9578190b | rot | – | 3 |
| modelcontextprotocol/servers/src/memory | f46d9578190b | gelb | – | – |
| modelcontextprotocol/servers/src/sequentialthinking | f46d9578190b | gelb | – | – |
| modelcontextprotocol/servers/src/time | f46d9578190b | rot | – | 2 |
| microsoft/playwright-mcp | f183dad4a529 | gelb | – | – |
| awslabs/mcp/src/aws-documentation-mcp-server | 93991b85acfe | rot | – | 2 |
| awslabs/mcp/src/aws-pricing-mcp-server | 93991b85acfe | rot | – | 2 |
| awslabs/mcp/src/cloudwatch-mcp-server | 93991b85acfe | rot | –<br>berechtigt: `H LB-E09-fremdes-paket skills/agentcore-investigation/mcp/.mcp.json`, `H LB-E09-fremdes-paket skills/agentcore-investigation/mcp/.mcp.json` | 2 |
| awslabs/mcp/src/dynamodb-mcp-server | 93991b85acfe | rot | – | 3 |
| awslabs/mcp/src/ecs-mcp-server | 93991b85acfe | rot | – | 2 |
| awslabs/mcp/src/eks-mcp-server | 93991b85acfe | rot | – | 2 |
| awslabs/mcp/src/iam-mcp-server | 93991b85acfe | rot | – | 2 |
| awslabs/mcp/src/lambda-tool-mcp-server | 93991b85acfe | rot | – | 2 |
| awslabs/mcp/src/postgres-mcp-server | 93991b85acfe | rot | –<br>berechtigt: `H LB-E09-fremdes-paket kiro_power/mcp.json` | 2 |
| awslabs/mcp/src/s3-tables-mcp-server | 93991b85acfe | rot | – | 2 |

## Gutartig, eigener Korpus

| Paket | Stand | Ampel | K/H-Befunde | Bekannte Lücken |
|---|---|---|---|---|
| Matrix AGT-01 | – | gelb | – | – |
| Matrix AGT-02 | – | gelb | – | – |
| Matrix AGT-03 | – | gelb | – | – |
| Matrix AGT-04 | – | gelb | – | – |
| Matrix AGT-05 | – | gelb | – | – |
| Matrix AGT-06 | – | gelb | – | – |
| Matrix AGT-08 | – | gelb | – | – |
| Matrix ARC-02 | – | gelb | – | – |
| Matrix ARC-03 | – | gelb | – | – |
| Matrix COD-01 | – | gelb | – | – |
| Matrix COD-03 | – | gelb | – | – |
| Matrix COD-04 | – | gelb | – | – |
| Matrix COD-05 | – | gelb | – | – |
| Matrix COD-06 | – | gelb | – | – |
| Matrix COD-07 | – | gelb | – | – |
| Matrix COD-08 | – | gelb | – | – |
| Matrix COD-09 | – | gelb | – | – |
| Matrix DAT-01 | – | gelb | – | – |
| Matrix DAT-02 | – | gelb | – | – |
| Matrix DEP-03 | – | gelb | – | – |
| Matrix DOC-01 | – | gelb | – | – |
| Matrix DOC-02 | – | gelb | – | – |
| Matrix DOC-03 | – | gelb | – | – |
| Matrix INV-01 | – | gelb | – | – |
| Matrix MOD-01 | – | gelb | – | – |
| Matrix MOD-02 | – | gelb | – | – |
| Matrix MOD-03 | – | gelb | – | – |
| Matrix MOD-04 | – | gelb | – | – |
| Matrix MOD-07 | – | gelb | – | – |
| Matrix SEC-01 | – | gelb | – | – |
| beratungs-skill | – | gelb | – | – |
| notizen-mcp | – | gelb | – | – |
| repo-helfer-plugin | – | gelb | – | – |
| seo-skill | – | gelb | – | – |
| uebersetzer-mcp | – | gelb | – | – |
| wetter-skill | – | gelb | – | – |
| zusammenfassung | – | gelb | – | – |

