#!/usr/bin/env python3
"""The real content, on this machine, without ever committing it.

    python3 tools/dropin.py --init     # create _dropin/ with a slot per placeholder
    python3 tools/dropin.py            # assemble _local/ and say what is still missing
    python3 tools/dropin.py --serve    # assemble, then serve it

WHY THERE ARE TWO COPIES OF THE SITE.

This repository is public. The client's brand is an established
trademark, his references are unverified until he says otherwise, and
his photographs are his. None of that may ever be committed — see
NOTICE — and the surest way to keep a file out of a commit is for it to
live somewhere git was told to ignore.

So the tracked tree keeps the placeholders and stays publishable, and
the real content lives in `_dropin/`, which is ignored. This script
assembles the two into `_local/`, which is also ignored, and that is the
site you look at.

Nothing here writes to the tracked tree. There is no flag to make it.

HOW THE SLOTS WORK.

`_dropin/` mirrors the repository's own paths. A file at
`_dropin/content/work-01.jpg` lands at `content/work-01.jpg`. There is
no manifest and no second format to learn: it is the same layout, and
anything you put there wins.

    _dropin/content/_index.md        every text placeholder on the page
    _dropin/config.toml              address, legal notice, social links
    _dropin/content/work-01.jpg      Reference 01's photograph
    _dropin/static/video/            the showreel and its poster

WHY A WHOLE COPY RATHER THAN A CLEVER OVERLAY.

Because `_local/` is then an ordinary checkout, and every tool already
written works there with no changes at all — `zola serve`, the studio
panel, `objects.py`, `content-check.py`. Each one finds its root from
its own location, so run from `_local/` they check `_local/`. A partial
overlay would have needed all of them taught about a second root, which
is four more places to get it wrong.
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DROPIN = ROOT / "_dropin"
LOCAL = ROOT / "_local"

# Copied into the shadow. Everything else — .git, public/, node_modules,
# the shadow itself, the drop-in itself — is either generated, enormous,
# or would make the copy recursive.
SOURCES = ("config.toml", "content", "templates", "static", "tools",
           "package.json", "tsconfig.json", "src")

# Generated inside the shadow and deliberately left alone between runs:
# deleting them would make every preview a cold build.
KEEP = {"public", "processed_images"}


def ignored(_dir, names):
    return [n for n in names if n in KEEP or n == ".DS_Store" or n.endswith(".map")]


def assemble() -> list[str]:
    """Copy the tracked tree into _local/, then let _dropin/ overwrite it."""
    LOCAL.mkdir(exist_ok=True)
    (LOCAL / ".gitignore").write_text("*\n", encoding="utf-8")

    for name in SOURCES:
        src = ROOT / name
        if not src.exists():
            continue
        dest = LOCAL / name
        if src.is_dir():
            shutil.copytree(src, dest, dirs_exist_ok=True, ignore=ignored)
        else:
            shutil.copy2(src, dest)

    placed = []
    if DROPIN.is_dir():
        for src in sorted(DROPIN.rglob("*")):
            if not src.is_file() or src.name in {".DS_Store", "README.md"}:
                continue
            rel = src.relative_to(DROPIN)
            dest = LOCAL / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            placed.append(str(rel))
    return placed


def check() -> None:
    """Run the repository's own checks, against the shadow.

    Not reimplemented here: `_local/tools/` is a copy, so each script
    resolves its own root to `_local/` and checks the real content. The
    gate that decides whether the published site may go live is the same
    gate, pointed at the version with the real names in it.
    """
    for script in ("objects.py", "content-check.py"):
        path = LOCAL / "tools" / script
        if not path.exists():
            continue
        out = subprocess.run([sys.executable, str(path)],
                             capture_output=True, text=True, cwd=LOCAL)
        text = (out.stdout + out.stderr).strip()
        if text:
            print("\n".join("  " + ln for ln in text.splitlines()))


def init() -> int:
    """Create _dropin/ with a slot for every placeholder on the page."""
    if DROPIN.exists():
        print(f"\n  {DROPIN.name}/ is already there — leaving it alone.\n")
        return 0

    (DROPIN / "content").mkdir(parents=True)
    (DROPIN / "static" / "video").mkdir(parents=True)

    # The real files, copied as they stand. Editing a copy of the thing
    # itself beats filling in a form that has to be translated back: it
    # is TOML either way, and this way there is no second format to keep
    # in step with the first.
    shutil.copy2(ROOT / "content" / "_index.md", DROPIN / "content" / "_index.md")
    shutil.copy2(ROOT / "config.toml", DROPIN / "config.toml")

    (DROPIN / "README.md").write_text(README, encoding="utf-8")
    print(f"""
  {DROPIN.name}/ is ready.

    {DROPIN.name}/content/_index.md   every text placeholder on the page
    {DROPIN.name}/config.toml         address, legal notice, social links
    {DROPIN.name}/content/            photographs go here
    {DROPIN.name}/static/video/       the showreel and its poster

  Read {DROPIN.name}/README.md, then:

    python3 tools/dropin.py --serve
