#!/usr/bin/env python3
"""Files someone drops on the page: photographs, a film, a document,
the mark, the typeface.

Each is judged by what is INSIDE it, never by its name — a text file
called .pdf, a photograph called .woff2 and a desktop font called
.woff2 are all refused, by `tools/dossier.py`, `tools/logo.py` and
`tools/fonts.py` respectively. What belongs here is the part that
touches the repository: where the bytes land, and what the content
file is told about them.

A photograph arrives WITH its description or not at all. That is the
whole reason attaching is a verb here rather than `image` being an
editable field: a photograph with no `alt` is the exact gap it was
added to close, and the moment someone attaches one is the only moment
they know what it shows.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from objects import blocks

from . import surgery as s
from .blocks import _projects, apply_edit


# What a photograph may be. Checked by its s.CONTENT, not its name: a
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
        raise s.Refused("that file has no usable name")
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
        raise s.Refused("only a reference carries a photograph today")

    alt = alt.strip()
    if not alt:
        raise s.Refused("a photograph needs a description — what does it show?")
    if s.UNWRITTEN in alt:
        raise s.Refused("that is the placeholder, not a description")
    if len(alt) > s.MAX_LEN:
        raise s.Refused(f"{len(alt)} characters; the limit is {s.MAX_LEN}")
    s.plain(alt, "that description")

    if not raw:
        raise s.Refused("no file arrived")
    if len(raw) > MAX_IMAGE:
        raise s.Refused(f"{len(raw) // 1024 // 1024}MB; the limit is 12MB")

    kind_of = next((k for sig, k in MAGIC.items() if raw.startswith(sig)), None)
    if kind_of is None and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        kind_of = "webp"
    if kind_of is None:
        raise s.Refused("that is not a JPEG, PNG or WebP — whatever it is named")

    # The extension comes from the s.CONTENT, not the name it arrived
    # with. A PNG called `.jpg` is a thing people really do send, and
    # a file whose name lies about what it is will mislead every tool
    # that touches it afterwards.
    stem = _safe_name(filename).rsplit(".", 1)[0]
    name = f"{stem}.{kind_of}"
    dest = s.ROOT / "content" / name
    # Never overwrite. Another object may be pointing at the file that is
    # already there, and replacing it would change that one silently.
    n = 2
    while dest.exists() and dest.read_bytes() != raw:
        name = f"{stem}-{n}.{kind_of}"
        dest = s.ROOT / "content" / name
        n += 1

    dest.write_bytes(raw)
    try:
        # One candidate, both fields. Either the photograph and its
        # description land together or neither does.
        candidate = apply_edit(kind, index, "alt", alt, allow_locked=True)
        candidate = apply_edit(kind, index, "image", name,
                               allow_locked=True, source=candidate)
        return s.commit(candidate, f"{name} attached to {kind} {index}")
    except Exception:
        # The file was written before the content was; if the content
        # would not take it, the file should not be left behind either.
        if dest.exists():
            dest.unlink()
        raise


def attach_photo(project_id: str, filename: str, raw: bytes, alt: str) -> str:
    """A photograph into a project's reel.

    Unlike a reference's single image, this is a new OBJECT rather than
    a field — so it appends rather than replaces, and a project's reel
    grows by dropping one more on it.

    Everything that guards `attach()` guards this: the description is
    required and arrives with the file, the type comes from the content
    and not from the name, and nothing is ever overwritten.
    """
    alt = s.plain(alt.strip(), "that description")
    if not alt:
        raise s.Refused("a photograph needs a description — what does it show?")
    if s.UNWRITTEN in alt:
        raise s.Refused("that is the placeholder, not a description")
    if len(alt) > s.MAX_LEN:
        raise s.Refused(f"{len(alt)} characters; the limit is {s.MAX_LEN}")

    if not raw:
        raise s.Refused("no file arrived")
    if len(raw) > MAX_IMAGE:
        raise s.Refused(f"{len(raw) // 1024 // 1024}MB; the limit is 12MB")

    kind_of = next((k for sig, k in MAGIC.items() if raw.startswith(sig)), None)
    if kind_of is None and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        kind_of = "webp"
    if kind_of is None:
        raise s.Refused("that is not a JPEG, PNG or WebP — whatever it is named")

    _, fm, _ = s.front(s.CONTENT.read_text(encoding="utf-8"))
    if not any(p.get("id") == project_id for p in _projects(fm)):
        raise s.Refused(f"no project has the id {project_id!r}")

    stem = _safe_name(filename).rsplit(".", 1)[0] or project_id
    name = f"{stem}.{kind_of}"
    dest = s.ROOT / "content" / name
    n = 2
    while dest.exists() and dest.read_bytes() != raw:
        name = f"{stem}-{n}.{kind_of}"
        dest = s.ROOT / "content" / name
        n += 1
    dest.write_bytes(raw)

    try:
        text = s.CONTENT.read_text(encoding="utf-8")
        head, fm, tail = s.front(text)
        at = s.insert_at(fm, "extra.photo")
        block = (f"[[extra.photo]]\n"
                 f'project = "{project_id}"\n'
                 f'file = "{name}"\n'
                 f'alt = "{s.quote(alt)}"\n')
        fm = fm[:at] + block + "\n" + fm[at:]
        return s.commit(head + "+++" + fm + tail, f"{name} added to {project_id}")
    except Exception:
        if dest.exists():
            dest.unlink()
        raise


def remove_photo(file: str) -> str:
    """One photograph out of a reel. The file stays — another may use it."""
    text = s.CONTENT.read_text(encoding="utf-8")
    head, fm, tail = s.front(text)
    shots = blocks(fm, "extra.photo")
    where = [i for i, s in enumerate(shots) if s.get("file") == file]
    if not where:
        raise s.Refused(f"no photograph named {file!r}")
    begin, end = s.block_span(fm, "extra.photo", where[0])
    fm = fm[:begin] + fm[end:]
    return s.commit(head + "+++" + fm + tail, f"{file} removed from its project")


MAX_FILM = 120 * 1024 * 1024


def _is_mp4(raw: bytes) -> bool:
    """An MP4 by its box structure, never by its name.

    The first box is a `ftyp` whose type sits at offset 4. That is the
    signature; the four bytes before it are the box length. A `.mp4`
    that does not begin this way is something else wearing the name.
    """
    return len(raw) > 12 and raw[4:8] == b"ftyp"


def attach_showreel(filename: str, raw: bytes) -> str:
    """The film, or its poster — whichever was dropped.

    ONE VERB, because the file says which it is. The slot takes an MP4
    and a still, and asking a person to tell the panel which of the two
    they just chose is asking them to repeat what the file already
    knows.

    They are refused apart in the sense that matters: `content-check.py`
    reports a film with no poster, because a video with no poster is a
    black rectangle until it is pressed. Both can be dropped in either
    order, and the message says what is still missing.
    """
    if not raw:
        raise s.Refused("no file arrived")

    video_dir = s.ROOT / "static" / "video"
    video_dir.mkdir(parents=True, exist_ok=True)

    if _is_mp4(raw):
        if len(raw) > MAX_FILM:
            raise s.Refused(f"{len(raw) // 1024 // 1024}MB; the limit is "
                          f"{MAX_FILM // 1024 // 1024}MB. A showreel of 60 to "
                          f"90 seconds should be well under it")
        (video_dir / "showreel.mp4").write_bytes(raw)
        message = s.write_front_field("video", "video/showreel.mp4")
        still = not (video_dir / "poster.jpg").exists()
        return (f"{message} — now drop a poster image on the same slot"
                if still else message)

    kind = next((k for sig, k in MAGIC.items() if raw.startswith(sig)), None)
    if kind is None and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        kind = "webp"
    if kind is None:
        raise s.Refused("that is neither an MP4 nor an image — whatever it is "
                      "named. The slot takes the film and the still it shows "
                      "before it is pressed")
    if len(raw) > MAX_IMAGE:
        raise s.Refused(f"{len(raw) // 1024 // 1024}MB; the limit is 12MB")

    # Always .jpg on disk whatever arrived, because the s.front matter and
    # `content-check.py` both name `video/poster.jpg`. The bytes are
    # untouched — only the name is settled.
    (video_dir / "poster.jpg").write_bytes(raw)
    message = s.write_front_field("poster", "video/poster.jpg")
    missing = not (video_dir / "showreel.mp4").exists()
    return (f"{message} — the film itself is still to come"
            if missing else message)


def remove_showreel() -> str:
    """Take the film off, and its poster with it."""
    _, fm, _ = s.front(s.CONTENT.read_text(encoding="utf-8"))
    current = re.search(r'^video\s*=\s*"([^"]*)"', fm, re.M)
    poster = re.search(r'^poster\s*=\s*"([^"]*)"', fm, re.M)
    if not (current and current.group(1)):
        raise s.Refused("there is no showreel to remove")

    s.write_front_field("video", "")
    message = s.write_front_field("poster", "")
    for rel in (current.group(1), poster.group(1) if poster else ""):
        if rel:
            f = s.ROOT / "static" / rel
            if f.is_file():
                f.unlink()
    return message.replace("poster updated", "the showreel removed")


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

    _, fm, _ = s.front(s.CONTENT.read_text(encoding="utf-8"))
    concepts = blocks(fm, "extra.concepts")
    if not 1 <= concept <= len(concepts):
        raise s.Refused(f"there is no concept {concept}")

    alt = alt.strip()
    if not alt:
        raise s.Refused("a document needs a description — what is it?")
    if s.UNWRITTEN in alt:
        raise s.Refused("that is the placeholder, not a description")
    if len(alt) > s.MAX_LEN:
        raise s.Refused(f"{len(alt)} characters; the limit is {s.MAX_LEN}")
    s.plain(alt, "that description")

    if not raw:
        raise s.Refused("no file arrived")

    stem = _safe_name(filename).rsplit(".", 1)[0].lower()
    slug = re.sub(r"[^a-z0-9-]+", "-", stem).strip("-")[:38] or f"concept-{concept}"
    if len(slug) < 3:
        slug = f"concept-{concept}"

    with tempfile.TemporaryDirectory() as tmp:
        dropped = Path(tmp) / "dropped"
        dropped.write_bytes(raw)
        try:
            pages = render_pdf(dropped, slug, s.ROOT / "content")
        except PdfRejected as no:
            # The checker's words, not ours. It is the thing that looked.
            raise s.Refused(str(no))

    # Replace whatever this concept had.
    #
    # NOTHING IS DELETED UNTIL THE WRITE HAS SUCCEEDED. The first version
    # removed the old pages here, before rewriting the s.front matter, and
    # when the rewrite then failed it left a concept pointing at pages
    # that no longer existed — the files gone, the entry still there.
    # The old images are taken away at the end, or not at all.
    text = s.CONTENT.read_text(encoding="utf-8")
    head, fm, tail = s.front(text)
    superseded = ""
    for i, doc in enumerate(blocks(fm, "extra.dossier")):
        if doc.get("concept", "").strip() != str(concept):
            continue
        superseded = doc.get("id", "").strip()
        # `s.block_span` counts from ZERO — `enumerate` without a start,
        # therefore. Handing it a 1-based index asks for a block one past
        # the end, which it refuses, and the refusal arrives after the
        # pages have already been written.
        start, end = s.block_span(fm, "extra.dossier", i)
        fm = fm[:start] + fm[end:]
        break

    block = (f"[[extra.dossier]]\n"
             f"concept = {concept}\n"
             f'id = "{slug}"\n'
             f"pages = {len(pages)}\n"
             # `s.quote()` escapes the contents; the quotes themselves are
             # the caller's, as everywhere else in this file. Without
             # them the s.front matter is not TOML and the build stops.
             f'alt = "{s.quote(alt)}"\n')
    at = s.insert_at(fm, "extra.dossier")
    fm = fm[:at] + block + "\n" + fm[at:]
    message = s.commit(head + "+++" + fm + tail,
                      f"{len(pages)}-page document on concept {concept}")

    # Written and accepted. Now the pages nothing points at any more.
    if superseded and superseded != slug:
        for leaf in (s.ROOT / "content").glob(f"dossier-{superseded}-p*.jpg"):
            leaf.unlink()
    return message


def remove_dossier(concept: int) -> str:
    """Take the document off a concept, pages and all.

    The panel could s.put a document on a card and never take it off
    again, which left the only way back a hand edit of the s.front matter
    plus six stray images nobody would think to delete. Every other
    thing the panel adds has a way out; this is that way.
    """
    text = s.CONTENT.read_text(encoding="utf-8")
    head, fm, tail = s.front(text)

    for i, doc in enumerate(blocks(fm, "extra.dossier")):
        if doc.get("concept", "").strip() != str(concept):
            continue
        slug = doc.get("id", "").strip()
        start, end = s.block_span(fm, "extra.dossier", i)
        fm = fm[:start] + fm[end:]
        message = s.commit(head + "+++" + fm + tail,
                          f"the document on concept {concept} removed")
        # The pages only once the page itself no longer names them, so
        # a refusal leaves a document that still works.
        if slug:
            for leaf in (s.ROOT / "content").glob(f"dossier-{slug}-p*.jpg"):
                leaf.unlink()
        return message

    raise s.Refused(f"concept {concept} has no document")


def set_logo(slot: str, raw: bytes) -> str:
    """Put one of their three marks in place, and rebuild what it feeds.

    The validation is not here: `tools/logo.py` owns what a usable mark
    is, because `tools/icons.py` has to agree with it — a file this
    accepted and that one then refused would leave the tab showing the
    placeholder with nothing saying why.
    """
    import logo

    if len(raw) > MAX_IMAGE:
        raise s.Refused(f"{len(raw) // 1024 // 1024}MB; the limit is "
                      f"{MAX_IMAGE // 1024 // 1024}MB")
    try:
        placed = logo.accept(slot, raw)
    except logo.Rejected as no:
        raise s.Refused(str(no)) from None

    import subprocess
    out = subprocess.run([sys.executable, str(s.ROOT / "tools" / "icons.py")],
                         capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        why = (out.stderr or out.stdout or "the icons could not be built")
        raise s.Refused(f"{placed}, but the icons could not be rebuilt: "
                      f"{why.strip().splitlines()[-1].strip()}")
    return f"{placed}; the tab, the touch icon and the share image were rebuilt"


def remove_logo(slot: str) -> str:
    """Take one of their marks away again, and draw the stand-in back."""
    import logo

    if slot not in logo.SLOTS:
        raise s.Refused(f"{slot!r} is not one of {', '.join(logo.SLOTS)}")
    name = logo.SLOTS[slot][0]
    path = s.ROOT / "static" / name
    if not path.exists():
        raise s.Refused(f"there is no {name} to remove")
    path.unlink()

    import subprocess
    out = subprocess.run([sys.executable, str(s.ROOT / "tools" / "icons.py")],
                         capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        why = (out.stderr or out.stdout or "the icons could not be built")
        raise s.Refused(f"{name} was removed, but the icons could not be "
                      f"redrawn: {why.strip().splitlines()[-1].strip()}")
    return f"{name} removed; the drawn mark is back"


def set_font(slot: str, raw: bytes) -> str:
    """Put one webfont in place, and regenerate the stylesheet it feeds.

    Validation lives in `tools/fonts.py` for the same reason the logo's
    lives in `tools/logo.py`: the tool that writes the stylesheet has
    to agree with whatever accepted the file, or a face would be in
    place with no rule loading it.
    """
    import fonts

    if len(raw) > fonts.MAX_FACE:
        raise s.Refused(f"{len(raw) // 1024}KB; the limit is "
                      f"{fonts.MAX_FACE // 1024}KB")
    try:
        placed = fonts.accept(slot, raw)
    except fonts.Rejected as no:
        raise s.Refused(str(no)) from None

    import subprocess
    out = subprocess.run([sys.executable, str(s.ROOT / "tools" / "fonts.py")],
                         capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        why = (out.stderr or out.stdout or "the stylesheet could not be written")
        raise s.Refused(f"{placed}, but the stylesheet could not be written: "
                      f"{why.strip().splitlines()[-1].strip()}")
    return f"{placed}; the stylesheet was rebuilt"


def remove_font(slot: str) -> str:
    """Take one face away, and leave the stack to its fallback."""
    import fonts

    if slot not in fonts.SLOTS:
        raise s.Refused(f"{slot!r} is not one of {', '.join(fonts.SLOTS)}")
    name = fonts.SLOTS[slot][0]
    path = s.ROOT / "static" / "fonts" / name
    if not path.exists():
        raise s.Refused(f"there is no {name} to remove")
    path.unlink()

    import subprocess
    out = subprocess.run([sys.executable, str(s.ROOT / "tools" / "fonts.py")],
                         capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        why = (out.stderr or out.stdout or "the stylesheet could not be written")
        raise s.Refused(f"{name} was removed, but the stylesheet could not be "
                      f"rewritten: {why.strip().splitlines()[-1].strip()}")
    return f"{name} removed; the rest of the stack takes over"
