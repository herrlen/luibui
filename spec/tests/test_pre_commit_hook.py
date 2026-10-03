"""S5-5: the pre-commit hook definition calls the real CLI with valid options."""

from pathlib import Path

import yaml

from luibui_cli.main import build_parser

HOOKS = Path(__file__).parents[2] / ".pre-commit-hooks.yaml"


def test_hook_entry_is_a_valid_luibui_call() -> None:
    hooks = yaml.safe_load(HOOKS.read_text(encoding="utf-8"))
    hook = next(h for h in hooks if h["id"] == "luibui-scan")
    befehl, *argumente = hook["entry"].split()
    assert befehl == "luibui" and hook["language"] == "system" and not hook["pass_filenames"]
    args = build_parser().parse_args([*argumente, *hook["args"]])
    assert args.command == "scan" and args.fail_on == "rot" and str(args.pfad) == "."
