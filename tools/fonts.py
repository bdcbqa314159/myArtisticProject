#!/usr/bin/env python3
"""The typeface she chose, actually loaded.

    python3 tools/fonts.py            # write static/css/fonts.css
    python3 tools/fonts.py --check    # fail if what is committed is stale

WHY THIS EXISTS

`[extra.theme]` in config.toml takes a font stack, and the studio panel
invites someone to type one — `serif = "Canela, Georgia, serif"`. Until
now that did nothing at all: this site loads no font file anywhere, so
the browser looked for Canela among the faces installed on the
visitor's own machine, did not find it, and quietly drew Georgia. The
panel said the decision had been taken and every visitor saw the
fallback.

So the stack is now half of the answer and the file is the other half:

    static/fonts/display.woff2      the display face      weight 400
    static/fonts/text.woff2         the text face         weight 400
    static/fonts/text-bold.woff2    the text face, bold   weight 700

THE FAMILY NAME IS NOT INVENTED HERE

It is the FIRST family in the stack she typed. Drop `display.woff2`,
write `serif = "Canela, Georgia, serif"`, and this emits an `@font-face`
for "Canela" — so the stack in the stylesheet resolves to the file, and
the rest of the stack stays a real fallback for the moment the file is
missing. Neither half works alone, and this says which one is absent.

WHY A SEPARATE STYLESHEET

`tools/theme.py` writes custom properties and refuses an `@`-rule by
design — it validates that what it produced is nothing but tokens. An
`@font-face` is not a token, so it belongs in its own artefact with its
own validation, linked after it.

WHERE THE CHECKING STOPS. A woff2 body is Brotli, and there is no
Brotli in the standard library — so this reads the header and the
lengths it declares, and does not decompress anything. That catches
every accident: a woff1, a desktop otf, a truncated upload, a file
renamed. It would not catch a deliberately crafted header over
rubbish, and the consequence of one is that the browser ignores the
face and draws the fallback. Refusing a real font with a confusing
message is the worse failure of the two, so the check stops where it
can still be certain.

WEIGHTS. Three faces, two weights, no synthesis: a request for 500 —
which `site.css` makes — matches 400 under the CSS matching rules. If
the bold file is absent the browser synthesises it, exactly as it would
have done before any of this. Nothing here reads the inside of the
font, so a variable font is used at its default instance and its axes
are not reachable; that is a real ceiling and the alternative is a
dependency.
"""
from __future__ import annotations

import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.toml"
FONTS = ROOT / "static" / "fonts"
SHEET = ROOT / "static" / "css" / "fonts.css"

SIGNATURE = b"wOF2"

# A woff2 text face is tens of kilobytes. A megabyte of it is a family
# with every weight in one file, or a CJK face, and either way the
# visitor waits for it before a word appears.
MAX_FACE = 2 * 1024 * 1024

# What the file may claim to contain. Anything else is not a font that
# a browser will load, whatever the name says.
FLAVOURS = (b"\x00\x01\x00\x00", b"OTTO", b"true", b"ttcf")

# slot -> (file, which stack it belongs to, weight, what it is)
SLOTS = {
    "display":   ("display.woff2", "serif", 400, "the display face"),
    "text":      ("text.woff2", "sans", 400, "the text face"),
    "text-bold": ("text-bold.woff2", "sans", 700, "the text face in bold"),
}

# A family name, and nothing that could end a declaration or start a
# rule. Deliberately stricter than it has to be: this string is written
# into a stylesheet. The accented range is the same one `theme.py`
# allows in a stack, and it is not decoration — Söhne, Fóra and Grüner
# are typefaces a graphiste actually specifies.
FAMILY = re.compile(r"^[A-Za-z0-9 ._\-À-ɏ]{1,60}$")

# Names a browser resolves itself. One of these as the first family
# means no decision has been taken yet, and an @font-face claiming the
# name `serif` would be a trap for whoever reads the CSS next.
GENERIC = {
    "serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui",
    "ui-serif", "ui-sans-serif", "ui-monospace", "ui-rounded",
    "-apple-system", "blinkmacsystemfont", "math", "emoji", "fangsong",
}


class Rejected(Exception):
    """The file is not a usable webfont. Nothing was written."""


