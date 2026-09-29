"""MCP tools read statically from the package (S2-3). Nothing is imported, run or started.

Python is parsed with ``ast`` (a syntax tree only; the code never runs): FastMCP and the official
SDK (``@mcp.tool``, ``@server.tool()``) and ``Tool(name=…, description=…, inputSchema=…)``.
JavaScript/TypeScript is matched with patterns (``server.tool("name", "…")``,
``registerTool("name", {description: …})``, ``{name: …, description: …}`` and zod
``.describe("…")``). Only literal text is read; text built at run time stays unknown.
"""

import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from luibui_scan.analyzers._common import TextFile

MAX_TEXT = 20_000
"""Longer descriptions are cut for the checks (they are never shown in full)."""


@dataclass(frozen=True, slots=True)
class Text:
    art: str
    """``name``, ``beschreibung`` or ``parameter <name>``."""
    text: str
    zeile: int


@dataclass(slots=True)
class Tool:
    name: str
    datei: str
    zeile: int
    texte: list[Text] = field(default_factory=list)
    faehigkeiten: set[str] = field(default_factory=set)
    """What the handler does (Python only): ``befehle``, ``dateien``."""

    @property
    def beschreibung(self) -> str:
        return " ".join(t.text for t in self.texte if t.art == "beschreibung")


# --- Python ------------------------------------------------------------------------------------


def _str(node: ast.AST | None) -> str | None:
    """Literal text of a node: plain strings, f-strings (parts only) and ``"a" + "b"``."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(
            v.value if isinstance(v, ast.Constant) and isinstance(v.value, str) else "{…}"
            for v in node.values
        )
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _str(node.left), _str(node.right)
        if left is not None and right is not None:
            return left + right
    return None


def _kwarg(call: ast.Call, name: str) -> ast.AST | None:
    return next((k.value for k in call.keywords if k.arg == name), None)


def _is_tool_decorator(d: ast.expr) -> ast.Call | bool:
    """``@x.tool``, ``@x.tool(...)``, ``@tool``, ``@tool(...)``; the call if there is one."""
    target = d.func if isinstance(d, ast.Call) else d
    named = (isinstance(target, ast.Attribute) and target.attr == "tool") or (
        isinstance(target, ast.Name) and target.id == "tool"
    )
    if not named:
        return False
    return d if isinstance(d, ast.Call) else True


def _field_description(annotation: ast.AST | None, default: ast.AST | None) -> str | None:
    """``Annotated[str, Field(description=…)]`` or ``x: str = Field(description=…)``."""
    for node in (default, annotation):
        if node is None:
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                text = _str(_kwarg(sub, "description"))
                if text is not None:
                    return text
    return None


_BEFEHLE = {"system", "popen", "run", "call", "check_call", "check_output", "Popen", "exec", "eval"}
_DATEI_AENDERN = {
    "write_text", "write_bytes", "unlink", "rmtree", "remove", "rmdir", "rename", "replace",
    "move", "copy", "copyfile", "copytree", "mkdir", "makedirs", "truncate",
}  # fmt: skip


def _faehigkeiten(fn: ast.AST) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
        owner = f.value.id if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) else ""
        if (
            (owner in ("subprocess", "os") and name in _BEFEHLE)
            or (not owner and name in ("exec", "eval", "system"))
            or (owner == "asyncio" and name.startswith("create_subprocess_"))
        ):
            found.add("befehle")
        elif name in _DATEI_AENDERN and owner not in ("json", "re", "str", "list", "dict"):
            found.add("dateien")
        elif name == "open" and len(node.args) >= 2:
            mode = _str(node.args[1]) or ""
            if any(c in mode for c in "wax+"):
                found.add("dateien")
        elif name == "open" and any(c in (_str(_kwarg(node, "mode")) or "") for c in "wax+"):
            found.add("dateien")
    return found


def _konstanten(tree: ast.Module) -> dict[str, str]:
    """``X = "…"`` at module level and in classes (enums): ``{"X": …, "Klasse.X": …}``."""
    out: dict[str, str] = {}
    for node in tree.body:
        prefix, body = (
            (f"{node.name}.", node.body) if isinstance(node, ast.ClassDef) else ("", [node])
        )
        for stmt in body:
            if isinstance(stmt, ast.Assign) and (text := _str(stmt.value)) is not None:
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        out[prefix + target.id] = text
    return out


def _name(node: ast.AST | None, konstanten: dict[str, str]) -> str | None:
    if (text := _str(node)) is not None:
        return text
    if isinstance(node, ast.Name | ast.Attribute):
        key = ast.unparse(node).removesuffix(".value")  # Enum members: Tools.X.value
        return konstanten.get(key, key)
    return None


def _python(f: TextFile) -> Iterator[Tool]:
    try:
        tree = ast.parse(f.text, filename=f.path)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return
    konstanten = _konstanten(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            deco = next((r for d in node.decorator_list if (r := _is_tool_decorator(d))), None)
            if deco is None:
                continue
            call = deco if isinstance(deco, ast.Call) else None
            name = (_str(_kwarg(call, "name")) if call else None) or node.name
            tool = Tool(name, f.path, node.lineno)
            tool.texte.append(Text("name", name, node.lineno))
            desc = _str(_kwarg(call, "description")) if call else None
            zeile = node.lineno
            if desc is None and (desc := ast.get_docstring(node)) is not None:
                zeile = node.body[0].lineno
            if desc:
                tool.texte.append(Text("beschreibung", desc[:MAX_TEXT], zeile))
            args = node.args.args + node.args.kwonlyargs
            defaults: list[ast.expr | None] = [None] * (
                len(node.args.args) - len(node.args.defaults)
            )
            defaults += [*node.args.defaults, *node.args.kw_defaults]
            for arg, default in zip(args, defaults, strict=False):
                text = _field_description(arg.annotation, default)
                if text:
                    tool.texte.append(Text(f"parameter {arg.arg}", text[:MAX_TEXT], arg.lineno))
            tool.faehigkeiten = _faehigkeiten(node)
            yield tool
        elif isinstance(node, ast.Call):
            func = node.func
            called = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            tool_name = _name(_kwarg(node, "name"), konstanten)
            if called != "Tool" or tool_name is None:
                continue
            tool = Tool(tool_name, f.path, node.lineno)
            tool.texte.append(Text("name", tool_name, node.lineno))
            desc = _str(_kwarg(node, "description"))
            if desc:
                tool.texte.append(Text("beschreibung", desc[:MAX_TEXT], node.lineno))
            schema = _kwarg(node, "inputSchema") or _kwarg(node, "input_schema")
            for sub in ast.walk(schema) if schema is not None else ():
                if isinstance(sub, ast.Dict):
                    for k, v in zip(sub.keys, sub.values, strict=False):
                        if _str(k) == "description" and (text := _str(v)):
                            tool.texte.append(Text("parameter", text[:MAX_TEXT], sub.lineno))
            yield tool


# --- JavaScript / TypeScript -------------------------------------------------------------------

_S = r"""(?:"((?:\\.|[^"\\\n])*)"|'((?:\\.|[^'\\\n])*)'|`((?:\\.|[^`\\])*)`)"""
_TOOL_CALL = re.compile(rf"\.tool\(\s*{_S}\s*,\s*(?:{_S})?")
_DESCRIPTION = re.compile(rf"\bdescription\s*:\s*{_S}")
_INPUT_SCHEMA = re.compile(r"\binputSchema\b")
_NAME_BEFORE = (
    re.compile(rf"\.registerTool\(\s*{_S}"),
    re.compile(rf"\bname\s*:\s*{_S}"),
    re.compile(rf"\b(?:const|let|var)\s+\w*[Nn]ame\s*=\s*{_S}"),
    re.compile(rf"\btitle\s*:\s*{_S}"),
)
_DESCRIBE = re.compile(rf"\.describe\(\s*{_S}\s*\)")
_MCP_JS = re.compile(r"@modelcontextprotocol/sdk|McpServer|\bServer\s*\(|ListToolsRequestSchema")
_JS_SUFFIXES = frozenset({".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts"})


