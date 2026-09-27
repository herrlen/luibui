"""Narrow adapters for external scanners (CLAUDE.md: subprocess with timeout, parsed JSON output,
never called directly from the pipeline)."""


class ToolError(Exception):
    """The scanner is missing, timed out or produced unusable output. Never contains content."""
