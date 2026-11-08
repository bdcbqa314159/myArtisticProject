"""What the PDF checker refuses.

    python3 tools/dossier-check.py

"Only pdf type — with a real checker. No txt renamed pdf or whatever."

So the thing being tested here is not that a PDF is accepted. It is that
the eight ways of pretending to be one are all refused, and that NONE of
the refusals depend on the file's name — every fixture below is written
with a `.pdf` extension on purpose.

The fixtures are built, not stored: `tools/pdfmake.py` writes a genuine
PDF, and each fake is a deliberate corruption of it. A fixture committed
as a binary would rot quietly the first time anything about the checker
changed.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


dossier = _load("dossier", ROOT / "tools" / "dossier.py")
pdfmake = _load("pdfmake", ROOT / "tools" / "pdfmake.py")
Rejected = dossier.Rejected

passed = 0
failed: "list[str]" = []


def refuses(name: str, data: bytes, expect: str) -> None:
    """It must say no, and say WHY in those words. Asserting only that it
    refused would pass against a checker that refuses everything."""
    global passed
    with tempfile.TemporaryDirectory() as d:
        # ALWAYS .pdf. The extension is the lie being tested.
        f = Path(d) / "dropped.pdf"
        f.write_bytes(data)
        try:
            dossier.accept(f)
        except Rejected as no:
            if expect in str(no):
                passed += 1
            else:
                failed.append(f"{name}: refused, but for the wrong reason — "
                              f"wanted {expect!r}, got {str(no)!r}")
            return
    failed.append(f"{name}: ACCEPTED. A file that is not a PDF was taken "
                  f"for one")


def accepts(name: str, data: bytes, pages: int) -> None:
    global passed
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "dropped.pdf"
        f.write_bytes(data)
        try:
            n = dossier.accept(f)
        except Rejected as no:
            failed.append(f"{name}: REFUSED a real PDF — {no}")
            return
    if n != pages:
        failed.append(f"{name}: counted {n} pages, expected {pages}")
    else:
        passed += 1


REAL = pdfmake.build([["Format Two"], ["A second page"], ["A third"]])

# ---- the one that must work -------------------------------------------
accepts("a genuine three-page PDF", REAL, 3)

# ---- and every way of pretending --------------------------------------
refuses("a text file renamed .pdf",
        b"This is just prose, saved with the wrong extension.\n" * 20,
        "begins with %PDF-")

refuses("a PNG renamed .pdf",
        b"\x89PNG\r\n\x1a\n" + bytes(400),
        "begins with %PDF-")

refuses("a zip renamed .pdf",
        b"PK\x03\x04" + bytes(400),
        "begins with %PDF-")

# The signature moved off offset zero — a file something has been done to.
refuses("a PDF with junk in front of the signature",
        b"HELLO" + REAL,
        "begins with %PDF-")

refuses("an empty file", b"", "too small")

refuses("a few bytes that happen to start right",
        b"%PDF-1.4\n", "too small")

# Header present, body gone: the shape a half-finished upload has.
refuses("a truncated PDF", REAL[:len(REAL) // 2] + bytes(300),
        "no end-of-file marker")

refuses("a made-up PDF version",
        b"%PDF-9.9\n" + REAL[9:], "not of a version that exists")

# Signature and trailer both present, nothing in between that parses.
# This is the one only a real parser can catch.
refuses("a forgery with the right ends and nothing in the middle",
        b"%PDF-1.4\n" + b"x" * 400 + b"\n%%EOF\n",
        "could not read that file")

refuses("more pages than the page is willing to carry",
        pdfmake.build([["p"]] * (dossier.MAX_PAGES + 1)),
        "over the")

# ---- the name is never the evidence -----------------------------------
with tempfile.TemporaryDirectory() as d:
    odd = Path(d) / "no-extension-at-all"
    odd.write_bytes(REAL)
    try:
        dossier.accept(odd)
        passed += 1
    except Rejected as no:
        failed.append(f"a real PDF with no .pdf extension was refused — {no}")

# ---- and the pages really come out ------------------------------------
with tempfile.TemporaryDirectory() as d:
    src = Path(d) / "x.pdf"
    src.write_bytes(REAL)
    try:
        made = dossier.render(src, "probe-dossier", Path(d) / "out")
        if len(made) == 3 and all(f.stat().st_size > 1000 for f in made):
            passed += 1
        else:
            failed.append(f"rendering produced {len(made)} usable pages, "
                          f"expected 3")
    except Rejected as no:
        failed.append(f"a real PDF would not render — {no}")

    for bad_slug in ("", "a", "Format Two", "../escape", "x" * 50):
        try:
            dossier.render(src, bad_slug, Path(d) / "out")
            failed.append(f"the name {bad_slug!r} was accepted — a name "
                          f"becomes a path, and a path that escapes writes "
                          f"wherever it likes")
        except Rejected:
            passed += 1

if failed:
    print("\n  THE PDF CHECKER IS WRONG\n")
    for f in failed:
        print(f"    - {f}")
    print()
    raise SystemExit(1)

print(f"\n  dossier: {passed} checks — a real PDF is taken, and "
      f"{len(['x'] * 11)} kinds of fake are refused by what is inside them\n")
