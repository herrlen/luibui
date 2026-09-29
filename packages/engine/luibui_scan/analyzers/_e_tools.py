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
    """What the handler does: ``befehle``, ``dateien`` (Python; JS/TS for inline handlers)."""
    art: str = "Tool"
    """``Tool``, ``Prompt`` or ``Resource``: all are read by the model, only tools act."""

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


_ARTEN = {"tool": "Tool", "prompt": "Prompt", "resource": "Resource"}


def _decorator(d: ast.expr) -> tuple[str, ast.Call | None] | None:
    """``@x.tool``, ``@x.prompt(...)``, ``@x.resource("uri")``, ``@tool``: (art, call or None)."""
    target = d.func if isinstance(d, ast.Call) else d
    if isinstance(target, ast.Attribute) and target.attr in _ARTEN:
        art = _ARTEN[target.attr]
    elif isinstance(target, ast.Name) and target.id == "tool":
        art = "Tool"
    else:
        return None
    return art, d if isinstance(d, ast.Call) else None


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
            deco = next((r for d in node.decorator_list if (r := _decorator(d))), None)
            if deco is None:
                continue
            art, call = deco
            name = (_str(_kwarg(call, "name")) if call else None) or node.name
            tool = Tool(name, f.path, node.lineno, art=art)
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
            if art == "Tool":
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
_TOOL_CALL = re.compile(rf"\.(tool|prompt)\(\s*{_S}\s*,\s*(?:{_S})?")
_REGISTER = re.compile(rf"\.(registerTool|registerPrompt|registerResource|resource)\(\s*{_S}")
_CALL_ART = {
    "tool": "Tool",
    "prompt": "Prompt",
    "registerTool": "Tool",
    "registerPrompt": "Prompt",
    "registerResource": "Resource",
    "resource": "Resource",
}
_JS_BEFEHLE = re.compile(r"\b(exec|execSync|execFile|execFileSync|spawn|spawnSync|fork)\s*\(")
_JS_DATEIEN = re.compile(
    r"\b(writeFile|writeFileSync|appendFile|appendFileSync|unlink|unlinkSync|rm|rmSync|rmdir|"
    r"rmdirSync|mkdir|mkdirSync|rename|renameSync|copyFile|copyFileSync|cp|cpSync)\s*\("
)
_JS_CHILD = re.compile(r"""["'](node:)?child_process["']""")
_JS_FS = re.compile(r"""["'](node:)?fs(/promises)?["']""")
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


def _call_end(text: str, open_paren: int) -> int:
    """Index after the parenthesis that closes the call opened at ``open_paren``; strings,
    template literals and comments are skipped. Unbalanced input ends at the end of the text."""
    depth, i, n = 0, open_paren, len(text)
    while i < n:
        c = text[i]
        if c in "\"'`":
            i += 1
            while i < n and text[i] != c:
                i += 2 if text[i] == "\\" else 1
        elif text.startswith("//", i):
            i = text.find("\n", i)
            i = n if i < 0 else i
        elif text.startswith("/*", i):
            i = text.find("*/", i)
            i = n if i < 0 else i + 1
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def _faehigkeiten_js(span: str, child: bool, fs: bool) -> set[str]:
    found = set()
    if child and _JS_BEFEHLE.search(span):
        found.add("befehle")
    if fs and _JS_DATEIEN.search(span):
        found.add("dateien")
    return found


def _javascript(f: TextFile) -> Iterator[Tool]:
    if not _MCP_JS.search(f.text):
        return
    child, fs = bool(_JS_CHILD.search(f.text)), bool(_JS_FS.search(f.text))
    starts: list[tuple[int, Tool]] = []
    calls: list[tuple[int, int, set[str]]] = []
    for m in _TOOL_CALL.finditer(f.text):
        name = _group(m, 2) or ""
        tool = Tool(name, f.path, f.line_of(m.start()), art=_CALL_ART[m.group(1)])
        tool.texte.append(Text("name", name, tool.zeile))
        if (desc := _group(m, 5)) is not None:
            tool.texte.append(Text("beschreibung", desc[:MAX_TEXT], tool.zeile))
        starts.append((m.start(), tool))
    for m in _REGISTER.finditer(f.text):
        paren = f.text.index("(", m.start())
        end = _call_end(f.text, paren)
        art = _CALL_ART[m.group(1)]
        if art == "Tool":
            calls.append((m.start(), end, _faehigkeiten_js(f.text[paren:end], child, fs)))
            continue  # its description is found below, next to the input schema
        name = _group(m, 2) or ""
        tool = Tool(name, f.path, f.line_of(m.start()), art=art)
        tool.texte.append(Text("name", name, tool.zeile))
        if d := _DESCRIPTION.search(f.text, m.end(), end):
            tool.texte.append(Text("beschreibung", (_group(d, 1) or "")[:MAX_TEXT], tool.zeile))
        starts.append((m.start(), tool))
    for pos, tool in starts:
        if tool.art == "Tool":
            paren = f.text.index("(", pos)
            end = _call_end(f.text, paren)
            tool.faehigkeiten = _faehigkeiten_js(f.text[paren:end], child, fs)
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
        # The handler: the registerTool call around this object, or the next one after it.
        call = next((c for c in calls if c[0] <= m.start() < c[1]), None) or next(
            (c for c in calls if c[0] > m.start()), None
        )
        if call is not None:
            tool.faehigkeiten = call[2]
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
