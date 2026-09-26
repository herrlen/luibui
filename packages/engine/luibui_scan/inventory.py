"""Inventory (S1-4): file list with real types, SHA-256, languages and the detected package type.

Files are only opened for reading, never through a symlink, and only the first bytes are inspected
for the type. Package-type markers are searched as plain text; nothing is parsed as code.
"""

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from luibui_scan.context import InventoryEntry
from luibui_scan.models import Pakettyp

_HEAD = 4096
_CHUNK = 64 * 1024
_MARKER_MAX_BYTES = 1024 * 1024


class InventoryError(Exception):
    """The scratch directory contains something intake never creates (symlink, device, …)."""


@dataclass(frozen=True, slots=True)
class Inventory:
    entries: tuple[InventoryEntry, ...]
    sha256: str
    """Hash over the sorted ``path NUL sha256 LF`` lines, see ``inventory_hash``."""
    bytes: int
    sprachen: dict[str, int]
    """Language → number of files."""
    pakettyp: Pakettyp
    merkmale: tuple[str, ...]
    """Why the package type was chosen, e.g. ``skill: SKILL.md``. Paths are package content."""


# --- file types ------------------------------------------------------------------------------

_MAGIC: tuple[tuple[bytes, str], ...] = (
    (b"\x7fELF", "elf"),
    (b"\xfe\xed\xfa\xce", "macho"),
    (b"\xfe\xed\xfa\xcf", "macho"),
    (b"\xce\xfa\xed\xfe", "macho"),
    (b"\xcf\xfa\xed\xfe", "macho"),
    (b"\x00asm", "wasm"),
    (b"PK\x03\x04", "zip"),
    (b"PK\x05\x06", "zip"),
    (b"\x1f\x8b", "gzip"),
    (b"BZh", "bzip2"),
    (b"\xfd7zXZ\x00", "xz"),
    (b"7z\xbc\xaf\x27\x1c", "7z"),
    (b"Rar!\x1a\x07", "rar"),
    (b"%PDF-", "pdf"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpeg"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
    (b"SQLite format 3\x00", "sqlite"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "ole"),
)

EXECUTABLE_KINDS = frozenset({"elf", "macho", "pe", "java-class", "wasm"})


def detect_kind(head: bytes) -> str:
    """Return the real file type from the first bytes. Text is ``text``, the rest ``binary``."""
    if not head:
        return "leer"
    for magic, kind in _MAGIC:
        if head.startswith(magic):
            return kind
    if head.startswith(b"\xca\xfe\xba\xbe") and len(head) >= 8:
        # Java class files carry a version >= 45 here, fat Mach-O binaries a small arch count.
        return "java-class" if int.from_bytes(head[4:8], "big") >= 45 else "macho"
    if head.startswith(b"MZ") and not _is_text(head):
        return "pe"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if len(head) > 262 and head[257:262] == b"ustar":
        return "tar"
    if _is_text(head):
        return "script" if head.startswith(b"#!") else "text"
    return "binary"


def _is_text(head: bytes) -> bool:
    if b"\x00" in head:
        return False
    try:
        head.decode("utf-8")
    except UnicodeDecodeError as exc:
        # A multi-byte character may be cut off at the end of the sample.
        return exc.start >= len(head) - 3 and exc.reason == "unexpected end of data"
    return True


# --- languages -------------------------------------------------------------------------------

_EXT_LANG = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".tsx": "typescript",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".ps1": "powershell",
    ".psm1": "powershell",
    ".bat": "batch",
    ".cmd": "batch",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".java": "java",
    ".kt": "kotlin",
    ".cs": "csharp",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".lua": "lua",
    ".md": "markdown",
    ".mdx": "markdown",
    ".json": "json",
    ".jsonc": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".svg": "svg",
    ".xml": "xml",
    ".sql": "sql",
}
_SHEBANG = re.compile(rb"^#![^\n]*?\b(python3?|node|deno|bun|bash|sh|zsh|ruby|perl|php)\b")
_SHEBANG_LANG = {
    b"python": "python",
    b"python3": "python",
    b"node": "javascript",
    b"deno": "typescript",
    b"bun": "javascript",
    b"bash": "shell",
    b"sh": "shell",
    b"zsh": "shell",
    b"ruby": "ruby",
    b"perl": "perl",
    b"php": "php",
}


def detect_language(path: str, head: bytes) -> str | None:
    lang = _EXT_LANG.get(PurePosixPath(path).suffix.lower())
    if lang is not None:
        return lang
    match = _SHEBANG.match(head)
    return _SHEBANG_LANG[match.group(1)] if match else None


# --- package type ----------------------------------------------------------------------------

_PLUGIN_FILES = {
    ".claude-plugin/plugin.json": "Claude-Plugin",
    ".well-known/ai-plugin.json": "ChatGPT-Plugin",
    "gemini-extension.json": "Gemini-Erweiterung",
}
_MCP_TEXT = re.compile(
    r"@modelcontextprotocol/sdk|from\s+mcp[.\s]|import\s+mcp\b|\bFastMCP\b|"
    r"modelcontextprotocol/(go-sdk|rust-sdk|java-sdk|csharp-sdk)|github\.com/mark3labs/mcp-go"
)
_MCP_DEP = re.compile(r"^\s*[\"']?(mcp|fastmcp)\b", re.MULTILINE)
_CODE_LANGS = frozenset({"python", "javascript", "typescript", "go", "rust", "java", "csharp"})


