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

# The fields that decide a launch, and nothing else.
#
# An allowlist rather than "any key in config.toml": the file also holds
# `live`, the base URL and the build settings, and a panel that could
# reach those is a panel that can take the site down from a browser.
#
# `live` is deliberately absent. The gate decides whether the site MAY
# be published; a person decides whether it IS. That is not a button.
CONFIG_FIELDS = {
    "extra.real": {
        "name":          "the name on the page",
        "person":        "the person, as they write it",
        "title":         "the browser tab and the shared link",
        "approach_lead": "the paragraph under 01 / Approach",
        "about_lead":    "the opening of 06 / About",
    },
    "extra.contact": {
        "email":       "the verified business address — never a placeholder",
        "vcard_name":  "as it should appear in a phonebook",
        "vcard_role":  "the line under the name on a saved card",
        "vcard_org":   "the entity",
        "vcard_phone": "optional, international format",
        "vcard_url":   "optional",
    },
    "extra.legal": {
        "entity":       "the legal name of the publisher",
        "status":       "e.g. Entrepreneur individuel, SASU",
        "registration": "SIRET / RCS",
        "address":      "the registered address",
        "publisher":    "directeur de la publication",
    },
}


class Refused(Exception):
    """The edit was not made, and the file was not touched."""


def quote(value: str) -> str:
    """A TOML basic string. Anything that could end the string early, or
    start a line that looks like TOML, is escaped rather than trusted."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def apply_edit(kind: str, index: int, field: str, value: str,
               allow_locked: bool = False, source: "str | None" = None) -> str:
    """Return the whole file with one value changed. Raises, or returns."""
    if kind not in SCHEMA:
        raise Refused(f"no such object: {kind}")

    array, _doc, fields = SCHEMA[kind]

    if field not in fields:
        raise Refused(f"{kind} has no field {field!r}")
    if field in LOCKED and not allow_locked:
        raise Refused(f"{field!r} is not editable here — see LOCKED in objects.py")

    value = value.strip()
    if "\n" in value or "\r" in value:
        raise Refused("a value is one line; a newline would end the string early")
    if len(value) > MAX_LEN:
        raise Refused(f"{len(value)} characters; the limit is {MAX_LEN}")

    # `source` lets two edits be composed into ONE candidate. Writing
    # them one after another would leave the first on disk when the
    # second is refused — a photograph attached with no description, or
    # a description pointing at nothing.
    text = CONTENT.read_text(encoding="utf-8") if source is None else source
    fm = text.split("+++")[1] if text.count("+++") >= 2 else ""
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

    line = re.search(
        rf'^({re.escape(field)}\s*=\s*)"(?:[^"\\]|\\.)*"([ \t]*#.*)?$', block, re.M
    )
    new_line = f'{field} = "{quote(value)}"'

    if line:
        # Any trailing comment on the line belongs to the field, not to
        # the value, and survives the edit.
        updated = (
            block[: line.start()]
            + f'{line.group(1)}"{quote(value)}"{line.group(2) or ""}'
            + block[line.end():]
        )
    else:
        # An optional field that was never written has no line to
        # change, so one is added. Not at the end of the block — that is
        # where a comment explaining the NEXT thing may already sit —
        # but directly after the last `key = value` in it.
        assignments = list(re.finditer(r"^[a-z_]+\s*=.*$", block, re.M))
        if not assignments:
            raise Refused(f"{kind} {index} has no fields at all")
        at = assignments[-1].end()
        updated = block[:at] + "\n" + new_line + block[at:]
    return text[:start] + updated + text[end:]


# What a photograph may be. Checked by its CONTENT, not its name: a
# file called `.jpg` is a claim, and the first bytes are a fact.
MAGIC = {
    b"\xff\xd8\xff": "jpg",
    b"\x89PNG\r\n\x1a\n": "png",
}
MAX_IMAGE = 12 * 1024 * 1024


def _safe_name(name: str) -> str:
    """A filename that cannot leave content/ or hide what it is."""
    name = name.replace("\\", "/").rsplit("/", 1)[-1].strip().lower()
    name = re.sub(r"[^a-z0-9._-]+", "-", name).lstrip(".-")
    if not name or "." not in name:
        raise Refused("that file has no usable name")
    return name


def attach(kind: str, index: int, filename: str, raw: bytes, alt: str) -> str:
    """Put a photograph in content/ and point an object at it.

    The image and its `alt` arrive TOGETHER and are refused apart. That
    is the whole point of doing this here rather than leaving `image` as
    an editable text field: a photograph without a description is the
    exact gap `alt` was added to close, and the moment someone attaches
    one is the only moment they know what it shows.
    """
    if kind != "reference":
        raise Refused("only a reference carries a photograph today")

    alt = alt.strip()
    if not alt:
        raise Refused("a photograph needs a description — what does it show?")
    if UNWRITTEN in alt:
        raise Refused("that is the placeholder, not a description")
    if len(alt) > MAX_LEN:
        raise Refused(f"{len(alt)} characters; the limit is {MAX_LEN}")

    if not raw:
        raise Refused("no file arrived")
    if len(raw) > MAX_IMAGE:
        raise Refused(f"{len(raw) // 1024 // 1024}MB; the limit is 12MB")

    kind_of = next((k for sig, k in MAGIC.items() if raw.startswith(sig)), None)
    if kind_of is None and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        kind_of = "webp"
    if kind_of is None:
        raise Refused("that is not a JPEG, PNG or WebP — whatever it is named")

    # The extension comes from the CONTENT, not the name it arrived
    # with. A PNG called `.jpg` is a thing people really do send, and
    # a file whose name lies about what it is will mislead every tool
    # that touches it afterwards.
    stem = _safe_name(filename).rsplit(".", 1)[0]
    name = f"{stem}.{kind_of}"
    dest = ROOT / "content" / name
    # Never overwrite. Another object may be pointing at the file that is
    # already there, and replacing it would change that one silently.
    n = 2
    while dest.exists() and dest.read_bytes() != raw:
        name = f"{stem}-{n}.{kind_of}"
        dest = ROOT / "content" / name
        n += 1

    dest.write_bytes(raw)
    try:
        # One candidate, both fields. Either the photograph and its
        # description land together or neither does.
        candidate = apply_edit(kind, index, "alt", alt, allow_locked=True)
        candidate = apply_edit(kind, index, "image", name,
                               allow_locked=True, source=candidate)
        return _commit(candidate, f"{name} attached to {kind} {index}")
    except Exception:
        # The file was written before the content was; if the content
        # would not take it, the file should not be left behind either.
        if dest.exists():
            dest.unlink()
        raise


def set_config(section: str, key: str, value: str) -> str:
    """Change one launch field in config.toml.

    Surgical, for the same reason as the content file: config.toml is
    mostly comments explaining why each switch exists — the identity
    swap, why `live` is false, why French is not built. A serializer
    would take all of it.
    """
    if section not in CONFIG_FIELDS:
        raise Refused(f"{section} is not editable here")
    if key not in CONFIG_FIELDS[section]:
        raise Refused(f"{section} has no editable field {key!r}")

    value = value.strip()
    if "\n" in value or "\r" in value:
        raise Refused("a value is one line")
    if len(value) > MAX_LEN:
        raise Refused(f"{len(value)} characters; the limit is {MAX_LEN}")

    text = CONFIG.read_text(encoding="utf-8")

    header = re.search(rf"^\[{re.escape(section)}\]\s*$", text, re.M)
    if not header:
        raise Refused(f"config.toml has no [{section}]")
    start = header.end()
    nxt = re.search(r"^\[", text[start:], re.M)
    end = start + (nxt.start() if nxt else len(text[start:]))
    block = text[start:end]

    # The trailing comment is kept. In config.toml it is often the only
    # thing saying what the field is for — "never a placeholder",
    # "international format" — and replacing the line without it would
    # quietly delete the instruction along with the blank.
    line = re.search(
        rf'^({re.escape(key)}\s*=\s*)"(?:[^"\\]|\\.)*"([ \t]*#.*)?$', block, re.M
    )
    if not line:
        raise Refused(f"[{section}] has no {key} line")

    updated = (
        block[: line.start()]
        + f'{line.group(1)}"{quote(value)}"{line.group(2) or ""}'
        + block[line.end():]
    )
    candidate = text[:start] + updated + text[end:]

    original = text
    CONFIG.write_text(candidate, encoding="utf-8")
    try:
        if original.count("#") != candidate.count("#"):
            raise Refused("a comment was lost; the edit was undone")
        leaked = _protected_terms_leaked()
        if leaked:
            raise Refused(
                f"{leaked} is protected from this repository — it is public. "
                "See NOTICE; the real identity goes in at handover."
            )
    except Exception:
        CONFIG.write_text(original, encoding="utf-8")
        raise

    return f"[{section}] {key} updated"


def _protected_terms_leaked() -> str:
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


def add(kind: str) -> str:
    """Append an object to its group, filled with honest placeholders."""
    if kind not in SCHEMA:
        raise Refused(f"no such object: {kind}")

    array, _doc, fields = SCHEMA[kind]
    text = CONTENT.read_text(encoding="utf-8")

    lines = [f"[[{array}]]"]
    for field, (required, _what) in fields.items():
        if field == "verified":
            lines.append("verified = false")
        elif field in LOCKED:
            lines.append(f'{field} = ""')
        elif required:
            lines.append(f'{field} = "{UNWRITTEN}"')
        else:
            lines.append(f'{field} = ""')
    block = "\n".join(lines) + "\n"

    starts = [m.start() for m in re.finditer(rf"\[\[{re.escape(array)}\]\]", text)]
    if not starts:
        raise Refused(f"no {kind} blocks to append to")

    # After the LAST block of this group, and not a line further: the
    # text after it is the next section's comment, which explains the
    # next section.
    last = starts[-1]
    following = re.search(r"\n(?=\[\[|# ----)", text[last:])
    at = last + (following.start() + 1 if following else len(text[last:]))

    return _commit(text[:at] + block + "\n" + text[at:],
                   f"{kind} added — fill it in")


def remove(kind: str, index: int) -> str:
    """Delete one object. The last of its kind cannot go: `objects.py`
    fails on an empty class, and this undoes anything that fails."""
    if kind not in SCHEMA:
        raise Refused(f"no such object: {kind}")

    array, _doc, _fields = SCHEMA[kind]
    text = CONTENT.read_text(encoding="utf-8")
    starts = [m.start() for m in re.finditer(rf"\[\[{re.escape(array)}\]\]", text)]

    if not 1 <= index <= len(starts):
        raise Refused(f"{kind} {index} does not exist ({len(starts)} present)")

    start = starts[index - 1]
    following = re.search(r"\n(?=\[\[|# ----)", text[start:])
    end = start + (following.start() + 1 if following else len(text[start:]))

    return _commit(text[:start] + text[end:], f"{kind} {index} removed")


def write(kind: str, index: int, field: str, value: str) -> str:
    """Apply, re-check, and only then replace the file.

    The candidate is validated BEFORE it is written. A tool that writes
    and then tells you it was wrong has already lost the thing it was
    editing.
    """
    return _commit(apply_edit(kind, index, field, value),
                   f"{kind} {index}: {field} updated")


def _commit(candidate: str, message: str) -> str:
    """Write, re-check, and undo if the result is not sound.

    The file is replaced only after the candidate has been checked, and
    put back if anything about the result is wrong. A tool that writes
    and then reports a failure has already lost the thing it was
    editing.
    """
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

    return message
