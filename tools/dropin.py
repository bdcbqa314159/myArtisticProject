#!/usr/bin/env python3
"""The real content, on this machine, without ever committing it.

    python3 tools/dropin.py --init     # create _dropin/, full of stand-in content
    python3 tools/dropin.py --init --bare   # ...or with the slots empty
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
    _dropin/documents/concept-2.pdf  the document behind concept 2
    _dropin/documents/concept-2.txt  what that document is, one line

THE ONE SLOT THAT IS NOT A MIRRORED PATH.

A PDF has no place in the repository by design — everything under
`content/` is copied into the built site, so a PDF left there would be
published and downloadable, which is the one thing a dossier exists to
prevent. It therefore cannot mirror a path, because there is no path to
mirror.

So `documents/` is named for the concept it belongs to, and the PDF
never travels: `tools/dossier.py` checks it is really a PDF, turns it
into page images in `_local/content/`, and the file itself stays here,
ignored, where it was dropped.

WHY A WHOLE COPY RATHER THAN A CLEVER OVERLAY.

Because `_local/` is then an ordinary checkout, and every tool already
written works there with no changes at all — `zola serve`, the studio
panel, `objects.py`, `content-check.py`. Each one finds its root from
its own location, so run from `_local/` they check `_local/`. A partial
overlay would have needed all of them taught about a second root, which
is four more places to get it wrong.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dropin_samples as samples

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
            # `documents/` is not a mirrored path and must not be copied:
            # the PDF stays here and only its pages travel. See
            # `documents()` below.
            if rel.parts and rel.parts[0] == "documents":
                continue
            dest = LOCAL / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            placed.append(str(rel))
    return placed


DOCUMENTS = DROPIN / "documents"
CONCEPT_PDF = re.compile(r"^concept-(\d+)\.pdf$", re.IGNORECASE)


def _replace_dossier(concept: int, slug: str, pages: int, alt: str) -> str:
    """Point one concept at its document, in `_local/content/_index.md`.

    The entry is rewritten rather than added to, because a card shows one
    document and the tracked page already carries a placeholder for
    concept 2. Returns the id of whatever it replaced, or "".
    """
    page = LOCAL / "content" / "_index.md"
    text = page.read_text(encoding="utf-8")

    superseded = ""

    # Each block by its bounds: from its header to whatever starts next.
    blocks = []
    i = 0
    while True:
        at = text.find("[[extra.dossier]]", i)
        if at == -1:
            break
        end = len(text)
        for marker in ("\n[[", "\n# ----"):
            nxt = text.find(marker, at + 1)
            if nxt != -1:
                end = min(end, nxt + 1)
        blocks.append((at, end, text[at:end]))
        i = at + 1

    for at, end, body in reversed(blocks):
        if re.search(rf"^concept\s*=\s*{concept}\s*$", body, re.M):
            found = re.search(r'^id\s*=\s*"([^"]*)"', body, re.M)
            superseded = found.group(1) if found else ""
            text = text[:at] + text[end:]

    entry = (f"[[extra.dossier]]\n"
             f"concept = {concept}\n"
             f'id = "{slug}"\n'
             f"pages = {pages}\n"
             f'alt = "{alt}"\n\n')

    # INSIDE the front matter, not at the end of the file. `_index.md` is
    # `+++ TOML +++ body`, and appending to the end put the block in the
    # markdown body where nothing reads it: the page built, every check
    # passed, and the document simply was not there.
    close = text.find("\n+++", text.find("+++") + 3)
    if close == -1:
        raise SystemExit("  _local/content/_index.md has no closing +++")
    text = text[:close + 1] + entry + text[close + 1:]
    page.write_text(text, encoding="utf-8")
    return superseded


def documents() -> "tuple[list[str], list[str]]":
    """Each dropped PDF, checked and turned into the pages of a dossier.

    Returns what was placed, and what was refused — refusals are
    reported rather than raised, so one bad file does not stop the rest
    of the site being assembled.
    """
    if not DOCUMENTS.is_dir():
        return [], []

    sys.path.insert(0, str(ROOT / "tools"))
    import dossier                                        # noqa: E402

    placed, refused = [], []
    for src in sorted(DOCUMENTS.iterdir()):
        if not src.is_file() or src.name in {".DS_Store", "README.md"}:
            continue
        if src.suffix.lower() == ".txt":
            continue                                      # a description
        match = CONCEPT_PDF.match(src.name)
        if not match:
            refused.append(f"{src.name} — name it concept-1.pdf, "
                           f"concept-2.pdf or concept-3.pdf, for the concept "
                           f"it belongs to")
            continue

        n = int(match.group(1))
        slug = f"concept-{n}"
        beside = src.with_suffix(".txt")
        alt = (beside.read_text(encoding="utf-8").strip().replace('"', "'")
               if beside.is_file() else "")
        alt = " ".join(alt.split())[:400]
        if not alt:
            alt = f"Document du concept {n}"

        try:
            made = dossier.render(src, slug, LOCAL / "content")
        except dossier.Rejected as no:
            refused.append(f"{src.name} — {no}")
            continue

        old = _replace_dossier(n, slug, len(made), alt)
        # The placeholder's pages, now that nothing points at them.
        if old and old != slug:
            for leaf in (LOCAL / "content").glob(f"dossier-{old}-p*.jpg"):
                leaf.unlink()
        placed.append(f"documents/{src.name} → {len(made)} page(s) on concept {n}")
    return placed, refused


def check() -> None:
    """Run the repository's own checks, against the shadow.

    Not reimplemented here: `_local/tools/` is a copy, so each script
    resolves its own root to `_local/` and checks the real content. The
    gate that decides whether the published site may go live is the same
    gate, pointed at the version with the real names in it.
    """
    # Generators first. `_local/` is a real checkout, so the things the
    # site builds for itself — the saveable contact card, the icons —
    # have to be built there as well, or the gate reports a card that is
    # promised and missing and the fixture can never come out clean.
    for script in ("vcard.py", "icons.py"):
        path = LOCAL / "tools" / script
        if path.exists():
            subprocess.run([sys.executable, str(path)],
                           capture_output=True, text=True, cwd=LOCAL)

    for script in ("objects.py", "content-check.py"):
        path = LOCAL / "tools" / script
        if not path.exists():
            continue
        out = subprocess.run([sys.executable, str(path)],
                             capture_output=True, text=True, cwd=LOCAL)
        text = (out.stdout + out.stderr).strip()
        if text:
            print("\n".join("  " + ln for ln in text.splitlines()))


def init(bare: bool = False) -> int:
    """Create _dropin/, full by default.

    Empty slots are a folder of instructions. A full one is a site that
    already works — so replacing a single photograph shows what a single
    photograph does, instead of needing six references, three concepts,
    five legal fields and a film before anything can be judged at all.

    `--bare` gives the empty version, for when the real content is going
    in wholesale and the fixture would only be in the way.
    """
    if DROPIN.exists():
        print(f"\n  {DROPIN.name}/ is already there — leaving it alone.")
        print("  Delete it yourself if you want a fresh one.\n")
        return 0

    content = DROPIN / "content"
    video = DROPIN / "static" / "video"
    content.mkdir(parents=True)
    video.mkdir(parents=True)
    DOCUMENTS.mkdir(parents=True)
    (DOCUMENTS / "README.md").write_text(
        "# Les documents\n\n"
        "Un PDF par concept, nommé d'après le concept qu'il accompagne :\n\n"
        "    concept-1.pdf     le document du premier concept\n"
        "    concept-2.pdf     celui du deuxième\n"
        "    concept-3.pdf     celui du troisième\n\n"
        "À côté de chacun, un fichier `.txt` du même nom peut dire en une\n"
        "ligne ce qu'est le document — `concept-2.txt`. Sans lui le site\n"
        "met une description provisoire, que tu peux changer dans le\n"
        "panneau d'édition.\n\n"
        "Le PDF lui-même ne part jamais en ligne : il est transformé en\n"
        "images de pages, et ce sont elles seules qui vont sur le site. Il\n"
        "n'y a donc rien à télécharger — c'est voulu.\n\n"
        "Seulement de vrais PDF : renommer un fichier en `.pdf` ne suffit\n"
        "pas, le site regarde ce qu'il y a dedans et refuse le reste en\n"
        "disant pourquoi. Maximum 16 pages.\n",
        encoding="utf-8")

    source_content = (ROOT / "content" / "_index.md").read_text(encoding="utf-8")
    source_config = (ROOT / "config.toml").read_text(encoding="utf-8")

    made: list[str] = []
    if bare:
        # The real files, as they stand. It is TOML either way, so there
        # is no second format to keep in step with the first.
        (content / "_index.md").write_text(source_content, encoding="utf-8")
        (DROPIN / "config.toml").write_text(source_config, encoding="utf-8")
    else:
        scratch = DROPIN / ".scratch"
        scratch.mkdir(exist_ok=True)
        rows: "list[dict]" = []
        shots: "list[dict]" = []
        try:
            made += samples.images(content, scratch)
            made += samples.showreel(video, scratch)
            photos, rows, shots = samples.projects(content)
            made += photos
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

        have_images = len([m for m in made if m.startswith("work-")]) == 6
        have_video = "showreel.mp4" in made and "poster.jpg" in made

        (content / "_index.md").write_text(
            samples.fill_content(source_content, have_images, have_video,
                                 rows, shots),
            encoding="utf-8")
        (DROPIN / "config.toml").write_text(
            samples.fill_config(source_config), encoding="utf-8")

        # The stand-in ledger lists photographs this fixture replaces.
        # Emptying it retires them; the gate counts entries, not files.
        (content / "PLACEHOLDERS.txt").write_text("", encoding="utf-8")

    (DROPIN / "README.md").write_text(README, encoding="utf-8")

    print(f"\n  {DROPIN.name}/ is ready.\n")
    if bare:
        print("    content/_index.md   every text placeholder on the page")
        print("    config.toml         address, legal notice, social links")
        print("    content/            photographs go here")
        print("    static/video/       the showreel and its poster\n")
    else:
        print(f"    a full set of stand-in content — {len(made)} file(s) generated")
        for name in made[:10]:
            print(f"      {name}")
        if len(made) > 10:
            print(f"      … and {len(made) - 10} more")
        if rows:
            print(f"      {len(rows)} projects across the six references, "
                  f"{len(shots)} photographs")
        missing = []
        if not any(m.startswith("work-") for m in made):
            missing.append("images (needs Chrome and sips)")
        if "showreel.mp4" not in made:
            missing.append("the showreel (needs ffmpeg)")
        for m in missing:
            print(f"      — skipped: {m}")
        print("\n    Nothing here is real. Replace it a piece at a time.")
    print(f"""
  Read {DROPIN.name}/README.md, then:

    python3 tools/dropin.py --serve
