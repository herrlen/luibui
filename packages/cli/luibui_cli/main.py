"""Entry point of the ``luibui`` command. Subcommands arrive from Sprint 1 on (S1-11: scan)."""

import argparse
from collections.abc import Sequence

from luibui_scan import __version__ as engine_version


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="luibui",
        description="Prüft KI-Skills, Plugins und MCP-Server lokal auf Sicherheit und Datenschutz.",
    )
    parser.add_argument("--version", action="version", version=f"luibui-scan {engine_version}")
    parser.add_subparsers(dest="command", metavar="<befehl>")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
    return 0