def _group(m: re.Match[str], first: int) -> str | None:
    """The text of the ``_S`` alternative that matched, starting at group ``first``."""
    for i in range(first, first + 3):
        if m.group(i) is not None:
            return m.group(i)
    return None


def _js_name(text: str, pos: int) -> str:
    """The name of a tool object, in this order: registerTool("…"), name: "…", const name = "…",
    and only then its display title; each time the one closest before the description."""
    for pattern in _NAME_BEFORE:
        found = [_group(m, 1) for m in pattern.finditer(text, max(0, pos - 800), pos)]
        if found and found[-1] is not None:
            return found[-1]
    return "unbenannt"


def _javascript(f: TextFile) -> Iterator[Tool]:
    if not _MCP_JS.search(f.text):
        return
    starts: list[tuple[int, Tool]] = []
    for m in _TOOL_CALL.finditer(f.text):
        name = _group(m, 1) or ""
        tool = Tool(name, f.path, f.line_of(m.start()))
        tool.texte.append(Text("name", name, tool.zeile))
        if (desc := _group(m, 4)) is not None:
            tool.texte.append(Text("beschreibung", desc[:MAX_TEXT], tool.zeile))
        starts.append((m.start(), tool))
    # Tool objects: registerTool configs, ListTools entries, config constants. What makes them a
    # tool (and not a resource or prompt) is the input schema right after the description.
    for m in _DESCRIPTION.finditer(f.text):
        schema = _INPUT_SCHEMA.search(f.text, m.end(), m.end() + 600)
        between = f.text[m.end() : schema.start()] if schema else ""
        if schema is None or _DESCRIPTION.search(between):
            continue
        name = _js_name(f.text, m.start())
        tool = Tool(name, f.path, f.line_of(m.start()))
        tool.texte.append(Text("name", name, tool.zeile))
        tool.texte.append(Text("beschreibung", (_group(m, 1) or "")[:MAX_TEXT], tool.zeile))
        starts.append((m.start(), tool))
    starts.sort(key=lambda s: s[0])
    for m in _DESCRIBE.finditer(f.text):
        before = [t for pos, t in starts if pos < m.start()]
        owner = before[-1] if before else starts[0][1] if starts else None
        if owner is not None:
            text = (_group(m, 1) or "")[:MAX_TEXT]
            owner.texte.append(Text("parameter", text, f.line_of(m.start())))
    yield from (t for _, t in starts)


def tools(files: list[TextFile]) -> list[Tool]:
    out: list[Tool] = []
    for f in files:
        suffix = PurePosixPath(f.path).suffix.lower()
        if suffix in (".py", ".pyw"):
            out += _python(f)
        elif suffix in _JS_SUFFIXES:
            out += _javascript(f)
    return out