""")
    return 0


README = """# The real content goes here

This folder is **ignored by git**. Nothing in it can reach the public
repository, which is the point: the client's names, photographs and
showreel live here and nowhere else.

It starts **full**, with a complete set of stand-in content, so the site
already works before you touch anything. Replace a piece at a time and
watch the real thing arrive — rather than needing six references, three
concepts, five legal fields and a film before there is anything to look
at.

**Nothing here is real.** "Test Organisation 01", "sample-fixture, not a
real record", images generated on this machine. Nothing reads as a
credential, and nothing came from anyone else's camera.

## See it

    python3 tools/dropin.py --serve

That assembles `_local/` — the tracked site with everything here laid
over it — and serves that. `./preview.sh` still shows the placeholder
site, which is the one that gets published.

## It runs as the finished site

`live = true` in this folder's `config.toml`. That is why the page wears
the real identity instead of the 10MILES demo one, and why the palette
toggle and the stand-in badges are gone — it is the launch
configuration, which is the thing worth looking at.

Safe **here and only here**: this file is ignored and nothing publishes
it. The tracked `config.toml` stays `false`, and flipping that one is a
decision made with the repository in front of you, not a side effect.

## The slots

The folder mirrors the repository's own paths. A file here lands at the
same path in the preview — there is no manifest to keep up to date.

