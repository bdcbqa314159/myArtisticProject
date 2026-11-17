#!/usr/bin/env python3
"""A mark is judged by what is in the file, never by its name.

    python3 tools/logo-check.py

The same standard `tools/dossier-check.py` holds a PDF to, for the same
reason: a logo is a file someone hands over, and the extension on it is
whatever the export dialog last said. Every fixture here is written with
the RIGHT extension on purpose — `.svg` for a text file, `.png` for one
that merely starts like a PNG — because trusting the name is the failure
being tested for.

Nothing touches `static/`: each case runs against a temporary directory
with `logo.STATIC` pointed at it.
"""
from __future__ import annotations

import struct
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import logo                                                 # noqa: E402
from icons import mark, png                                 # noqa: E402

checks = 0
bad: "list[str]" = []


def ok(condition: bool, what: str) -> None:
    global checks
    checks += 1
    if not condition:
        bad.append(what)


def refused(slot: str, raw: bytes, fragment: str, what: str) -> None:
    """Refused, AND for a reason naming the real problem.

    The message is asserted, not just the refusal: every one of these
    is read by someone who has just dropped a file and has to work out
    what to export instead.
    """
    global checks
    checks += 1
    try:
        logo.accept(slot, raw)
    except logo.Rejected as no:
        if fragment.lower() not in str(no).lower():
            bad.append(f"{what} — refused, but said {str(no)!r}")
        return
    except Exception as boom:                               # noqa: BLE001
        bad.append(f"{what} — raised {boom!r} instead of refusing")
        return
    bad.append(what)


def accepted(slot: str, raw: bytes, what: str) -> None:
    global checks
    checks += 1
    try:
        logo.accept(slot, raw)
    except Exception as no:                                 # noqa: BLE001
        bad.append(f"{what} — refused with {no}")


def a_png(w: int, h: int) -> bytes:
    out = Path(tempfile.mkdtemp()) / "x.png"
    png(out, w, h, mark(w, h, 0.3))
    return out.read_bytes()


SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">'
       '<path d="M12 36 L24 12 L36 36 Z" fill="#111"/></svg>')


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        logo.STATIC = Path(tmp)

        square, wide = a_png(256, 256), a_png(*logo.SHARE)

        # ---- what a handover actually gives you ----------------------
        accepted("logo", SVG.encode(), "a plain SVG mark was refused")
        accepted("touch", square, "a square 256px PNG was refused as a touch icon")
        accepted("share", wide, "a 1200x630 PNG was refused as a share image")
        ok((Path(tmp) / "logo.svg").read_bytes() == SVG.encode(),
           "the SVG in place is not the one that was given")
        ok(set(logo.installed()) == {"logo", "touch", "share"},
           "three marks are in place and installed() does not report them")

        # ---- the name proves nothing --------------------------------
        refused("logo", b"just some text", "not valid XML",
                "a text file named .svg was accepted as the tab's mark")
        refused("touch", b"just some text", "does not begin like a PNG",
                "a text file named .png was accepted as the touch icon")
        refused("touch", logo.SIGNATURE + b"nothing else at all", "truncated",
                "eight bytes of PNG signature with rubbish after it was accepted")
        refused("share", SVG.encode(), "does not begin like a PNG",
                "an SVG was accepted where a PNG is required")
        refused("logo", square, "not text",
                "a PNG was accepted as the tab's SVG")

        # A real PNG with one byte of its image data altered. The
        # signature still matches and the header still parses — only
        # the checksum knows.
        tampered = bytearray(square)
        at = bytes(tampered).index(b"IDAT") + 10
        tampered[at] ^= 0xFF
        refused("touch", bytes(tampered), "checksum",
                "a PNG whose data was altered after it was written was accepted")

        # A header that lies about its own length.
        lying = bytearray(square)
        struct.pack_into(">I", lying, 8, 12)
        refused("touch", bytes(lying), "checksum",
                "a PNG whose header length was rewritten was accepted")

        # Everything a PNG needs except the pixels.
        def chunk(kind: bytes, data: bytes) -> bytes:
            return (struct.pack(">I", len(data)) + kind + data
                    + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

        headless = (logo.SIGNATURE
                    + chunk(b"IHDR", struct.pack(">IIBBBBB", 8, 8, 8, 2, 0, 0, 0))
                    + chunk(b"IEND", b""))
        refused("touch", headless, "no image data",
                "a PNG with a header and no pixels was accepted")

        # ---- the wrong size is the wrong file ------------------------
        refused("touch", wide, "square",
                "a 1200x630 image was accepted as a home-screen icon")
        refused("touch", a_png(64, 64), "180",
                "a 64px icon was accepted, which iOS would scale up")
        refused("share", square, "1200x630",
                "a square image was accepted as the share picture, which the "
                "page promises is 1200x630")

        # ---- an SVG is a drawing, not a program ----------------------
        for carrying, fragment, what in (
            ('<script>fetch("//elsewhere")</script>', "<script>", "script"),
            ('<foreignObject><b>x</b></foreignObject>', "foreignObject",
             "a foreignObject"),
            ('<image href="https://elsewhere/x.png"/>', "<image>",
             "an image fetched from elsewhere"),
            ('<use href="https://elsewhere/x.svg#m"/>', "<use>", "a remote use"),
        ):
            refused("logo",
                    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
                    f'{carrying}</svg>'.encode(),
                    fragment,
                    f"an SVG carrying {what} was accepted into the browser tab")

        refused("logo",
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
                '<rect width="10" height="10" onload="alert(1)"/></svg>'.encode(),
                "script", "an SVG with an event handler attribute was accepted")
        refused("logo",
                '<!DOCTYPE svg [<!ENTITY a "x">]>'
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"/>'
                .encode(),
                "document type",
                "an SVG declaring entities was accepted — that is how an XML "
                "file is made to read another one")
        refused("logo",
                '<svg xmlns="http://www.w3.org/2000/svg"><circle r="4"/></svg>'
                .encode(),
                "viewBox",
                "an SVG that says nothing about its own size was accepted, so "
                "a 16px tab has nothing to scale")
        refused("logo", b"<html><body>no</body></html>", "not <svg>",
                "an HTML document was accepted as the mark")

        # ---- the limits ---------------------------------------------
        refused("logo",
                ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
                 + "<!--" + "x" * (logo.MAX_SVG + 10) + "-->" + "</svg>").encode(),
                "limit", "half a megabyte of SVG was accepted")
        refused("logo", b"", "no file", "an empty drop was accepted")
        refused("nowhere", SVG.encode(), "not one of",
                "a slot that does not exist was accepted")

        # ---- a refusal writes nothing -------------------------------
        before = (Path(tmp) / "logo.svg").read_bytes()
        refused("logo", b"<svg>broken", "not valid XML", "broken XML accepted")
        ok((Path(tmp) / "logo.svg").read_bytes() == before,
           "a refused drop changed the mark that was already in place")

        # ---- and one that is there but wrong is reported absent ------
        (Path(tmp) / "share.png").write_bytes(b"not a png at all")
        have = logo.installed()
        ok("share" not in have,
           "a file that is present but unusable is reported as installed — "
           "icons.py would copy it into the share image")
        ok({"logo", "touch"} <= set(have),
           "one unusable mark made the usable ones disappear")

    if bad:
        print("\n  THE MARK\n")
        for b in bad:
            print(f"    - {b}")
        print()
        return 1
    print(f"\n  logo: a mark is judged by its bytes, at {checks} points\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