def detect_package_type(
    root: Path, entries: tuple[InventoryEntry, ...]
) -> tuple[Pakettyp, tuple[str, ...]]:
    found: dict[Pakettyp, str] = {}
    for entry in entries:
        path = entry.path
        name = PurePosixPath(path).name
        lower = path.lower()
        if name.lower() == "skill.md":
            found.setdefault(Pakettyp.SKILL, f"skill: {path}")
        for suffix, label in _PLUGIN_FILES.items():
            if lower == suffix or lower.endswith("/" + suffix):
                found.setdefault(Pakettyp.PLUGIN, f"plugin: {path} ({label})")
        if entry.kind not in ("text", "script") or entry.size > _MARKER_MAX_BYTES:
            continue
        if Pakettyp.MCP_SERVER not in found and _is_mcp(root, entry, name):
            found[Pakettyp.MCP_SERVER] = f"mcp-server: {path}"
        if Pakettyp.TOOL not in found and name.endswith(".json") and _is_tool_json(root, path):
            found[Pakettyp.TOOL] = f"tool: {path}"
    merkmale = tuple(found[t] for t in sorted(found))
    if Pakettyp.PLUGIN in found:
        # A plugin bundles skills, tools and MCP servers; the bundle is the package.
        return Pakettyp.PLUGIN, merkmale
    kinds = set(found) - {Pakettyp.TOOL} if len(found) > 1 else set(found)
    if not kinds:
        return Pakettyp.UNBEKANNT, merkmale
    if len(kinds) == 1:
        return kinds.pop(), merkmale
    return Pakettyp.GEMISCHT, merkmale


def _read_text(root: Path, path: str) -> str:
    return _read(root, path, _MARKER_MAX_BYTES).decode("utf-8", errors="replace")


def _is_mcp(root: Path, entry: InventoryEntry, name: str) -> bool:
    if name == "package.json":
        return "@modelcontextprotocol/sdk" in _read_text(root, entry.path)
    if name in ("pyproject.toml", "requirements.txt"):
        return _MCP_DEP.search(_read_text(root, entry.path)) is not None
    if name == "server.json":
        return "modelcontextprotocol" in _read_text(root, entry.path)
    if detect_language(entry.path, b"") in _CODE_LANGS or entry.kind == "script":
        return _MCP_TEXT.search(_read_text(root, entry.path)) is not None
    return False


def _is_tool_json(root: Path, path: str) -> bool:
    """A JSON list of tool definitions (MCP ``inputSchema`` or OpenAI function calling)."""
    try:
        data = json.loads(_read_text(root, path))
    except (ValueError, RecursionError):
        return False
    tools = data.get("tools") if isinstance(data, dict) else data
    if not isinstance(tools, list) or not tools:
        return False
    return all(_is_tool(t) for t in tools)


def _is_tool(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    function = item.get("function")
    if item.get("type") == "function" and isinstance(function, dict):
        item = function
    has_schema = any(k in item for k in ("inputSchema", "input_schema", "parameters"))
    return isinstance(item.get("name"), str) and has_schema


# --- inventory -------------------------------------------------------------------------------


def _open(root: Path, path: str) -> int:
    return os.open(root.joinpath(*path.split("/")), os.O_RDONLY | os.O_NOFOLLOW)


def _read(root: Path, path: str, limit: int) -> bytes:
    with os.fdopen(_open(root, path), "rb") as f:
        return f.read(limit)


def _hash_and_head(root: Path, path: str) -> tuple[str, bytes, int]:
    digest = hashlib.sha256()
    size = 0
    with os.fdopen(_open(root, path), "rb") as f:
        head = f.read(_HEAD)
        digest.update(head)
        size += len(head)
        while chunk := f.read(_CHUNK):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), head, size


def _walk(root: Path) -> list[str]:
    files: list[str] = []
    pending = [""]
    while pending:
        rel = pending.pop()
        with os.scandir(root / rel if rel else root) as it:
            for item in it:
                child = f"{rel}/{item.name}" if rel else item.name
                mode = item.stat(follow_symlinks=False).st_mode
                if stat.S_ISDIR(mode):
                    pending.append(child)
                elif stat.S_ISREG(mode):
                    files.append(child)
                else:
                    raise InventoryError(f"keine reguläre Datei: {child!r}")
    return sorted(files)


def inventory_hash(entries: tuple[InventoryEntry, ...]) -> str:
    digest = hashlib.sha256()
    for entry in sorted(entries, key=lambda e: e.path.encode()):
        digest.update(entry.path.encode() + b"\x00" + entry.sha256.encode() + b"\n")
    return digest.hexdigest()


def build_inventory(root: Path) -> Inventory:
    """Inventory every regular file below ``root`` (the job's scratch after intake)."""
    entries: list[InventoryEntry] = []
    sprachen: dict[str, int] = {}
    for path in _walk(root):
        sha256, head, size = _hash_and_head(root, path)
        kind = detect_kind(head)
        sprache = detect_language(path, head) if kind in ("text", "script") else None
        entries.append(InventoryEntry(path, size, sha256, kind, sprache))
        if sprache is not None:
            sprachen[sprache] = sprachen.get(sprache, 0) + 1
    frozen = tuple(entries)
    pakettyp, merkmale = detect_package_type(root, frozen)
    return Inventory(
        entries=frozen,
        sha256=inventory_hash(frozen),
        bytes=sum(e.size for e in frozen),
        sprachen=dict(sorted(sprachen.items())),
        pakettyp=pakettyp,
        merkmale=merkmale,
    )
