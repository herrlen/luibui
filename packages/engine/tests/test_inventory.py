"""S1-4: inventory with real file types, hashes, languages and package type."""

import hashlib
import json
from pathlib import Path

import pytest

from luibui_scan.inventory import (
    InventoryError,
    build_inventory,
    detect_kind,
    detect_language,
    inventory_hash,
)
from luibui_scan.models import Pakettyp


def write(root: Path, files: dict[str, bytes | str]) -> Path:
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode() if isinstance(content, str) else content)
    return root


# --- file types ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("head", "kind"),
    [
        (b"", "leer"),
        (b"# Skill\n", "text"),
        ("Grüße ✓".encode(), "text"),
        ("ä".encode()[:1], "text"),  # multi-byte character cut off at the end of the sample
        (b"#!/usr/bin/env python3\nprint(1)", "script"),
        (b"\x7fELF\x02\x01\x01", "elf"),
        (b"\xcf\xfa\xed\xfe\x07\x00", "macho"),
        (b"\xca\xfe\xba\xbe\x00\x00\x00\x02", "macho"),
        (b"\xca\xfe\xba\xbe\x00\x00\x00\x41", "java-class"),
        (b"MZ\x90\x00\x03\x00\x00\x00", "pe"),
        ("MZ ist ein Kürzel\n".encode(), "text"),
        (b"\x00asm\x01\x00\x00\x00", "wasm"),
        (b"PK\x03\x04\x14\x00", "zip"),
        (b"\x1f\x8b\x08", "gzip"),
        (b"%PDF-1.7", "pdf"),
        (b"\x89PNG\r\n\x1a\n", "png"),
        (b"RIFF\x00\x00\x00\x00WEBPVP8 ", "webp"),
        (b"\x00" * 257 + b"ustar\x0000" + b"\x00" * 10, "tar"),
        (b"\x00\x01\x02\xff", "binary"),
        (b"\xff\xfe\xfa", "binary"),
    ],
)
def test_detect_kind(head: bytes, kind: str) -> None:
    assert detect_kind(head) == kind


@pytest.mark.parametrize(
    ("path", "head", "lang"),
    [
        ("src/server.py", b"", "python"),
        ("index.MJS", b"", "javascript"),
        ("a.tsx", b"", "typescript"),
        ("SKILL.md", b"", "markdown"),
        ("bin/run", b"#!/usr/bin/env node\n", "javascript"),
        ("install", b"#!/bin/sh\necho harmlos", "shell"),
        ("tool", b"#!/usr/bin/python3 -u\n", "python"),
        ("LICENSE", b"MIT", None),
    ],
)
def test_detect_language(path: str, head: bytes, lang: str | None) -> None:
    assert detect_language(path, head) == lang


# --- inventory -------------------------------------------------------------------------------


def test_inventory_entries_and_hash(tmp_path: Path) -> None:
    root = write(
        tmp_path,
        {"SKILL.md": "# Skill\n", "scripts/run.sh": "#!/bin/sh\necho harmlos\n", "logo.png": b""},
    )
    (root / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 10)
    inv = build_inventory(root)

    by_path = {e.path: e for e in inv.entries}
    assert list(by_path) == ["SKILL.md", "logo.png", "scripts/run.sh"]
    assert by_path["SKILL.md"].sha256 == hashlib.sha256(b"# Skill\n").hexdigest()
    assert by_path["SKILL.md"].size == 8
    assert (by_path["logo.png"].kind, by_path["logo.png"].sprache) == ("png", None)
    assert (by_path["scripts/run.sh"].kind, by_path["scripts/run.sh"].sprache) == (
        "script",
        "shell",
    )
    assert inv.sprachen == {"markdown": 1, "shell": 1}
    assert inv.bytes == 8 + 18 + 23
    assert inv.sha256 == inventory_hash(inv.entries)


def test_inventory_hash_is_order_independent_and_path_sensitive(tmp_path: Path) -> None:
    a = build_inventory(write(tmp_path / "a", {"x.md": "1", "y.md": "2"}))
    b = build_inventory(write(tmp_path / "b", {"y.md": "2", "x.md": "1"}))
    c = build_inventory(write(tmp_path / "c", {"x.md": "2", "y.md": "1"}))
    assert a.sha256 == b.sha256 != c.sha256
    assert inventory_hash(tuple(reversed(a.entries))) == a.sha256