""")
    return 0


README = """# Drop the real content here

This folder is **ignored by git**. Nothing in it can reach the public
repository, which is the point: the client's names, photographs and
showreel live here and nowhere else.

The folder mirrors the repository's own paths. A file here lands at the
same path in the preview — there is no manifest to keep up to date.

## See it

    python3 tools/dropin.py --serve

That assembles `_local/` — the tracked site with everything here laid
over it — and serves that. `./preview.sh` still shows the placeholder
site, which is the one that gets published; use this for the real thing.

## The slots

### Text

`content/_index.md` and `config.toml` are copies of the real files. Edit
them here. Everything marked *"supplied at handover"* is a placeholder
waiting for you, and so is every empty `url`, `email` and legal field in
`config.toml`.

### Photographs

Drop them in `content/` and point an entry at one:

    image = "work-01.jpg"
    alt   = "what the photograph shows, for someone who cannot see it"

`alt` is not optional — the build refuses an image without one. JPEG,
PNG or WebP. Roughly 1600px on the long edge is plenty; the site resizes
and converts to WebP by itself.

### The showreel

    static/video/showreel.mp4     the film
    static/video/poster.jpg       the still shown before it plays

and in `content/_index.md`:

    video  = "video/showreel.mp4"
    poster = "video/poster.jpg"

**The poster is required when there is a video.** The player does not
load the film until someone presses play, so with no poster the section
is a black rectangle — the one state worse than the empty slot that is
there now.

MP4 (H.264/AAC) plays everywhere that matters. Keep it under ~50MB: it
is served as a plain file, so the viewer waits for exactly as long as it
takes to arrive.

## What is still missing

    python3 tools/dropin.py

Assembles the preview and then runs the repository's own checks against
it — the same gate that decides whether the site may go live, pointed at
the version with the real names in. It lists what is still unfilled.
"""


def serve() -> int:
    if not shutil.which("zola"):
        print("\n  Zola is not installed. ./preview.sh installs it.\n")
        return 1
    print("\n  Serving the real content. Ctrl-C to stop.\n")
    return subprocess.call(
        ["zola", "--root", str(LOCAL), "serve", "--interface", "127.0.0.1"]
    )


def main(argv: list[str]) -> int:
    if "--init" in argv:
        return init()

    if not DROPIN.exists():
        print("\n  no _dropin/ yet — run: python3 tools/dropin.py --init\n")
        return 1

    placed = assemble()
    print(f"\n  _local/ assembled, {len(placed)} file(s) from _dropin/:")
    for rel in placed:
        print(f"    {rel}")
    if not placed:
        print("    (none — the preview is the placeholder site)")

    check()

    if "--serve" in argv:
        return serve()
    print("\n  See it with: python3 tools/dropin.py --serve\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
