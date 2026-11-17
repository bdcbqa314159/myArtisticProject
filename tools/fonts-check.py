#!/usr/bin/env python3
"""A typeface is judged by its header, and the stylesheet by what it says.

    python3 tools/fonts-check.py

Two things are being held to account here. One is the file: a woff2 is
accepted or refused on what its header declares, never on the name it
arrived with — every fixture below is written as `.woff2` on purpose.
The other is the artefact: `static/css/fonts.css` is generated from a
family name a person typed into config.toml, so the check reads the
produced stylesheet back and refuses anything that is not a font face.

Nothing touches `static/`: the module's paths are pointed at a
temporary directory for the duration.
"""
from __future__ import annotations

import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import fonts                                                # noqa: E402

checks = 0
bad: "list[str]" = []


def ok(condition: bool, what: str) -> None:
    global checks
    checks += 1
    if not condition:
        bad.append(what)


def refused(call, fragment: str, what: str) -> None:
    """Refused, AND for a reason that names what to do instead."""
    global checks
    checks += 1
    try:
        call()
    except fonts.Rejected as no:
        if fragment.lower() not in str(no).lower():
            bad.append(f"{what} — refused, but said {str(no)!r}")
        return
    except Exception as boom:                               # noqa: BLE001
        bad.append(f"{what} — raised {boom!r} instead of refusing")
        return
    bad.append(what)


def a_woff2(body: bytes = b"\x00" * 400, *, tables: int = 14,
            flavour: bytes = b"\x00\x01\x00\x00",
            length: "int | None" = None,
            compressed: "int | None" = None) -> bytes:
    """A woff2 header that declares the truth, over an opaque body.

    There is no Brotli here, so a REAL woff2 cannot be built — and that
    is exactly the ceiling `fonts.py` states: it checks the header and
    the lengths, and the body is opaque to it. These fixtures therefore
    test precisely what it claims to test, no more.
    """
    head = bytearray(48)
    head[0:4] = b"wOF2"
    head[4:8] = flavour
    struct.pack_into(">I", head, 8,
                     len(body) + 48 if length is None else length)
    struct.pack_into(">H", head, 12, tables)
    struct.pack_into(">I", head, 16, 2000)
    struct.pack_into(">I", head, 20,
                     len(body) if compressed is None else compressed)
    struct.pack_into(">HH", head, 24, 1, 0)
    return bytes(head) + body


