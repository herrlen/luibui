"""The only entry point for package content (CLAUDE.md rule 2).

Every function writes into an existing, empty scratch directory owned by the job and raises
``IntakeRejectedError`` for anything unsafe. Nothing here executes, imports or evaluates content.
Git clones follow in ``safe_git`` (S1-3).
"""

from luibui_scan.intake.errors import Ablehnung, IntakeRejectedError
from luibui_scan.intake.limits import DEFAULT_LIMITS, Limits
from luibui_scan.intake.safe_extract import extract_zip
from luibui_scan.intake.sources import (
    accept_directory,
    accept_file,
    accept_selection,
    accept_text,
)

__all__ = [
    "DEFAULT_LIMITS",
    "Ablehnung",
    "IntakeRejectedError",
    "Limits",
    "accept_directory",
    "accept_file",
    "accept_selection",
    "accept_text",
    "extract_zip",
]
