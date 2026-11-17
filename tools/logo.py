#!/usr/bin/env python3
"""Their own mark, in the browser tab and under a pasted link.

    python3 tools/logo.py        # say which marks are in place, and which are not

WHAT THIS IS FOR

`tools/icons.py` draws a placeholder: a point on a circle, no
letterform, because a letterform would be a logo and that is the
graphiste's to design. The moment they have designed one, three files
replace it, and nothing in the page or the head has to change — the
published names stay `favicon.svg`, `icon-180.png` and `og.png`.

THE THREE SLOTS

    static/logo.svg     the browser tab
    static/logo.png     the icon iOS puts on a home screen — square
    static/share.png     the picture under a pasted link — exactly 1200x630

Each is used EXACTLY as it was given. Whatever is not given keeps the
drawn mark, so one file may arrive without the other two.

WHY NOTHING IS CONVERTED HERE

There is no rasteriser in this repository and no dependency to add one:
an SVG cannot become those two PNGs, and a PNG cannot be rescaled
without a decoder. The ceiling is deliberate — the three files are what
a handover gives you anyway, and guessing a crop of someone's mark is
worse than asking for the export. What this does instead is refuse
anything that would ship broken: a file that is not the format it is
named, an SVG that carries script, a touch icon that is not square, a
share image that is not the size the meta tags promise.

WHERE THE REAL ONE LIVES

Not here. `_dropin/static/logo.svg` mirrors `static/logo.svg`, so the
mark is assembled into `_local/` and never enters the tracked tree —
the same mechanism as their photographs and their film, and for the same
reason: this repository is public and the brand is a stand-in.
"""
from __future__ import annotations

import re
import struct
import sys
import zlib
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

SIGNATURE = b"\x89PNG\r\n\x1a\n"

# A mark is a few kilobytes of geometry. A megabyte of it is a
# photograph that has been given the wrong name, or a font embedded by
# an export dialog nobody read.
MAX_SVG = 512 * 1024
MAX_PNG = 4 * 1024 * 1024

# What the share image must be. Not a preference: the page states these
# numbers to the scrapers in og:image:width and og:image:height, and a
# picture that disagrees with them is cropped by some and dropped by
# others.
SHARE = (1200, 630)


class Rejected(Exception):
    """The file was not accepted, and nothing was written."""


def png_size(raw: bytes) -> "tuple[int, int]":
    """The dimensions, from a PNG that is really a PNG.

    Every chunk is walked and every checksum verified. That is not
    paranoia about a corrupt download — it is the only way to tell a
    PNG from something renamed: the signature is eight bytes anyone can
    paste in front of anything.
    """
    if len(raw) > MAX_PNG:
        raise Rejected(f"{len(raw) // 1024 // 1024}MB of PNG; the limit is "
                       f"{MAX_PNG // 1024 // 1024}MB. A mark is geometry, not "
                       f"a photograph")
    if not raw.startswith(SIGNATURE):
        raise Rejected("that does not begin like a PNG, whatever it is named")

    at, size, seen = len(SIGNATURE), None, []
    while at + 8 <= len(raw):
        length, kind = struct.unpack(">I", raw[at:at + 4])[0], raw[at + 4:at + 8]
        body = raw[at + 8:at + 8 + length]
        if len(body) != length or at + 12 + length > len(raw):
            raise Rejected(f"the {kind.decode('latin-1')} chunk runs past the "
                           f"end of the file — it is truncated or it is not a PNG")
        want = struct.unpack(">I", raw[at + 8 + length:at + 12 + length])[0]
        if zlib.crc32(kind + body) & 0xFFFFFFFF != want:
            raise Rejected(f"the {kind.decode('latin-1')} chunk fails its own "
                           f"checksum — the bytes are not what a PNG writer wrote")
        seen.append(kind)
        if kind == b"IHDR":
            if length != 13:
                raise Rejected("the header is the wrong length for a PNG")
            w, h = struct.unpack(">II", body[:8])
            if not w or not h:
                raise Rejected("the header says the image has no width or no height")
            size = (w, h)
        at += 12 + length
        if kind == b"IEND":
            break

    if size is None or seen[0] != b"IHDR":
        raise Rejected("no PNG header where a PNG keeps it")
    if b"IDAT" not in seen:
        raise Rejected("a PNG with no image data in it")
    if seen[-1] != b"IEND":
        raise Rejected("the PNG never ends — the last chunk is not IEND")
    return size


# Elements and attributes that make an SVG more than a picture. It is
# served from our own origin and the policy forbids inline script, so a
# <script> in here would be blocked rather than run — but "blocked by
# the second lock" is not a reason to hand it the first one.
FORBIDDEN_TAGS = ("script", "foreignObject", "iframe", "handler", "audio",
                  "video", "use", "image")


