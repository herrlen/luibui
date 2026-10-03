"""Entry point of the ``luibui`` command."""

import argparse
import sys
from collections.abc import Sequence

from luibui_cli import audit, scan
from luibui_scan import __version__ as engine_version


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="luibui",
        description="Prüft KI-Skills, Plugins und MCP-Server lokal auf Sicherheit und Datenschutz.",
    )
    parser.add_argument("--version", action="version", version=f"luibui-scan {engine_version}")
    subparsers = parser.add_subparsers(dest="command", metavar="<befehl>")
    scan.add_parser(subparsers)
    audit.add_parser(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args_roh = list(sys.argv[1:] if argv is None else argv)
    if args_roh[:1] == ["install"]:
        # Same tool as the public `luibui-install` (S4-5), so both behave identically.
        from luibui_install.main import main as install

        return install(args_roh[1:])
    parser = build_parser()
    args = parser.parse_args(args_roh)
    if args.command is None:
        parser.print_help()
        return 0
    code: int = args.run(args, sys.stdout, sys.stderr)
    return code
