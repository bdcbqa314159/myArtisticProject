#!/usr/bin/env python3
"""Writing one value into a file without disturbing it.

The content file and `config.toml` are edited BY HAND — find the block,
find the line, replace the value — rather than parsed and written back.

That is not a shortcut, it is the requirement. Both files carry the
comments that hold the reasoning: the voice ruling, why `verified`
needs a date and evidence, why the client's trademark is absent from
every tracked file, why `live` is false. **A serializer deletes all of
them**, in any language, as a matter of course. A surgical edit cannot:
it never sees them.

This module is the surgery and knows nothing about what is being
written. The verbs that do are its neighbours: `words`, `launch`,
`blocks`, `drops`.

THE PATHS LIVE HERE, AND ONLY HERE. `tools/studio/check.py` points them
at a temporary copy so that nothing it does can touch the real content
file — which only works while there is one place to point.
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import sys
from pathlib import Path

# tools/studio/edit/surgery.py — four parents to the repository, not
# three. The file moved a level deeper into a package, and three put
# ROOT at `tools/`, which reads as a missing content file.
ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import markers                                              # noqa: E402
import objects                                              # noqa: E402


CONTENT = ROOT / "content" / "_index.md"


MAX_LEN = 600


# What a new object is filled with.
#
# It cannot be blank: `tools/objects.py` fails on an empty required
# field, and `write()` undoes anything that fails — so a new object made
# of nothing could never be saved at all.
#
# So it is filled with text that SAYS it is unfinished, and
# `tools/content-check.py` refuses to publish while any of it survives.
# The alternative — relaxing the checker for new objects — would mean
# the one tool that knows what a complete object looks like stops
# knowing it at the exact moment one is created.
UNWRITTEN = "To be written"


CONFIG = ROOT / "config.toml"


class Refused(Exception):
    """The edit was not made, and the file was not touched."""


# Anything that cannot appear in a TOML basic string. Newlines are
# already refused by each caller with a clearer message; this catches
# the rest — a bell, a vertical tab, a DEL, the invisible things that
# arrive with text pasted out of a word processor.
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def plain(value: str, what: str = "that text") -> str:
    """Refuse what would produce a file the site cannot build.

    `quote()` escapes the two characters that could END a string early.
    It does not make a string VALID, and a control character in the
    middle of one is invalid TOML — which the panel happily wrote until
    this existed. The result passed `objects.check()`, because that is a
    regular expression over lines and not a parser, and then `zola
    build` refused the site.

    A tool with a GUI must not be able to produce a file that does not
    load. That is the whole difference between an editor and a hazard.
    """
    found = CONTROL.search(value)
    if found:
        raise Refused(
            f"{what} contains a character that cannot be written here "
            f"(code {ord(found.group(0))}) — it is usually invisible, and "
            "arrives with text pasted out of another application"
        )
    # THE FENCE. `+++` is what separates the front matter from the body,
    # and every reader of this file — four of them, in two languages —
    # finds it by splitting on exactly that. A value containing one cuts
    # the front matter in half: the write was already undone by
    # `commit`, but the complaint that came back said the references had
    # all vanished, which is the symptom and not the cause.
    # WHAT MAY BE WRITTEN AT ALL. One rule, in `tools/markers.py`, so
    # the panel and the launch gate cannot drift apart about it: no
    # angle brackets, and `((two faces))` marked in pairs. The template
    # turns those markers into a span, which is only safe because
    # nothing else here can be markup.
    said = markers.trouble(value, what)
    if said:
        raise Refused(said)

    if "+++" in value:
        raise Refused(
            f"{what} contains +++, which is the fence between the front "
            "matter and the page. Three plus signs in a row cannot be "
            "written into a value; two can"
        )
    return value


def quote(value: str) -> str:
    """A TOML basic string. Anything that could end the string early, or
    start a line that looks like TOML, is escaped rather than trusted."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def write_front_field(key: str, value: str) -> str:
    """Rewrite one `key = "value"` line in the front matter.

    The surgery, without the gate. `set_text` guards which keys a
    browser may reach before calling this; the other callers are
    `attach_showreel` and `remove_showreel`, which pass constants of
    their own and never anything a visitor typed — including the empty
    string, which `set_text` refuses and removal requires.
    """
    text = CONTENT.read_text(encoding="utf-8")
    parts = text.split("+++")
    if len(parts) < 3:
        raise Refused("content/_index.md has no front matter")

    fm = parts[1]
    # Only before the first [[array]]: the same name can appear inside an
    # object, and writing the heading into a reference would be a quiet
    # disaster to find.
    cut = fm.find("\n[[")
    head = fm if cut < 0 else fm[:cut]
    tail = "" if cut < 0 else fm[cut:]

    line = re.search(rf'^({re.escape(key)}\s*=\s*)"(?:[^"\\]|\\.)*"([ \t]*#.*)?$',
                     head, re.M)
    if not line:
        raise Refused(f"content/_index.md has no {key} line")

    head = (head[: line.start()]
            + f'{line.group(1)}"{quote(value)}"{line.group(2) or ""}'
            + head[line.end():])

    return commit("+++".join([parts[0], head + tail] + parts[2:]),
                   f"{key} updated")