def main() -> int:
    global checks
    face = a_woff2()

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        fonts.FONTS = tmp / "fonts"
        fonts.SHEET = tmp / "css" / "fonts.css"
        fonts.CONFIG = tmp / "config.toml"

        def named(serif: str = "", sans: str = "") -> None:
            fonts.CONFIG.write_text(
                f'[extra.theme]\nserif = "{serif}"\nsans = "{sans}"\n\n'
                f'[extra.other]\nserif = "not this one"\n', encoding="utf-8")

        # ---- the name and the file are two halves --------------------
        named()
        refused(lambda: fonts.accept("display", face), "theme.serif is empty",
                "a face was accepted with no family name decided, so nothing "
                "would have loaded it")

        named(serif="serif, Georgia")
        refused(lambda: fonts.accept("display", face), "resolves itself",
                "a stack beginning with a generic was accepted, which would "
                "emit @font-face for a keyword the browser owns")

        # Valid TOML, and the dangerous half is not quotes — a brace and
        # a semicolon need none, and they reach the stylesheet intact.
        # A quote cannot appear raw: `set_config` escapes it, so what
        # reaches here is the backslash — which is in the list.
        for carrying in ('Canela; } body { display: none',
                         'Canela\\', 'Canela url(//x)', 'Canela/*x*/',
                         'Canela<script>'):
            named(serif=carrying)
            refused(lambda: fonts.accept("display", face), "not a family name",
                    f"the family name {carrying!r} was accepted — it is "
                    f"written straight into a stylesheet")

        named(serif="Canela, Georgia, serif", sans="Söhne, system-ui")
        fonts.accept("display", face)
        ok((fonts.FONTS / "display.woff2").read_bytes() == face,
           "the face in place is not the file that was given")
        ok(fonts.family("serif") == "Canela",
           "the family name is not the first one in the stack")
        ok(fonts.family("sans") == "Söhne",
           "a family name with a diacritic in it was mangled")
        ok(fonts.stack("serif") == "Canela, Georgia, serif",
           "the stack was read from the wrong section of config.toml")

        # ---- what it produces ---------------------------------------
        css = fonts.build()
        ok('font-family: "Canela"' in css,
           "the stylesheet does not name the family the stack asks for")
        ok('url("../fonts/display.woff2")' in css,
           "the stylesheet does not point at the file, or not relatively — an "
           "absolute path breaks the moment the site is served from a subpath")
        ok("font-weight: 400" in css and "font-display: swap" in css,
           "the face is declared without a weight, or without swap — which is "
           "invisible text while it loads")
        ok(css.count("@font-face") == 1,
           "one face is in place and the stylesheet declares a different number")
        ok(fonts.malformed(css) == "",
           f"the stylesheet it generates fails its own check: "
           f"{fonts.malformed(css)}")

        # Two files, two faces, both weights.
        fonts.accept("text", a_woff2(body=b"\x01" * 200))
        fonts.accept("text-bold", a_woff2(body=b"\x02" * 220))
        css = fonts.build()
        ok(css.count("@font-face") == 3, "three faces in place, not three rules")
        ok("font-weight: 700" in css,
           "the bold file is in place and nothing declares it bold")
        ok(css.count('font-family: "Söhne"') == 2,
           "the text face and its bold are not the same family, so the browser "
           "would treat them as two unrelated typefaces")

        # ---- the artefact is read back ------------------------------
        # The MESSAGE, not just the refusal. Two of these guards
        # overlap — an `@import` is both an at-rule and text outside any
        # block — and with only "something was refused" asserted, either
        # could be deleted with the suite still green. Mutation said so.
        for carrying, fragment, what in (
            (':root { --ink: red }', "may carry only @font-face",
             "a rule that is not a font face"),
            ('@import url("//elsewhere/x.css");', "may carry only @font-face",
             "an import of someone else's stylesheet"),
            ('--ink: red;', "outside any rule",
             "a declaration loose in the file"),
            ('@font-face { behavior: url("x.htc") }', "not a font descriptor",
             "a descriptor that is not one"),
            ('@font-face { src: url("https://elsewhere/x.woff2") }',
             "must come from static/fonts/",
             "a face fetched from another origin"),
        ):
            checks += 1
            said = fonts.malformed(fonts.HEAD + "\n" + carrying)
            if not said:
                bad.append(f"the stylesheet check accepts {what}")
            elif fragment not in said:
                bad.append(f"{what} is refused, but for the wrong reason: "
                           f"{said!r}")

        # ---- the file is not what it is named -----------------------
        refused(lambda: fonts.accept("display", b"just some text"),
                "does not begin like a woff2",
                "a text file named .woff2 was accepted")
        refused(lambda: fonts.accept("display", b"wOFF" + b"\x00" * 100),
                "woff, not woff2",
                "a woff1 was accepted, and it was not told what to export")
        refused(lambda: fonts.accept("display", b"OTTO" + b"\x00" * 100),
                "desktop font",
                "an otf was accepted, and it was not told what to export")
        refused(lambda: fonts.accept("display",
                                     b"\x00\x01\x00\x00" + b"\x00" * 100),
                "desktop font", "a ttf was accepted")
        refused(lambda: fonts.accept("display", b"wOF2" + b"\x00" * 20),
                "shorter than a woff2 header",
                "twenty bytes were accepted as a typeface")
        refused(lambda: fonts.accept("display", a_woff2(length=999_999)),
                "truncated", "a header claiming a longer file was accepted")
        refused(lambda: fonts.accept("display", a_woff2(tables=0)),
                "no tables", "a font declaring no tables was accepted")
        refused(lambda: fonts.accept("display", a_woff2(compressed=900_000)),
                "more compressed data than the file holds",
                "a header promising more data than it carries was accepted")
        refused(lambda: fonts.accept("display", a_woff2(flavour=b"junk")),
                "flavour", "a header with no recognisable flavour was accepted")
        refused(lambda: fonts.accept("display",
                                     a_woff2(body=b"\x00" * (fonts.MAX_FACE + 1))),
                "limit", "three megabytes of typeface were accepted")
        refused(lambda: fonts.accept("display", b""), "no file",
                "an empty drop was accepted")
        refused(lambda: fonts.accept("italic", face), "not one of",
                "a slot that does not exist was accepted")

        # ---- a refusal writes nothing -------------------------------
        before = (fonts.FONTS / "display.woff2").read_bytes()
        refused(lambda: fonts.accept("display", b"wOFF" + b"\x00" * 60),
                "woff, not woff2", "a woff1 was accepted")
        ok((fonts.FONTS / "display.woff2").read_bytes() == before,
           "a refused drop replaced the face that was already in place")

        # ---- present but unusable is reported absent ----------------
        (fonts.FONTS / "text.woff2").write_bytes(b"not a font at all")
        have = fonts.installed()
        ok("text" not in have,
           "a file that is present but unusable is reported as installed — the "
           "stylesheet would declare a face no browser can read")
        ok({"display", "text-bold"} <= set(have),
           "one unusable face made the usable ones disappear")
        ok("text.woff2" not in fonts.build(),
           "the stylesheet declares a face that did not pass its own check")

        # ---- and the state this whole thing exists to stop ----------
        # A name decided, no file: the generated stylesheet must be
        # empty rather than pointing at a file that is not there.
        for name in fonts.SLOTS:
            (fonts.FONTS / fonts.SLOTS[name][0]).unlink(missing_ok=True)
        ok("@font-face" not in fonts.build(),
           "with nothing dropped the stylesheet still declares a face, so "
           "every visitor waits for a file that does not exist")

    if bad:
        print("\n  THE TYPEFACE\n")
        for b in bad:
            print(f"    - {b}")
        print()
        return 1
    print(f"\n  fonts: a face is judged by its header and the stylesheet by "
          f"its contents, at {checks} points\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
