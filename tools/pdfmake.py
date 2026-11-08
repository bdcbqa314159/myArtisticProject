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


def jpeg_size(data: bytes) -> "tuple[int, int, int]":
    """Width, height and component count, read from the JPEG itself.

    Only the SOF marker is needed, and only to tell the PDF how big the
    picture is — the bytes go in untouched. A PDF can carry a JPEG
    verbatim under /DCTDecode, so nothing here decodes an image."""
    i = 2
    while i < len(data) - 9:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        # SOF0..SOF15, skipping the four that are not frame headers
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            h = int.from_bytes(data[i + 5:i + 7], "big")
            w = int.from_bytes(data[i + 7:i + 9], "big")
            return w, h, data[i + 9]
        i += 2 + int.from_bytes(data[i + 2:i + 4], "big")
    raise ValueError("no JPEG frame header — is that really a JPEG?")


def _content(lines: "list[str]", pictures: "list[tuple]") -> bytes:
    """One page: words from the top, pictures laid out below them."""
    out = ["BT", "/F1 22 Tf", "64 740 Td", "28 TL"]
    for i, line in enumerate(lines):
        out.append(f"({_escape(line)}) Tj" if i == 0
                   else f"T* ({_escape(line)}) Tj")
    out.append("ET")

    # Below the last line of text, side by side if there are two.
    top = 740 - 28 * max(1, len(lines)) - 40
    if pictures:
        room = PAGE_W - 128
        gap = 24 if len(pictures) > 1 else 0
        each = (room - gap * (len(pictures) - 1)) / len(pictures)
        x = 64.0
        for name, w, h in pictures:
            drawn_h = each * h / w
            y = top - drawn_h
            out.append(f"q {each:.2f} 0 0 {drawn_h:.2f} {x:.2f} {y:.2f} cm "
                       f"/{name} Do Q")
            x += each + gap
    return "\n".join(out).encode("latin-1", "replace")


def build(pages: "list") -> bytes:
    """`pages` is a list of pages.

    A page is either a list of text lines, or a dict:
        {"lines": [...], "images": [Path, Path]}
    """
    objects: "list[bytes]" = []

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)                      # object numbers are 1-based

    catalog = add(b"")                           # reserved, filled in below
    pages_obj = add(b"")
    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
               b"/Encoding /WinAnsiEncoding >>")

    kids = []
    for spec in pages:
        lines = spec["lines"] if isinstance(spec, dict) else spec
        files = spec.get("images", []) if isinstance(spec, dict) else []

        pictures, xobjects = [], []
        for n, path in enumerate(files, 1):
            raw = Path(path).read_bytes()
            w, h, comps = jpeg_size(raw)
            space = b"/DeviceGray" if comps == 1 else b"/DeviceRGB"
            # The JPEG goes in BYTE FOR BYTE. /DCTDecode is the PDF
            # saying "this stream is a JPEG, decode it yourself".
            img = add(b"<< /Type /XObject /Subtype /Image "
                      b"/Width " + str(w).encode() + b" /Height " + str(h).encode()
                      + b" /ColorSpace " + space + b" /BitsPerComponent 8 "
                      b"/Filter /DCTDecode /Length " + str(len(raw)).encode()
                      + b" >>\nstream\n" + raw + b"\nendstream")
            name = f"Im{n}"
            pictures.append((name, w, h))
            xobjects.append(f"/{name} {img} 0 R")

        stream = _content(lines, pictures)
        contents = add(b"<< /Length " + str(len(stream)).encode() + b" >>\n"
                       b"stream\n" + stream + b"\nendstream")
        resources = (b"<< /Font << /F1 " + str(font).encode() + b" 0 R >>"
                     + (b" /XObject << " + " ".join(xobjects).encode() + b" >>"
                        if xobjects else b"") + b" >>")
        page = add(
            b"<< /Type /Page /Parent " + str(pages_obj).encode() + b" 0 R "
            b"/MediaBox [0 0 " + f"{PAGE_W} {PAGE_H}".encode() + b"] "
            b"/Resources " + resources + b" "
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