| | |
|---|---|
| `content/_index.md` | every text placeholder: references, concepts, titles |
| `config.toml` | identity, contact, legal notice, social links |
| `content/work-01.jpg` … `work-06.jpg` | the six photographs |
| `static/video/showreel.mp4` | the film |
| `static/video/poster.jpg` | the still shown before it plays |

### Photographs

Drop one in `content/` and point an entry at it:

    image = "whatever-you-called-it.jpg"
    alt   = "what it shows, for someone who cannot see it"

`alt` is not optional — the build refuses an image without one. JPEG,
PNG or WebP; about 1600px on the long edge is plenty, and the site
resizes and converts to WebP itself.

### The showreel

**The poster is required when there is a video.** The player loads
nothing until someone presses play, so with no poster the section is a
black rectangle. MP4 (H.264/AAC) plays everywhere that matters; keep it
under ~50MB, because the viewer waits exactly as long as it takes to
arrive.

## What is still missing

    python3 tools/dropin.py

Assembles the preview, builds what the site builds for itself, and then
runs the repository's own checks against it — the same gate that decides
whether the site may go live, pointed at the version with the real names
in. Out of the box it reports nothing, because the fixture is complete.
As you replace it with real content, it will tell you what is not.

## Starting empty instead

    rm -rf _dropin && python3 tools/dropin.py --init --bare