def check_svg(raw: bytes) -> str:
    """An SVG that is a drawing and nothing else. Returns what it is."""
    if len(raw) > MAX_SVG:
        raise Rejected(f"{len(raw) // 1024}KB of SVG; the limit is "
                       f"{MAX_SVG // 1024}KB. That is usually a photograph "
                       f"traced, or a font embedded by the export")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise Rejected("that is not text, so it is not an SVG") from None

    # Before the parser, not after: a document type declaration is how
    # an XML file is made to read another file or expand to a gigabyte,
    # and there is no reason for a logo to carry one.
    if re.search(r"<!DOCTYPE|<!ENTITY", text, re.I):
        raise Rejected("the SVG declares a document type or an entity. Export "
                       "it as plain SVG — nothing here needs one")

    try:
        root = ET.fromstring(text)
    except ET.ParseError as broken:
        raise Rejected(f"that is not valid XML, so it is not an SVG ({broken})") \
            from None

    if root.tag.rsplit("}", 1)[-1] != "svg":
        raise Rejected(f"the document is <{root.tag.rsplit('}', 1)[-1]}>, not <svg>")
    if not (root.get("viewBox") or (root.get("width") and root.get("height"))):
        raise Rejected("the SVG says nothing about its own size — it needs a "
                       "viewBox, or a width and a height. A tab is 16 pixels "
                       "and the browser has to know what to scale")

    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1] if isinstance(el.tag, str) else ""
        if tag in FORBIDDEN_TAGS:
            raise Rejected(f"the SVG contains <{tag}>, which is not drawing — "
                           f"a mark in a browser tab is shapes and nothing else")
        for name, value in el.attrib.items():
            name = name.rsplit("}", 1)[-1]
            if name.lower().startswith("on"):
                raise Rejected(f"the SVG carries {name}, which is script")
            if name in ("href", "src") and not value.startswith("#"):
                raise Rejected(f"the SVG points at {value[:60]!r}. A mark that "
                               f"loads something else is a mark that breaks "
                               f"when that something moves")
            if "url(" in value.lower() and "#" not in value:
                raise Rejected("the SVG fetches something through url()")

    return f"{len(raw) // 1024 or 1}KB of SVG"


def check_touch(raw: bytes) -> str:
    w, h = png_size(raw)
    if w != h:
        raise Rejected(f"{w}x{h}: a home-screen icon is square. iOS crops it "
                       f"to a square either way, and its own crop is never "
                       f"the one you wanted")
    if w < 180:
        raise Rejected(f"{w}x{h}: 180x180 or larger. Below that iOS scales it "
                       f"up and the mark softens")
    return f"{w}x{h}"


def check_share(raw: bytes) -> str:
    w, h = png_size(raw)
    if (w, h) != SHARE:
        raise Rejected(f"{w}x{h}: the share image is exactly "
                       f"{SHARE[0]}x{SHARE[1]}. The page tells the scrapers "
                       f"that size, and one that disagrees is cropped by some "
                       f"of them and dropped by others")
    return f"{w}x{h}"


# name -> (file it becomes, what to check it with, what it is for)
SLOTS = {
    "logo": ("logo.svg", check_svg, "the browser tab"),
    "touch": ("logo.png", check_touch, "the icon on a home screen"),
    "share": ("share.png", check_share, "the picture under a pasted link"),
}


def accept(slot: str, raw: bytes) -> str:
    """Validate one dropped mark and put it in place.

    Nothing is written until the check passes, so a refused file leaves
    whatever was there before exactly as it was.
    """
    if slot not in SLOTS:
        raise Rejected(f"{slot!r} is not one of {', '.join(SLOTS)}")
    if not raw:
        raise Rejected("no file arrived")
    name, judge, what = SLOTS[slot]
    told = judge(raw)
    STATIC.mkdir(exist_ok=True)
    # Written beside and moved into place: a half-written mark in the
    # tab is worse than the placeholder it replaced.
    tmp = STATIC / f".{name}.part"
    tmp.write_bytes(raw)
    tmp.replace(STATIC / name)
    return f"{name} in place for {what} ({told})"


def installed() -> "dict[str, bytes]":
    """The marks that are present AND pass their own check.

    A file that is there but wrong is reported as absent, with the
    reason on stderr: `icons.py` then draws its placeholder, and the
    tab keeps working while someone fixes the export.
    """
    out = {}
    for slot, (name, judge, _what) in SLOTS.items():
        path = STATIC / name
        if not path.exists():
            continue
        raw = path.read_bytes()
        try:
            judge(raw)
        except Rejected as no:
            print(f"  static/{name} is not usable: {no}", file=sys.stderr)
            continue
        out[slot] = raw
    return out


def main() -> int:
    have = installed()
    print()
    for slot, (name, _judge, what) in SLOTS.items():
        state = "in place" if slot in have else "not dropped — the drawn mark stands"
        print(f"  {name:<12} {what:<36} {state}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
