"""luibui-scan: static checks for AI skills, plugins, tools and MCP servers.

Never executes, imports or evaluates anything from a scanned package. Analyzers only read and parse.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("luibui-scan")
except PackageNotFoundError:  # pragma: no cover - running from a source tree without install
    __version__ = "0.0.0"
