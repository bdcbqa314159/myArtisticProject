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
    # Only `url`. The mark filename and the service's name are the
    # studio's, and a mark pointing at a file that is not there is a
    # broken image in the footer — not a thing to expose to a browser.
    "extra.social.linkedin": {
        "url": "his LinkedIn profile, not linkedin.com",
    },
    "extra.social.whatsapp": {
        "url": "https://wa.me/ and the business number",
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
    return value


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
    plain(value)

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
    plain(alt, "that description")

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


# The page's own words — the titles and leads in content/_index.md's
# [extra] block. An allowlist rather than "any key in the file", for the
# same reason CONFIG_FIELDS is one: that block also holds `video`,
# `poster`, `nav` and `ecosystem_fields`, and a panel that could reach
# those is a panel that can point the page at a film that is not there
# or empty the navigation.
#
# Nothing wrote these before. The panel could edit objects and the
# launch fields and not one of the sentences a visitor actually reads,
# which is most of why it felt like a form rather than the site.
TEXT_FIELDS = {
    "eyebrow":          "the line above the name",
    "roles":            "the lead under the name",
    "intro":            "the paragraph under that",
    "cta_work":         "the first button",
    "cta_contact":      "the second button",
    "approach_title":   "the heading of 01 / Approach",
    "showreel_label":   "the word on the empty showreel slot",
    "showreel_spec":    "the line under it",
    "services_title":   "the heading of 02 / Expertise",
    "work_title":       "the heading of 03 / Selected Work",
    "work_lead":        "the paragraph under it",
    "work_note":        "the note under the references",
    "concepts_title":   "the heading of 04 / Concepts",
    "concepts_lead":    "the paragraph under it",
    "ecosystem_lead":   "the paragraph in 05 / Ecosystem",
    "about_title":      "the heading of 06 / About",
    "about_text":       "the second paragraph of About",
    "contact_title":    "the heading of 07 / Contact",
    "contact_lead":     "the paragraph under it",
    "form_title":       "the heading inside the form",
    "form_lead":        "the line under it",
    "form_mail":        "the label on the address field",
    "form_subject":     "the label on the subject field",
    "form_message":     "the label on the message field",
    "form_send":        "the button that sends",
    "form_cancel":      "the button that does not",
    "form_privacy":     "what happens to a message, in one sentence",
}


def set_text(key: str, value: str) -> str:
    """One of the page's own sentences, in content/_index.md.

    Surgical, like every other writer here: the file is mostly comments
    explaining why each decision was made — the voice rule, the ordering
    of the references — and a serialiser would take all of them.
    """
    if key not in TEXT_FIELDS:
        raise Refused(f"{key!r} is not editable here")

    value = value.strip()
    if "\n" in value or "\r" in value:
        raise Refused("a value is one line")
    if len(value) > MAX_LEN:
        raise Refused(f"{len(value)} characters; the limit is {MAX_LEN}")
    plain(value)
    if not value:
        raise Refused("that would leave it empty — remove the field instead")

    leak = _protected_terms_leaked()
    if leak:
        raise Refused(leak)

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

    return _commit("+++".join([parts[0], head + tail] + parts[2:]),
                   f"{key} updated")


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
    plain(value)

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


def _front(text: str) -> "tuple[str, str, str]":
    parts = text.split("+++")
    if len(parts) < 3:
        raise Refused("content/_index.md has no front matter")
    return parts[0], parts[1], "+++".join([""] + parts[2:])[0:]


def _insert_at(fm: str, array: str) -> int:
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


def _projects(fm: str) -> "list[dict]":
    return blocks(fm, "extra.project")


def add_project(reference: int) -> str:
    """A new project on one of the references.

    Not `add()`: that fills every required field with "To be written",
    which for a project means an `id` that is not unique the second time
    and a `reference` that is not a number. The result would be refused
    by the checker and undone — an add button that never adds.
    """
    _, fm, _ = _front(CONTENT.read_text(encoding="utf-8"))
    if not 1 <= reference <= len(blocks(fm, "extra.work")):
        raise Refused(f"there is no reference {reference}")

    # FIVE, and say so. The checker refuses a sixth too, but by then
    # the message is "the result would not pass tools/objects.py" —
    # which tells someone who pressed a button in a browser nothing at
    # all about what they did or what to do instead.
    here = [p for p in _projects(fm) if p.get("reference", "") == str(reference)]
    if len(here) >= 5:
        raise Refused(
            f"reference {reference} already has five projects, which is what "
            "a patchwork shows — remove one before adding another"
        )

    taken = {p.get("id", "") for p in _projects(fm)}
    letters = "abcdefghijklmnop"
    new_id = next((f"r{reference}-{c}" for c in letters
                   if f"r{reference}-{c}" not in taken), "")
    if not new_id:
        raise Refused("that reference already has as many projects as this adds")

    block = (f"[[extra.project]]\n"
             f'id = "{new_id}"\n'
             f"reference = {reference}\n"
             f'name = "{UNWRITTEN}"\n')

    text = CONTENT.read_text(encoding="utf-8")
    head, fm, tail = _front(text)
    at = _insert_at(fm, "extra.project")
    fm = fm[:at] + block + "\n" + fm[at:]
    return _commit(head + "+++" + fm + tail, f"project {new_id} added — name it")


def _block_span(fm: str, array: str, which: int) -> "tuple[int, int]":
    starts = [m.start() for m in re.finditer(rf"\[\[{re.escape(array)}\]\]", fm)]
    if which >= len(starts):
        raise Refused("that one is not there")
    begin = starts[which]
    following = re.search(r"\n(?=\[\[|# ----)", fm[begin:])
    end = begin + (following.start() + 1 if following else len(fm[begin:]))
    return begin, end


def remove_project(project_id: str) -> str:
    """A project, and every photograph that belonged to it.

    Both or neither. Removing the project alone leaves its photographs
    naming something that is gone — which the checker refuses, so the
    edit would be undone and the button would appear broken rather than
    forbidden.
    """
    text = CONTENT.read_text(encoding="utf-8")
    head, fm, tail = _front(text)

    where = [i for i, p in enumerate(_projects(fm)) if p.get("id") == project_id]
    if not where:
        raise Refused(f"no project has the id {project_id!r}")

    # Photographs first: removing them shifts no project index.
    shots = blocks(fm, "extra.photo")
    gone = 0
    for i in range(len(shots) - 1, -1, -1):
        if shots[i].get("project") == project_id:
            begin, end = _block_span(fm, "extra.photo", i)
            fm = fm[:begin] + fm[end:]
            gone += 1

    begin, end = _block_span(fm, "extra.project", where[0])
    fm = fm[:begin] + fm[end:]

    return _commit(head + "+++" + fm + tail,
                   f"{project_id} removed, with {gone} photograph(s)")


def attach_photo(project_id: str, filename: str, raw: bytes, alt: str) -> str:
    """A photograph into a project's reel.

    Unlike a reference's single image, this is a new OBJECT rather than
    a field — so it appends rather than replaces, and a project's reel
    grows by dropping one more on it.

    Everything that guards `attach()` guards this: the description is
    required and arrives with the file, the type comes from the content
    and not from the name, and nothing is ever overwritten.
    """
    alt = plain(alt.strip(), "that description")
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

    _, fm, _ = _front(CONTENT.read_text(encoding="utf-8"))
    if not any(p.get("id") == project_id for p in _projects(fm)):
        raise Refused(f"no project has the id {project_id!r}")

    stem = _safe_name(filename).rsplit(".", 1)[0] or project_id
    name = f"{stem}.{kind_of}"
    dest = ROOT / "content" / name
    n = 2
    while dest.exists() and dest.read_bytes() != raw:
        name = f"{stem}-{n}.{kind_of}"
        dest = ROOT / "content" / name
        n += 1
    dest.write_bytes(raw)

    try:
        text = CONTENT.read_text(encoding="utf-8")
        head, fm, tail = _front(text)
        at = _insert_at(fm, "extra.photo")
        block = (f"[[extra.photo]]\n"
                 f'project = "{project_id}"\n'
                 f'file = "{name}"\n'
                 f'alt = "{quote(alt)}"\n')
        fm = fm[:at] + block + "\n" + fm[at:]
        return _commit(head + "+++" + fm + tail, f"{name} added to {project_id}")
    except Exception:
        if dest.exists():
            dest.unlink()
        raise


def attach_dossier(concept: int, filename: str, raw: bytes, alt: str) -> str:
    """A PDF dropped on a concept, checked and turned into pages.

    THE PDF IS NOT KEPT. It is written to a temporary file, checked by
    `tools/dossier.py` — which looks at what is inside it and never at
    its name — rasterised, and discarded. Nothing but the page images
    survives this function, so there is no PDF to publish and none to
    leak out of the panel either.

    One document per concept. Dropping a second replaces the first,
    pages and all, because a card shows one.
    """
    import tempfile

    from dossier import Rejected as PdfRejected, render as render_pdf

    _, fm, _ = _front(CONTENT.read_text(encoding="utf-8"))
    concepts = blocks(fm, "extra.concepts")
    if not 1 <= concept <= len(concepts):
        raise Refused(f"there is no concept {concept}")

    alt = alt.strip()
    if not alt:
        raise Refused("a document needs a description — what is it?")
    if UNWRITTEN in alt:
        raise Refused("that is the placeholder, not a description")
    if len(alt) > MAX_LEN:
        raise Refused(f"{len(alt)} characters; the limit is {MAX_LEN}")
    plain(alt, "that description")

    if not raw:
        raise Refused("no file arrived")

    stem = _safe_name(filename).rsplit(".", 1)[0].lower()
    slug = re.sub(r"[^a-z0-9-]+", "-", stem).strip("-")[:38] or f"concept-{concept}"
    if len(slug) < 3:
        slug = f"concept-{concept}"

    with tempfile.TemporaryDirectory() as tmp:
        dropped = Path(tmp) / "dropped"
        dropped.write_bytes(raw)
        try:
            pages = render_pdf(dropped, slug, ROOT / "content")
        except PdfRejected as no:
            # The checker's words, not ours. It is the thing that looked.
            raise Refused(str(no))

    # Replace whatever this concept had.
    #
    # NOTHING IS DELETED UNTIL THE WRITE HAS SUCCEEDED. The first version
    # removed the old pages here, before rewriting the front matter, and
    # when the rewrite then failed it left a concept pointing at pages
    # that no longer existed — the files gone, the entry still there.
    # The old images are taken away at the end, or not at all.
    text = CONTENT.read_text(encoding="utf-8")
    head, fm, tail = _front(text)
    superseded = ""
    for i, doc in enumerate(blocks(fm, "extra.dossier")):
        if doc.get("concept", "").strip() != str(concept):
            continue
        superseded = doc.get("id", "").strip()
        # `_block_span` counts from ZERO — `enumerate` without a start,
        # therefore. Handing it a 1-based index asks for a block one past
        # the end, which it refuses, and the refusal arrives after the
        # pages have already been written.
        start, end = _block_span(fm, "extra.dossier", i)
        fm = fm[:start] + fm[end:]
        break

    block = (f"[[extra.dossier]]\n"
             f"concept = {concept}\n"
             f'id = "{slug}"\n'
             f"pages = {len(pages)}\n"
             # `quote()` escapes the contents; the quotes themselves are
             # the caller's, as everywhere else in this file. Without
             # them the front matter is not TOML and the build stops.
             f'alt = "{quote(alt)}"\n')
    at = _insert_at(fm, "extra.dossier")
    fm = fm[:at] + block + "\n" + fm[at:]
    message = _commit(head + "+++" + fm + tail,
                      f"{len(pages)}-page document on concept {concept}")

    # Written and accepted. Now the pages nothing points at any more.
    if superseded and superseded != slug:
        for leaf in (ROOT / "content").glob(f"dossier-{superseded}-p*.jpg"):
            leaf.unlink()
    return message


def remove_photo(file: str) -> str:
    """One photograph out of a reel. The file stays — another may use it."""
    text = CONTENT.read_text(encoding="utf-8")
    head, fm, tail = _front(text)
    shots = blocks(fm, "extra.photo")
    where = [i for i, s in enumerate(shots) if s.get("file") == file]
    if not where:
        raise Refused(f"no photograph named {file!r}")
    begin, end = _block_span(fm, "extra.photo", where[0])
    fm = fm[:begin] + fm[end:]
    return _commit(head + "+++" + fm + tail, f"{file} removed from its project")


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
