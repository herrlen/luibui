# LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("beispiel")
BASIS = Path("/daten").resolve()
MODELL_DATEI = "modell.json"


@mcp.tool()
def lesen(pfad: str) -> str:
    # ruleid: LB-C12-pfad-ohne-grenze-py
    return open(pfad).read()


@mcp.tool()
async def loeschen(datei: str) -> str:
    # ruleid: LB-C12-pfad-ohne-grenze-py
    os.remove(datei)
    return "ok"


@mcp.tool()
def sicher(pfad: str) -> str:
    ziel = (BASIS / pfad).resolve()
    if not ziel.is_relative_to(BASIS):
        raise ValueError("außerhalb")
    # ok: LB-C12-pfad-ohne-grenze-py
    return open(ziel).read()


def kein_tool(pfad: str) -> str:
    # ok: LB-C12-pfad-ohne-grenze-py
    return open(pfad).read()


@mcp.tool()
def als_text(pfad: str) -> str:
    # ruleid: LB-C12-pfad-ohne-grenze-py
    return Path(pfad).read_text()


@mcp.tool()
def vorhanden(pfad: str) -> bool:
    # ok: LB-C12-pfad-ohne-grenze-py
    return Path(pfad).exists()


@mcp.tool()
def aufgeloest(pfad: str) -> str:
    # ok: LB-C12-pfad-ohne-grenze-py
    return str(Path(pfad).resolve())


@mcp.tool()
def modell(ordner: str) -> str:
    # ok: LB-C12-pfad-ohne-grenze-py
    return open(os.path.join(ordner, MODELL_DATEI)).read()


@mcp.tool()
def beliebig(ordner: str, name: str) -> str:
    # ruleid: LB-C12-pfad-ohne-grenze-py
    return open(os.path.join(ordner, name)).read()
