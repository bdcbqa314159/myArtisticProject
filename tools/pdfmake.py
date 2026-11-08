"""A very small PDF writer — fixtures only, never the real thing.

    python3 tools/pdfmake.py out.pdf "Page one line" "Page two line"

It exists so that `tools/dossier-check.py` has a GENUINE PDF to test
against without a dependency, and so the tracked placeholder dossier is
something this repository made rather than anything of the client's.

Deliberately minimal: one of the base-14 fonts, no compression, no
images. If this ever needs to do more than make a page with words on it,
the answer is a real library and not more of this file.
"""
from __future__ import annotations

import sys
from pathlib import Path

PAGE_W, PAGE_H = 595, 842          # A4 at 72dpi


def _escape(s: str) -> str:
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _content(lines: "list[str]") -> bytes:
    out = ["BT", "/F1 22 Tf", "64 740 Td", "28 TL"]
    for i, line in enumerate(lines):
        out.append(f"({_escape(line)}) Tj" if i == 0
                   else f"T* ({_escape(line)}) Tj")
    out.append("ET")
    return "\n".join(out).encode("latin-1", "replace")


def build(pages: "list[list[str]]") -> bytes:
    """`pages` is a list of pages, each a list of text lines."""
    objects: "list[bytes]" = []

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)                      # object numbers are 1-based

    catalog = add(b"")                           # reserved, filled in below
    pages_obj = add(b"")
    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
               b"/Encoding /WinAnsiEncoding >>")

    kids = []
    for lines in pages:
        stream = _content(lines)
        contents = add(b"<< /Length " + str(len(stream)).encode() + b" >>\n"
                       b"stream\n" + stream + b"\nendstream")
        page = add(
            b"<< /Type /Page /Parent " + str(pages_obj).encode() + b" 0 R "
            b"/MediaBox [0 0 " + f"{PAGE_W} {PAGE_H}".encode() + b"] "
            b"/Resources << /Font << /F1 " + str(font).encode() + b" 0 R >> >> "
            b"/Contents " + str(contents).encode() + b" 0 R >>")
        kids.append(f"{page} 0 R")

    objects[catalog - 1] = (b"<< /Type /Catalog /Pages "
                            + str(pages_obj).encode() + b" 0 R >>")
    objects[pages_obj - 1] = (b"<< /Type /Pages /Kids [" + " ".join(kids).encode()
                              + b"] /Count " + str(len(pages)).encode() + b" >>")

    # ---- assemble, recording where each object starts ------------------
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for n, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += str(n).encode() + b" 0 obj\n" + body + b"\nendobj\n"

    start_xref = len(out)
    out += b"xref\n0 " + str(len(objects) + 1).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode()
    out += (b"trailer\n<< /Size " + str(len(objects) + 1).encode()
            + b" /Root " + str(catalog).encode() + b" 0 R >>\n"
            b"startxref\n" + str(start_xref).encode() + b"\n%%EOF\n")
    return bytes(out)


def main(argv: "list[str]") -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    dest = Path(argv[1])
    pages = [[line] for line in argv[2:]]
    dest.write_bytes(build(pages))
    print(f"  {dest}  {len(pages)} page(s)  {dest.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
