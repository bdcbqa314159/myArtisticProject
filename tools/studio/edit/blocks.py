#!/usr/bin/env python3
"""Objects: adding one, removing one, changing a field of one.

A reference, a capability, a concept, a project, a pillar — each is a
`[[extra.*]]` block in the content file's front matter. Every write
goes through `commit`, which runs the object checker over the result
and undoes the edit if it refuses: the file is never left in a state
the build would reject.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from objects import LOCKED, SCHEMA, blocks

from . import surgery as s


def apply_edit(kind: str, index: int, field: str, value: str,
               allow_locked: bool = False, source: "str | None" = None) -> str:
    """Return the whole file with one value changed. Raises, or returns."""
    if kind not in SCHEMA:
        raise s.Refused(f"no such object: {kind}")

    array, _doc, fields = SCHEMA[kind]

    if field not in fields:
        raise s.Refused(f"{kind} has no field {field!r}")
    if field in LOCKED and not allow_locked:
        raise s.Refused(f"{field!r} is not editable here — see LOCKED in objects.py")

    value = value.strip()
    if "\n" in value or "\r" in value:
        raise s.Refused("a value is one line; a newline would end the string early")
    if len(value) > s.MAX_LEN:
        raise s.Refused(f"{len(value)} characters; the limit is {s.MAX_LEN}")
    s.plain(value)

    # `source` lets two edits be composed into ONE candidate. Writing
    # them one after another would leave the first on disk when the
    # second is refused — a photograph attached with no description, or
    # a description pointing at nothing.
    text = s.CONTENT.read_text(encoding="utf-8") if source is None else source
    fm = text.split("+++")[1] if text.count("+++") >= 2 else ""
    found = blocks(fm, array)
    if not 1 <= index <= len(found):
        raise s.Refused(f"{kind} {index} does not exist ({len(found)} present)")

    # Walk to the right block in the real text, not in a copy of it: the
    # edit has to land at a known offset, and a reconstructed string
    # would lose exactly the s.comments this is protecting.
    starts = [m.start() for m in re.finditer(rf"\[\[{re.escape(array)}\]\]", text)]
    if len(starts) != len(found):
        raise s.Refused("the file on disk is not what was parsed; nothing written")

    start = starts[index - 1]
    end = starts[index] if index < len(starts) else len(text)
    block = text[start:end]

    line = re.search(
        rf'^({re.escape(field)}\s*=\s*)"(?:[^"\\]|\\.)*"([ \t]*#.*)?$', block, re.M
    )
    new_line = f'{field} = "{s.quote(value)}"'

    if line:
        # Any trailing comment on the line belongs to the field, not to
        # the value, and survives the edit.
        updated = (
            block[: line.start()]
            + f'{line.group(1)}"{s.quote(value)}"{line.group(2) or ""}'
            + block[line.end():]
        )
    else:
        # An optional field that was never written has no line to
        # change, so one is added. Not at the end of the block — that is
        # where a comment explaining the NEXT thing may already sit —
        # but directly after the last `key = value` in it.
        assignments = list(re.finditer(r"^[a-z_]+\s*=.*$", block, re.M))
        if not assignments:
            raise s.Refused(f"{kind} {index} has no fields at all")
        at = assignments[-1].end()
        updated = block[:at] + "\n" + new_line + block[at:]
    return text[:start] + updated + text[end:]


def add(kind: str) -> str:
    """Append an object to its group, filled with honest placeholders."""
    if kind not in SCHEMA:
        raise s.Refused(f"no such object: {kind}")

    array, _doc, fields = SCHEMA[kind]
    text = s.CONTENT.read_text(encoding="utf-8")

    lines = [f"[[{array}]]"]
    for field, (required, _what) in fields.items():
        if field == "verified":
            lines.append("verified = false")
        elif field in LOCKED:
            lines.append(f'{field} = ""')
        elif required:
            lines.append(f'{field} = "{s.UNWRITTEN}"')
        else:
            lines.append(f'{field} = ""')
    block = "\n".join(lines) + "\n"

    starts = [m.start() for m in re.finditer(rf"\[\[{re.escape(array)}\]\]", text)]
    if not starts:
        raise s.Refused(f"no {kind} blocks to append to")

    # After the LAST block of this group, and not a line further: the
    # text after it is the next section's comment, which explains the
    # next section.
    last = starts[-1]
    following = re.search(r"\n(?=\[\[|# ----)", text[last:])
    at = last + (following.start() + 1 if following else len(text[last:]))

    return s.commit(text[:at] + block + "\n" + text[at:],
                   f"{kind} added — fill it in")


def write(kind: str, index: int, field: str, value: str) -> str:
    """Apply, re-check, and only then replace the file.

    The candidate is validated BEFORE it is written. A tool that writes
    and then tells you it was wrong has already lost the thing it was
    editing.
    """
    return s.commit(apply_edit(kind, index, field, value),
                   f"{kind} {index}: {field} updated")


def remove(kind: str, index: int) -> str:
    """Delete one object. The last of its kind cannot go: `objects.py`
    fails on an empty class, and this undoes anything that fails."""
    if kind not in SCHEMA:
        raise s.Refused(f"no such object: {kind}")

    array, _doc, _fields = SCHEMA[kind]
    text = s.CONTENT.read_text(encoding="utf-8")
    starts = [m.start() for m in re.finditer(rf"\[\[{re.escape(array)}\]\]", text)]

    if not 1 <= index <= len(starts):
        raise s.Refused(f"{kind} {index} does not exist ({len(starts)} present)")

    start = starts[index - 1]
    following = re.search(r"\n(?=\[\[|# ----)", text[start:])
    end = start + (following.start() + 1 if following else len(text[start:]))

    return s.commit(text[:start] + text[end:], f"{kind} {index} removed")


def _projects(fm: str) -> "list[dict]":
    return blocks(fm, "extra.project")


def add_project(reference: int) -> str:
    """A new project on one of the references.

    Not `add()`: that fills every required field with "To be written",
    which for a project means an `id` that is not unique the second time
    and a `reference` that is not a number. The result would be refused
    by the checker and undone — an add button that never adds.
    """
    _, fm, _ = s.front(s.CONTENT.read_text(encoding="utf-8"))
    if not 1 <= reference <= len(blocks(fm, "extra.work")):
        raise s.Refused(f"there is no reference {reference}")

    # FIVE, and say so. The checker refuses a sixth too, but by then
    # the message is "the result would not pass tools/objects.py" —
    # which tells someone who pressed a button in a browser nothing at
    # all about what they did or what to do instead.
    here = [p for p in _projects(fm) if p.get("reference", "") == str(reference)]
    if len(here) >= 5:
        raise s.Refused(
            f"reference {reference} already has five projects, which is what "
            "a patchwork shows — remove one before adding another"
        )

    taken = {p.get("id", "") for p in _projects(fm)}
    letters = "abcdefghijklmnop"
    new_id = next((f"r{reference}-{c}" for c in letters
                   if f"r{reference}-{c}" not in taken), "")
    if not new_id:
        raise s.Refused("that reference already has as many projects as this adds")

    block = (f"[[extra.project]]\n"
             f'id = "{new_id}"\n'
             f"reference = {reference}\n"
             f'name = "{s.UNWRITTEN}"\n')

    text = s.CONTENT.read_text(encoding="utf-8")
    head, fm, tail = s.front(text)
    at = s.insert_at(fm, "extra.project")
    fm = fm[:at] + block + "\n" + fm[at:]
    return s.commit(head + "+++" + fm + tail, f"project {new_id} added — name it")


def remove_project(project_id: str) -> str:
    """A project, and every photograph that belonged to it.

    Both or neither. Removing the project alone leaves its photographs
    naming something that is gone — which the checker refuses, so the
    edit would be undone and the button would appear broken rather than
    forbidden.
    """
    text = s.CONTENT.read_text(encoding="utf-8")
    head, fm, tail = s.front(text)

    where = [i for i, p in enumerate(_projects(fm)) if p.get("id") == project_id]
    if not where:
        raise s.Refused(f"no project has the id {project_id!r}")

    # Photographs first: removing them shifts no project index.
    shots = blocks(fm, "extra.photo")
    gone = 0
    for i in range(len(shots) - 1, -1, -1):
        if shots[i].get("project") == project_id:
            begin, end = s.block_span(fm, "extra.photo", i)
            fm = fm[:begin] + fm[end:]
            gone += 1

    begin, end = s.block_span(fm, "extra.project", where[0])
    fm = fm[:begin] + fm[end:]

    return s.commit(head + "+++" + fm + tail,
                   f"{project_id} removed, with {gone} photograph(s)")
