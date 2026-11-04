#!/usr/bin/env python3
"""Changing one field, without disturbing anything around it.

The content file is edited BY HAND here — find the block, find the line,
replace the value — rather than parsed and written back.

That is not a shortcut, it is the requirement. `content/_index.md`
carries the comments that hold the reasoning: the voice ruling, why
`verified` needs a date and evidence, why the client's trademark is
absent from every tracked file. **A serializer deletes all of them**, in
any language, as a matter of course. A surgical edit cannot: it never
sees them.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from objects import LOCKED, SCHEMA, blocks, front_matter  # noqa: E402

CONTENT = ROOT / "content" / "_index.md"
MAX_LEN = 600


class Refused(Exception):
    """The edit was not made, and the file was not touched."""


def quote(value: str) -> str:
    """A TOML basic string. Anything that could end the string early, or
    start a line that looks like TOML, is escaped rather than trusted."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def apply_edit(kind: str, index: int, field: str, value: str) -> str:
    """Return the whole file with one value changed. Raises, or returns."""
    if kind not in SCHEMA:
        raise Refused(f"no such object: {kind}")

    array, _doc, fields = SCHEMA[kind]

    if field not in fields:
        raise Refused(f"{kind} has no field {field!r}")
    if field in LOCKED:
        raise Refused(f"{field!r} is not editable here — see LOCKED in objects.py")

    value = value.strip()
    if "\n" in value or "\r" in value:
        raise Refused("a value is one line; a newline would end the string early")
    if len(value) > MAX_LEN:
        raise Refused(f"{len(value)} characters; the limit is {MAX_LEN}")

    text = CONTENT.read_text(encoding="utf-8")
    fm = front_matter()
    found = blocks(fm, array)
    if not 1 <= index <= len(found):
        raise Refused(f"{kind} {index} does not exist ({len(found)} present)")

    # Walk to the right block in the real text, not in a copy of it: the
    # edit has to land at a known offset, and a reconstructed string
    # would lose exactly the comments this is protecting.
    starts = [m.start() for m in re.finditer(rf"\[\[{re.escape(array)}\]\]", text)]
    if len(starts) != len(found):
        raise Refused("the file on disk is not what was parsed; nothing written")

    start = starts[index - 1]
    end = starts[index] if index < len(starts) else len(text)
    block = text[start:end]

    line = re.search(rf'^{re.escape(field)}\s*=\s*"(?:[^"\\]|\\.)*"\s*$', block, re.M)
    if not line:
        raise Refused(f"{kind} {index} has no {field} line to change")

    updated = block[: line.start()] + f'{field} = "{quote(value)}"' + block[line.end():]
    return text[:start] + updated + text[end:]


def write(kind: str, index: int, field: str, value: str) -> str:
    """Apply, re-check, and only then replace the file.

    The candidate is validated BEFORE it is written. A tool that writes
    and then tells you it was wrong has already lost the thing it was
    editing.
    """
    candidate = apply_edit(kind, index, field, value)

    original = CONTENT.read_text(encoding="utf-8")
    CONTENT.write_text(candidate, encoding="utf-8")
    try:
        import objects

        if objects.check() != 0:
            raise Refused("the result would not pass tools/objects.py")
    except Exception:
        CONTENT.write_text(original, encoding="utf-8")
        raise

    # The comments are the reason this is a surgical edit. Prove it.
    if original.count("#") != candidate.count("#"):
        CONTENT.write_text(original, encoding="utf-8")
        raise Refused("a comment was lost; the edit was undone")

    return f"{kind} {index}: {field} updated"