def test_large_file_is_hashed_completely(tmp_path: Path) -> None:
    data = b"a" * 200_000 + b"b"
    inv = build_inventory(write(tmp_path, {"big.txt": data}))
    assert inv.entries[0].sha256 == hashlib.sha256(data).hexdigest()
    assert inv.entries[0].size == len(data)


def test_symlink_in_scratch_is_refused(tmp_path: Path) -> None:
    root = write(tmp_path / "root", {"a.md": "x"})
    (root / "link").symlink_to("/etc/passwd")
    with pytest.raises(InventoryError):
        build_inventory(root)


def test_empty_directory(tmp_path: Path) -> None:
    inv = build_inventory(tmp_path)
    assert inv.entries == ()
    assert inv.pakettyp is Pakettyp.UNBEKANNT


# --- package type ----------------------------------------------------------------------------

MCP_PKG = json.dumps({"name": "x", "dependencies": {"@modelcontextprotocol/sdk": "^1.0.0"}})
TOOLS = json.dumps(
    {"tools": [{"name": "suche", "description": "d", "inputSchema": {"type": "object"}}]}
)
PYPROJECT_MCP = '[project]\ndependencies = [\n  "mcp>=1.2",\n]\n'
OPENAI_TOOLS = json.dumps(
    [{"type": "function", "function": {"name": "suche", "parameters": {"type": "object"}}}]
)


@pytest.mark.parametrize(
    ("files", "typ"),
    [
        ({"SKILL.md": "# Skill"}, Pakettyp.SKILL),
        ({"skills/pdf/skill.md": "# Skill"}, Pakettyp.SKILL),
        ({"package.json": MCP_PKG, "index.js": "console.log(1)"}, Pakettyp.MCP_SERVER),
        ({"pyproject.toml": PYPROJECT_MCP}, Pakettyp.MCP_SERVER),
        ({"requirements.txt": "fastmcp==2.0\n"}, Pakettyp.MCP_SERVER),
        ({"server.py": "from mcp.server.fastmcp import FastMCP\n"}, Pakettyp.MCP_SERVER),
        ({"main.go": 'import "github.com/mark3labs/mcp-go/server"\n'}, Pakettyp.MCP_SERVER),
        ({"tools.json": TOOLS}, Pakettyp.TOOL),
        ({"functions.json": OPENAI_TOOLS}, Pakettyp.TOOL),
        ({".claude-plugin/plugin.json": "{}", "skills/a/SKILL.md": "x"}, Pakettyp.PLUGIN),
        ({"gemini-extension.json": "{}"}, Pakettyp.PLUGIN),
        ({".well-known/ai-plugin.json": "{}"}, Pakettyp.PLUGIN),
        ({"SKILL.md": "x", "server.py": "import mcp\n"}, Pakettyp.GEMISCHT),
        ({"server.py": "import mcp\n", "tools.json": TOOLS}, Pakettyp.MCP_SERVER),
        ({"README.md": "Hallo", "main.py": "print(1)"}, Pakettyp.UNBEKANNT),
        ({"requirements.txt": "mcpx==1.0\nrequests\n"}, Pakettyp.UNBEKANNT),
        ({"notes.md": "from mcp import x"}, Pakettyp.UNBEKANNT),
        ({"data.json": json.dumps({"tools": [{"name": "x"}]})}, Pakettyp.UNBEKANNT),
        ({"broken.json": "{" * 10}, Pakettyp.UNBEKANNT),
    ],
)
def test_package_type(tmp_path: Path, files: dict[str, str], typ: Pakettyp) -> None:
    inv = build_inventory(write(tmp_path, dict(files)))
    assert inv.pakettyp is typ


def test_package_type_names_its_evidence(tmp_path: Path) -> None:
    inv = build_inventory(write(tmp_path, {"SKILL.md": "x", "server.py": "import mcp\n"}))
    assert inv.merkmale == ("mcp-server: server.py", "skill: SKILL.md")


def test_binary_named_like_code_is_not_read_for_markers(tmp_path: Path) -> None:
    inv = build_inventory(write(tmp_path, {"server.py": b"\x7fELF\x00import mcp"}))
    assert inv.entries[0].kind == "elf"
    assert inv.pakettyp is Pakettyp.UNBEKANNT
