"""A dropped PDF, checked for real and turned into pages.

    python3 tools/dossier.py <file.pdf> <slug>          # into content/
    python3 tools/dossier.py --check <file>             # verdict only

WHY THE PDF NEVER REACHES THE SITE
==================================
The brief is "show it, but it must not be downloadable". You cannot
withhold a file the browser is displaying — if it renders, the bytes are
already on the reader's machine. So the PDF is not displayed. It is
rasterised HERE, once, and only the page images are published. There is
no PDF on the server to download, which is the one version of that
promise that is actually true.

Zola copies everything under `content/` into the built site — measured:
`public/work-r1-a-01.jpg` exists. So the PDF must never be put there.
Its pages go to `content/`; the PDF itself stays wherever it was
dropped, outside the tracked tree.

It also disposes of the other problem with publishing a PDF: a PDF can
carry JavaScript, embedded files and external references. A JPEG of a
page carries a picture of a page.

THE CHECK IS NOT THE EXTENSION
==============================
"No txt renamed pdf or whatever." Nothing here looks at the file name.
A file is a PDF if it begins with the signature, ends with the trailer,
parses in a real PDF parser, and — the only proof that counts — every
one of its pages actually rasterises.
"""
from __future__ import annotations

import re
import shutil
import tempfile
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"

MIN_BYTES = 200
MAX_BYTES = 40 * 1024 * 1024
MAX_PAGES = 16
PAGE_WIDTH = 1600          # enough to read at a phone's 2x, and no more
JPEG_QUALITY = 88

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$")


class Rejected(Exception):
    """Not a PDF, or not one we will take. The message is for a person."""


def _tool(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise Rejected(
            f"`{name}` is not installed, so the PDF cannot be checked or "
            f"turned into pages. On a Mac: brew install poppler")
    return found


def structurally_a_pdf(data: bytes) -> None:
    """The bytes, before any parser is asked. Cheap and decisive."""
    if len(data) < MIN_BYTES:
        raise Rejected(f"that file is {len(data)} bytes — too small to be a "
                       f"PDF at all")
    if len(data) > MAX_BYTES:
        raise Rejected(f"that file is {len(data) // (1024 * 1024)}MB, over the "
                       f"{MAX_BYTES // (1024 * 1024)}MB limit")

    # At offset zero, not "somewhere near the start". A file with junk in
    # front of the signature is a file something has been done to.
    if not data.startswith(b"%PDF-"):
        head = data[:8]
        raise Rejected(
            f"that is not a PDF. A PDF begins with %PDF- and this one begins "
            f"{head!r}. Renaming a file does not change what is inside it")
    if not re.match(rb"%PDF-[12]\.\d", data[:10]):
        raise Rejected("that claims to be a PDF but not of a version that "
                       "exists")

    # The trailer. Some writers leave a little padding after it.
    if b"%%EOF" not in data[-2048:]:
        raise Rejected("that PDF has no end-of-file marker in its last 2KB — "
                       "it is truncated, or it is not a whole file")


def pages_in(path: Path) -> int:
    """Ask a real parser. This is what a renamed text file cannot survive."""
    out = subprocess.run([_tool("pdfinfo"), str(path)],
                         capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        first = (out.stderr or "").strip().splitlines()
        why = first[0] if first else "no reason given"
        raise Rejected(f"a PDF parser could not read that file: {why}")

    fields = dict(
        (k.strip(), v.strip())
        for k, _, v in (line.partition(":") for line in out.stdout.splitlines())
        if _)

    if fields.get("Encrypted", "no").lower().startswith("yes"):
        raise Rejected("that PDF is encrypted, so its pages cannot be read")

    try:
        count = int(fields.get("Pages", "0"))
    except ValueError:
        count = 0
    if count < 1:
        raise Rejected("that PDF reports no pages")
    if count > MAX_PAGES:
        raise Rejected(f"that PDF has {count} pages, over the {MAX_PAGES}-page "
                       f"limit — every page becomes an image the reader has to "
                       f"download")
    return count


def accept(path: Path) -> int:
    """Everything short of rendering. Returns the page count."""
    if not path.is_file():
        raise Rejected(f"there is no file at {path}")
    structurally_a_pdf(path.read_bytes())
    return pages_in(path)


def render(path: Path, slug: str, into: Path = CONTENT) -> "list[Path]":
    """Pages to JPEG. The last and strongest check: a file that will not
    rasterise is not a document, whatever its header says."""
    if not SLUG.match(slug):
        raise Rejected(f"`{slug}` is not a usable name: lower case letters, "
                       f"digits and hyphens, 3 to 40 characters")
    expected = accept(path)

    into.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        """Rasterise somewhere empty first.

        `pdftoppm` appends its own `-1`, `-2` to whatever stem it is
        given, and pads differently depending on the page count. Writing
        straight into content/ meant globbing for the results among
        files that were already there, and the first version of this
        matched its own output and renamed nothing — the pages came out
        as `...-p-1.jpg`. An empty directory has nothing to confuse."""
        out = subprocess.run(
            [_tool("pdftoppm"), "-jpeg", "-jpegopt", f"quality={JPEG_QUALITY}",
             "-scale-to-x", str(PAGE_WIDTH), "-scale-to-y", "-1",
             str(path), str(Path(tmp) / "page")],
            capture_output=True, text=True, timeout=300)
        if out.returncode != 0:
            raise Rejected(f"that PDF would not render: "
                           f"{(out.stderr or '').strip()[:200]}")

        made = sorted(Path(tmp).glob("page-*.jpg"),
                      key=lambda f: int(f.stem.rsplit("-", 1)[1]))
        if len(made) != expected:
            raise Rejected(f"that PDF said it had {expected} pages but "
                           f"produced {len(made)} — it is damaged")

        # Only once every page exists is the old set replaced. A failure
        # half way through leaves what was there, rather than a gap.
        for stale in into.glob(f"dossier-{slug}-p*.jpg"):
            stale.unlink()
        final = []
        for n, f in enumerate(made, start=1):
            want = into / f"dossier-{slug}-p{n:02d}.jpg"
            want.write_bytes(f.read_bytes())
            final.append(want)
    return final


def main(argv: "list[str]") -> int:
    if len(argv) >= 3 and argv[1] == "--check":
        try:
            n = accept(Path(argv[2]))
        except Rejected as no:
            print(f"\n  refused: {no}\n")
            return 1
        print(f"\n  a real PDF, {n} page(s)\n")
        return 0

    if len(argv) < 3:
        print(__doc__)
        return 2

    try:
        made = render(Path(argv[1]), argv[2])
    except Rejected as no:
        print(f"\n  refused: {no}\n")
        return 1

    print(f"\n  {len(made)} page(s) written to content/")
    for f in made:
        print(f"    {f.name}  {f.stat().st_size // 1024}KB")
    print(f"""
  Add this to content/_index.md:

[[extra.dossier]]
concept = <which concept it belongs to, 1-based>
id = "{argv[2]}"
pages = {len(made)}
alt = "<what the document is, for someone who cannot see it>"
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
