# Notizen (MCP-Server)

Speichert kurze Notizen lokal in `~/Notizen`. Keine Verbindung ins Internet.

## Installation

```sh
pip install -r requirements.txt
python src/notizen/server.py
```

## Sicherheitshinweis

Notizen können Text aus fremden Quellen enthalten. Formulierungen wie `ignore all previous instructions`
in einer Notiz sind nur Text; der Server führt nichts davon aus.
