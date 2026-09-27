"""MCP server that keeps short notes in a local folder chosen by the user."""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("notizen")
NOTES = Path.home() / "Notizen"


@mcp.tool()
def notiz_speichern(titel: str, text: str) -> str:
    """Speichert eine Notiz unter dem Titel im Ordner ~/Notizen."""
    NOTES.mkdir(exist_ok=True)
    name = "".join(c for c in titel if c.isalnum() or c in " -_").strip() or "notiz"
    (NOTES / f"{name}.md").write_text(text, encoding="utf-8")
    return f"Gespeichert: {name}.md"


@mcp.tool()
def notizen_auflisten() -> list[str]:
    """Listet die Titel aller gespeicherten Notizen."""
    return sorted(p.stem for p in NOTES.glob("*.md"))


if __name__ == "__main__":
    mcp.run()