def check_woff2(raw: bytes) -> str:
    """A woff2 that is really a woff2. Returns what it is.

    The header is read rather than the four magic bytes alone: a
    signature is something anyone can paste in front of anything, and
    the one number that cannot be faked by accident is the file's own
    declared length.
    """
    if not raw:
        raise Rejected("no file arrived")
    if raw.startswith(b"wOFF"):
        raise Rejected("that is woff, not woff2. Export woff2 — it is half "
                       "the bytes for the same letters, and everything that "
                       "can read this site reads it")
    if raw[:4] in (b"\x00\x01\x00\x00", b"OTTO", b"true", b"ttcf"):
        raise Rejected("that is a desktop font (ttf or otf). Export woff2 — a "
                       "desktop file is three times the size, and the visitor "
                       "waits for every byte before a word appears")
    if not raw.startswith(SIGNATURE):
        raise Rejected("that does not begin like a woff2, whatever it is named")
    if len(raw) > MAX_FACE:
        raise Rejected(f"{len(raw) // 1024}KB; the limit is "
                       f"{MAX_FACE // 1024}KB. One weight of one face is tens "
                       f"of kilobytes — that is a whole family, or a face with "
                       f"every language in it")
    if len(raw) < 48:
        raise Rejected("the file is shorter than a woff2 header")

    flavour = raw[4:8]
    length, tables, _reserved = struct.unpack(">IHH", raw[8:16])
    compressed = struct.unpack(">I", raw[20:24])[0]

    if flavour not in FLAVOURS:
        raise Rejected("the header does not say what kind of font it wraps — "
                       "the four bytes after the signature are not a flavour "
                       "any woff2 writer emits")
    if length != len(raw):
        raise Rejected(f"the header says the file is {length:,} bytes and it "
                       f"is {len(raw):,} — it is truncated, or it is not a "
                       f"woff2")
    if not tables:
        raise Rejected("the header says the font has no tables in it")
    if compressed > len(raw) - 48:
        raise Rejected("the header promises more compressed data than the "
                       "file holds")
    return f"{len(raw) // 1024 or 1}KB, {tables} tables"


def stack(which: str) -> str:
    """One font stack as written in `[extra.theme]`, or empty."""
    text = CONFIG.read_text(encoding="utf-8")
    start = text.find("[extra.theme]")
    if start == -1:
        return ""
    rest = text[start + len("[extra.theme]"):]
    nxt = rest.find("\n[")
    block = rest if nxt == -1 else rest[:nxt]
    found = re.search(rf'^\s*{which}\s*=\s*"([^"]*)"', block, re.M)
    return found.group(1).strip() if found else ""


def family(which: str) -> str:
    """The first family in that stack — the one the file will answer to.

    Refuses a generic, because a generic is what is there when nobody
    has decided: emitting `@font-face { font-family: serif }` would
    capture a keyword the browser owns.
    """
    first = stack(which).split(",")[0].strip().strip('"').strip("'").strip()
    if not first:
        raise Rejected(
            f"theme.{which} is empty, so there is no family name for the file "
            f"to answer to. Write the face first — e.g. "
            f'{which} = "Canela, Georgia, serif" — then the file is loaded as '
            f'"Canela"')
    if first.lower() in GENERIC:
        raise Rejected(
            f"theme.{which} begins with {first!r}, which is a name the browser "
            f"resolves itself. Put the real face first: "
            f'"{first.title()} Display, {first}"')
    if not FAMILY.match(first):
        raise Rejected(f"{first!r} is not a family name. Letters, digits, "
                       f"spaces, dots, hyphens and underscores")
    return first


def installed() -> "dict[str, bytes]":
    """The faces that are present AND pass their own check."""
    out = {}
    for slot, (name, _which, _weight, _what) in SLOTS.items():
        path = FONTS / name
        if not path.exists():
            continue
        raw = path.read_bytes()
        try:
            check_woff2(raw)
        except Rejected as no:
            print(f"  static/fonts/{name} is not usable: {no}", file=sys.stderr)
            continue
        out[slot] = raw
    return out


def accept(slot: str, raw: bytes) -> str:
    """Validate one dropped face and put it in place."""
    if slot not in SLOTS:
        raise Rejected(f"{slot!r} is not one of {', '.join(SLOTS)}")
    name, which, _weight, what = SLOTS[slot]
    told = check_woff2(raw)
    # The name it will answer to has to exist before the file is worth
    # having, and the refusal is more useful before the upload than
    # after it.
    named = family(which)
    FONTS.mkdir(parents=True, exist_ok=True)
    tmp = FONTS / f".{name}.part"
    tmp.write_bytes(raw)
    tmp.replace(FONTS / name)
    return f"{name} in place for {what} ({told}), loaded as {named!r}"