def put(path: Path, text: str) -> None:
    """Replace a file's contents in one step.

    `write_text` truncates and then writes, so a process that dies in
    between leaves nothing at all — and this is the client's page. A
    temporary file beside it and a rename is atomic on this filesystem:
    either the old contents or the new, never half of either.
    """
    tmp = path.with_name(path.name + ".writing")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def comments(text: str) -> int:
    """How many comments config.toml has.

    Counting `#` characters was close enough while every value was
    prose — and then the theme arrived, where a value IS a `#`. Writing
    `bg = "#f8f4ea"` raised the count and the guard read that as the
    file having changed shape, so it undid every colour anyone set.

    Quoted strings are taken out first, so what is counted is comments
    and not content. The guard it serves is unchanged: a write may
    leave the number the same or raise it, never lower it.
    """
    return re.sub(r'"(?:[^"\\]|\\.)*"', "", text).count("#")


def protected_terms_leaked() -> str:
    """The client's trademark must not reach a tracked file. The terms
    live in _ref/identifiers.txt, which is untracked — a list that named
    what it guards would be the leak it prevents."""
    ids = ROOT / "_ref" / "identifiers.txt"
    if not ids.exists():
        return ""
    terms = [t.strip() for t in ids.read_text(encoding="utf-8").splitlines()
             if t.strip() and not t.startswith("#")]
    body = CONFIG.read_text(encoding="utf-8").lower()
    return next((repr(t) for t in terms if t.lower() in body), "")


def front(text: str) -> "tuple[str, str, str]":
    parts = text.split("+++")
    if len(parts) < 3:
        raise Refused("content/_index.md has no front matter")
    return parts[0], parts[1], "+++".join([""] + parts[2:])[0:]


def insert_at(fm: str, array: str) -> int:
    """Where a new block of this kind goes.

    After the last one of its own kind if there are any — and if there
    are none, before the next section's comment rather than at the end
    of the file, so the first project does not land in the middle of the
    concepts.
    """
    starts = [m.start() for m in re.finditer(rf"\[\[{re.escape(array)}\]\]", fm)]
    if starts:
        last = starts[-1]
        following = re.search(r"\n(?=\[\[|# ----)", fm[last:])
        return last + (following.start() + 1 if following else len(fm[last:]))
    mark = fm.find("# ---- 04 original concepts")
    return mark if mark >= 0 else len(fm)


def block_span(fm: str, array: str, which: int) -> "tuple[int, int]":
    starts = [m.start() for m in re.finditer(rf"\[\[{re.escape(array)}\]\]", fm)]
    if which >= len(starts):
        raise Refused("that one is not there")
    begin = starts[which]
    following = re.search(r"\n(?=\[\[|# ----)", fm[begin:])
    end = begin + (following.start() + 1 if following else len(fm[begin:]))
    return begin, end


def refusal(printed: str) -> str:
    """What to tell the person, out of what the checker printed."""
    for line in printed.splitlines():
        said = line.strip()
        if said.startswith("- "):
            return f"the result would not pass tools/objects.py: {said[2:]}"
    return "the result would not pass tools/objects.py"


def commit(candidate: str, message: str) -> str:
    """Write, re-check, and undo if the result is not sound.

    The file is replaced only after the candidate has been checked, and
    put back if anything about the result is wrong. A tool that writes
    and then reports a failure has already lost the thing it was
    editing.
    """
    original = CONTENT.read_text(encoding="utf-8")
    put(CONTENT, candidate)
    try:
        import objects

        # THE CHECKER ALREADY KNOWS WHY. It prints its complaints and
        # returns a count, and this used to keep the count and throw the
        # complaints away — so a person who typed `+++` into a sentence,
        # which truncates the front matter at its own fence, was told
        # only that "the result would not pass tools/objects.py". True,
        # unactionable, and the one thing they needed was on stdout.
        said = io.StringIO()
        with contextlib.redirect_stdout(said):
            sound = objects.check() == 0
        if not sound:
            raise Refused(refusal(said.getvalue()))
    except Exception:
        put(CONTENT, original)
        raise

    # The comments are the reason this is a surgical edit. Prove it.
    #
    # COUNTED WITH THE VALUES TAKEN OUT. This compared raw `#` counts
    # and asked for them to be EQUAL, which was fine while no value
    # could contain one — and then the form's replies became editable
    # and a message like "Dis-le en mots #1" raised the count. The edit
    # was undone and the person was told a comment had been lost, which
    # was neither true nor anything they could act on.
    if comments(candidate) < comments(original):
        put(CONTENT, original)
        raise Refused("a comment was lost; the edit was undone")

    return message
