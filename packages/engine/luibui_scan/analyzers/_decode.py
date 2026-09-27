"""Decoding hidden text for Ebene B: Base64, Hex, gzip inside Base64, several layers deep.

Only data is decoded; nothing is executed or unpickled. Every step has a size limit, so a small
block cannot expand into a large one (gzip bomb).
"""

import base64
import binascii
import re
import zlib
from dataclasses import dataclass

BASE64 = re.compile(r"(?<![A-Za-z0-9+/=_-])[A-Za-z0-9+/]{120,}={0,2}(?![A-Za-z0-9+/=])")
HEX = re.compile(r"(?<![0-9A-Fa-f])(?:[0-9A-Fa-f]{2}){80,}(?![0-9A-Fa-f])")
_SHORT_BASE64 = re.compile(r"^[A-Za-z0-9+/\s]{24,}={0,2}\s*$")
MAX_DEPTH = 3
MAX_DECODED = 64 * 1024


@dataclass(frozen=True, slots=True)
class Decoded:
    offset: int
    """Position of the outer block in the file."""
    art: str
    """How it was encoded, e.g. ``Base64`` or ``gzip+Base64 → Base64``."""
    text: str


def printable_ratio(data: bytes) -> float:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return 0.0
    return sum(c.isprintable() or c in "\n\t" for c in text) / max(len(text), 1)


def _b64(raw: str) -> bytes | None:
    try:
        return base64.b64decode(re.sub(r"\s+", "", raw) + "=" * (-len(raw.strip()) % 4))
    except (binascii.Error, ValueError):
        return None


def _gunzip(data: bytes) -> bytes | None:
    if not data.startswith(b"\x1f\x8b"):
        return None
    try:
        d = zlib.decompressobj(16 + zlib.MAX_WBITS)
        out = d.decompress(data, MAX_DECODED)
    except zlib.error:
        return None
    return out


def _layers(data: bytes, art: str, depth: int) -> tuple[str, bytes] | None:
    """Follow gzip and further Base64 layers; return the innermost readable text."""
    unzipped = _gunzip(data)
    if unzipped is not None:
        data, art = unzipped, f"gzip+{art}"
    if printable_ratio(data[:MAX_DECODED]) < 0.9:
        return None
    text = data[:MAX_DECODED].decode("utf-8", errors="replace")
    if depth < MAX_DEPTH and _SHORT_BASE64.match(text):
        inner = _b64(text)
        if inner is not None:
            deeper = _layers(inner, "Base64", depth + 1)
            if deeper is not None:
                return f"{art} → {deeper[0]}", deeper[1]
    return art, data[:MAX_DECODED]


def decode_blocks(text: str, *, skip_data_urls: bool = True) -> list[Decoded]:
    """Every Base64 or Hex block of the text that decodes to readable text."""
    found: list[Decoded] = []
    for m in BASE64.finditer(text):
        if skip_data_urls and text[max(0, m.start() - 40) : m.start()].rstrip().endswith("base64,"):
            continue  # data: URL (images, fonts)
        raw = _b64(m.group())
        result = _layers(raw, "Base64", 1) if raw is not None else None
        if result is not None:
            found.append(Decoded(m.start(), result[0], result[1].decode("utf-8", "replace")))
    for m in HEX.finditer(text):
        result = _layers(bytes.fromhex(m.group()), "Hex", 1)
        if result is not None:
            found.append(Decoded(m.start(), result[0], result[1].decode("utf-8", "replace")))
    return found


TAGS = re.compile("[\U000e0000-\U000e007f]+")


def tag_text(text: str) -> str:
    """The ASCII text hidden in Unicode tag characters (U+E0020–U+E007E)."""
    return "".join(
        chr(ord(c) - 0xE0000)
        for m in TAGS.finditer(text)
        for c in m.group()
        if 0x20 <= ord(c) - 0xE0000 < 0x7F
    )