For when the real content is going in wholesale and the fixture would
only be in the way.
"""


def serve(port: int = 1111) -> int:
    """The site, and a studio pointed at the same copy.

    The panel resolves its root from its own location, so running
    `_local/tools/studio/server.py` edits `_local` — which is the whole
    point. Started from `preview.sh` instead it edits the TRACKED page,
    and that page has no projects at all, so none of the gallery is
    reachable from it. Two sites, two panels, and each edits the one it
    is showing.
    """
    if not shutil.which("zola"):
        print("\n  Zola is not installed. ./preview.sh installs it.\n")
        return 1

    panel = LOCAL / "tools" / "studio" / "server.py"
    studio = None
    if panel.exists():
        studio = subprocess.Popen(
            [sys.executable, str(panel), str(port + 100),
             f"http://127.0.0.1:{port}"],
            stdout=subprocess.PIPE, text=True, cwd=LOCAL)
        where = (studio.stdout.readline() or "").strip() if studio.stdout else ""
        if where:
            print(f"\n  the studio, editing the real content:\n\n    {where}\n",
                  flush=True)

    print("  Serving the real content. Ctrl-C to stop.\n", flush=True)
    try:
        return subprocess.call(
            ["zola", "--root", str(LOCAL), "serve",
             "--interface", "127.0.0.1", "--port", str(port)]
        )
    finally:
        if studio:
            studio.terminate()


def main(argv: list[str]) -> int:
    if "--init" in argv:
        return init(bare="--bare" in argv)

    if not DROPIN.exists():
        print("\n  no _dropin/ yet — run: python3 tools/dropin.py --init\n")
        return 1

    placed = assemble()

    # After the copy, because a document's pages are written into the
    # assembled tree and its entry into the page that was just laid down.
    docs, refused = documents()
    placed += docs

    print(f"\n  _local/ assembled, {len(placed)} file(s) from _dropin/:")
    for rel in placed:
        print(f"    {rel}")
    if not placed:
        print("    (none — the preview is the placeholder site)")

    if refused:
        print("\n  documents REFUSED — the site was assembled without them:")
        for why in refused:
            print(f"    {why}")

    check()

    if "--serve" in argv:
        return serve()
    print("\n  See it with: python3 tools/dropin.py --serve\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