HEAD = ("/* GENERATED by tools/fonts.py from static/fonts/ and [extra.theme]\n"
        "   in config.toml. Do not edit: the next run overwrites it.\n"
        "\n"
        "   The family name is the first one in the stack, so the stack in\n"
        "   site.css resolves to the file and the rest of it stays a real\n"
        "   fallback. No file dropped means no rule here, and the page\n"
        "   draws what the visitor already has — which is what it did\n"
        "   before any of this. */\n")


def build() -> str:
    have = installed()
    if not have:
        return HEAD + "\n/* No face dropped. */\n"

    rules = []
    for slot, raw in have.items():
        name, which, weight, _what = SLOTS[slot]
        rules.append(
            "@font-face {\n"
            f'  font-family: "{family(which)}";\n'
            f'  src: url("../fonts/{name}") format("woff2");\n'
            f"  font-weight: {weight};\n"
            "  font-style: normal;\n"
            "  font-display: swap;\n"
            "}"
        )
    return HEAD + "\n" + "\n\n".join(rules) + "\n"


DESCRIPTORS = ("font-family", "src", "font-weight", "font-style", "font-display")


def malformed(css: str) -> str:
    """What the shipped stylesheet must not contain.

    Independent of how it was built, for the same reason `theme.py`
    does this: the thing that ships is the file. A family name arrives
    from config.toml, which a person types into, and it is written
    into CSS — so the artefact is read back and refused unless it is
    nothing but font faces.
    """
    body = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    if not body.strip():
        return ""
    # Every at-rule by name, BEFORE walking the braces. An `@import` has
    # no block at all, so a walk over `{...}` rules never sees one — it
    # slipped through the first version of this function entirely, which
    # is the whole argument for reading the artefact back rather than
    # trusting the thing that wrote it.
    for at in re.findall(r"@[\w-]+", body):
        if at != "@font-face":
            return (f"the stylesheet carries {at}, and may carry only "
                    f"@font-face — an at-rule with no block of its own is how "
                    f"a stylesheet reaches off this origin")
    opens, closes = body.count("{"), body.count("}")
    if opens != closes:
        return (f"{opens} opening braces against {closes} closing — a rule is "
                f"unbalanced, which is how one rule becomes two")
    for rule in re.finditer(r"([^{}]*)\{([^{}]*)\}", body):
        at = rule.group(1).strip()
        if at != "@font-face":
            return (f"the stylesheet carries {at!r}, and may carry only "
                    f"@font-face")
        for line in rule.group(2).strip().splitlines():
            line = line.strip().rstrip(";")
            if not line:
                continue
            prop = line.split(":", 1)[0].strip()
            if prop not in DESCRIPTORS:
                return (f"{prop!r} is not a font descriptor. This file may "
                        f"set {', '.join(DESCRIPTORS)} and nothing else")
            if prop == "src" and "../fonts/" not in line:
                return (f"a face is loaded from {line!r} — it must come from "
                        f"static/fonts/ on this origin")

    # Last, because a real rule deserves to be told what is wrong with
    # its selector rather than that it is loose: anything still here
    # once the faces are removed is text outside any block, which is
    # dead in CSS and was therefore not written by this tool.
    loose = re.sub(r"@font-face\s*\{[^{}]*\}", "", body).strip()
    if loose:
        return (f"{loose[:60]!r} sits outside any rule, and nothing here "
                f"writes text outside a rule")
    return ""


def main(argv: "list[str]") -> int:
    try:
        made = build()
    except Rejected as no:
        print(f"\n  FONTS REFUSED\n\n    - {no}\n", file=sys.stderr)
        return 1

    if "--check" in argv:
        on_disk = SHEET.read_text(encoding="utf-8") if SHEET.exists() else ""
        if on_disk != made:
            print("\n  static/css/fonts.css does not match static/fonts/ and "
                  "[extra.theme].\n\n    Fix it with: python3 tools/fonts.py\n",
                  file=sys.stderr)
            return 1
        shape = malformed(on_disk)
        if shape:
            print(f"\n  FONT STYLESHEET IS WRONG\n\n    - {shape}\n",
                  file=sys.stderr)
            return 1
        faces = made.count("@font-face")
        print(f"\n  fonts: the committed stylesheet matches what is dropped "
              f"and holds nothing but faces ({faces} in place)\n")
        return 0

    SHEET.parent.mkdir(parents=True, exist_ok=True)
    SHEET.write_text(made, encoding="utf-8")
    print(f"\n  wrote {SHEET.relative_to(ROOT)} "
          f"({made.count('@font-face')} face(s) in place)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
