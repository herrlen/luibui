# LUIBUI-TESTFIXTURE: entschärft, nicht ausführen
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("beispiel")
BASIS = Path("/daten").resolve()


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
